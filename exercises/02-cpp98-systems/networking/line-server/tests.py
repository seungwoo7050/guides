import argparse
import os
import select
import shutil
import signal
import socket
import subprocess
import threading
import time
from pathlib import Path


_RECEIVERS = {}


def terminate_failed_start(process):
    if process.poll() is None:
        process.terminate()
    try:
        process.wait(timeout=1)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait()
    return process.stderr.read()


def read_startup_line(process, timeout=5):
    deadline = time.monotonic() + timeout
    data = bytearray()
    descriptor = process.stdout.fileno()
    while b"\n" not in data:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            error = terminate_failed_start(process)
            raise RuntimeError(f"서버 시작 메시지가 {timeout}초 안에 오지 않았습니다: {error}")
        ready, _, _ = select.select([descriptor], [], [], remaining)
        if not ready:
            continue
        chunk = os.read(descriptor, 4096)
        if not chunk:
            break
        data.extend(chunk)
    return bytes(data).split(b"\n", 1)[0].decode("utf-8", errors="replace").strip()


def start(binary):
    process = subprocess.Popen(
        [binary, "0"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    line = read_startup_line(process)
    if not line.startswith("PORT "):
        error = terminate_failed_start(process)
        raise RuntimeError(f"서버가 시작되지 않았습니다: {line} {error}")
    try:
        port = int(line.split()[1])
    except (IndexError, ValueError) as error:
        detail = terminate_failed_start(process)
        raise RuntimeError(f"잘못된 시작 메시지입니다: {line} {detail}") from error
    return process, port


def stop(process):
    if process.poll() is None:
        process.send_signal(signal.SIGTERM)
    try:
        process.wait(timeout=3)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait()
        raise AssertionError("서버가 SIGTERM을 처리하지 않았습니다")
    if process.returncode != 0:
        raise RuntimeError(process.stderr.read())


def connect(port, timeout=3):
    peer = socket.create_connection(("127.0.0.1", port), timeout=timeout)
    peer.settimeout(timeout)
    return peer


def recv_line(peer):
    key = id(peer)
    receiver = _RECEIVERS.get(key)
    if receiver is None:
        receiver = peer.makefile("rb")
        _RECEIVERS[key] = receiver

    data = receiver.readline()
    if not data:
        raise RuntimeError("줄 끝을 받기 전에 연결이 닫혔습니다")
    if not data.endswith(b"\n"):
        raise RuntimeError("줄 종료 문자 없이 연결이 닫혔습니다")
    return data


def assert_no_response(peer, timeout=0.05):
    readable, _, exceptional = select.select([peer], [], [peer], timeout)
    if exceptional:
        raise AssertionError("부분 프레임 뒤 socket 오류가 발생했습니다")
    if readable:
        data = peer.recv(1, socket.MSG_PEEK)
        if not data:
            raise AssertionError("부분 프레임 뒤 연결이 닫혔습니다")
        raise AssertionError("줄 끝 전에 서버가 응답했습니다")


def normal(binary, observe=False):
    process, port = start(binary)
    try:
        first = connect(port)
        first.sendall(b"alpha\n")
        assert recv_line(first) == b"ECHO alpha\n"

        # 한 줄을 여러 write로 나누고, 줄 끝 전에는 응답하지 않는지 확인합니다.
        first.sendall(b"par")
        assert_no_response(first)
        first.sendall(b"tial\n")
        assert recv_line(first) == b"ECHO partial\n"

        # 한 write에 여러 줄이 있어도 각 프레임을 독립적으로 처리해야 합니다.
        first.sendall(b"one\ntwo\n")
        assert recv_line(first) == b"ECHO one\n"
        assert recv_line(first) == b"ECHO two\n"

        second = connect(port)
        second.sendall(b"beta\n")
        assert recv_line(second) == b"ECHO beta\n"
        second.close()

        if observe:
            print(f"{port}번 포트에서 분할·다중 프레임과 동시 연결을 확인했습니다")
        first.close()
    finally:
        stop(process)


def stress(binary):
    process, port = start(binary)
    errors = []
    lock = threading.Lock()
    count = 40
    barrier = threading.Barrier(count)

    def worker(index):
        try:
            peer = connect(port, timeout=5)
            barrier.wait(timeout=5)
            message = f"client-{index}\n".encode()
            peer.sendall(message)
            if recv_line(peer) != b"ECHO " + message:
                raise AssertionError("잘못된 echo 응답")
            peer.close()
        except Exception as error:  # 스레드의 실패를 주 스레드로 전달합니다.
            with lock:
                errors.append(error)

    threads = [threading.Thread(target=worker, args=(index,)) for index in range(count)]
    try:
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=10)
        alive = [thread for thread in threads if thread.is_alive()]
        assert not alive, f"종료되지 않은 client thread: {len(alive)}"
        assert not errors, errors
        print(f"동시 연결 {count}개 검사: 통과")
    finally:
        stop(process)


def backpressure(binary):
    process, port = start(binary)
    slow = None
    try:
        slow = connect(port)
        slow.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 4096)
        slow.settimeout(3)
        payload = b"x" * 200 + b"\n"
        try:
            slow.sendall(payload * 1000)
        except (BrokenPipeError, ConnectionResetError, socket.timeout):
            pass

        closed = False
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            try:
                chunk = slow.recv(65536)
            except (ConnectionResetError, BrokenPipeError):
                closed = True
                break
            except socket.timeout:
                continue
            if not chunk:
                closed = True
                break
        assert closed, "느린 독자 연결이 출력 상한 뒤 닫히지 않았습니다"

        probe = connect(port)
        probe.sendall(b"still-alive\n")
        assert recv_line(probe) == b"ECHO still-alive\n"
        probe.close()
        print("느린 독자 backpressure 검사: 통과")
    finally:
        if slow is not None:
            slow.close()
        stop(process)


def lsof_fd_count(pid):
    executable = shutil.which("lsof")
    if executable is None:
        return None
    result = subprocess.run(
        [executable, "-a", "-p", str(pid), "-Fn"],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=5,
        check=False,
    )
    if result.returncode not in (0, 1):
        raise RuntimeError(f"lsof 실패: {result.stderr}")
    return sum(1 for line in result.stdout.splitlines() if line.startswith("n"))


def fd_count(pid):
    directory = Path(f"/proc/{pid}/fd")
    if directory.is_dir():
        return len(list(directory.iterdir()))
    count = lsof_fd_count(pid)
    if count is not None:
        return count
    raise RuntimeError("FD 누수 검사를 위해 /proc 또는 lsof가 필요합니다")


def leak_check(binary):
    if os.uname().sysname == "Darwin":
        print("Darwin 환경에서는 FD 누수 검사를 건너뜁니다")
        return

    process, port = start(binary)
    try:
        before = fd_count(process.pid)
        for index in range(100):
            peer = connect(port)
            message = f"leak-{index}\n".encode()
            peer.sendall(message)
            assert recv_line(peer) == b"ECHO " + message
            peer.close()

        deadline = time.monotonic() + 5
        stable = 0
        after = None
        while time.monotonic() < deadline:
            after = fd_count(process.pid)
            if after <= before + 2:
                stable += 1
                if stable >= 3:
                    break
            else:
                stable = 0
            time.sleep(0.05)
        assert after is not None and after <= before + 2, (before, after)
        print(f"반복 연결 파일 디스크립터 검사: {before} -> {after}")
    finally:
        stop(process)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("binary")
    parser.add_argument("--observe", action="store_true")
    parser.add_argument("--stress", action="store_true")
    parser.add_argument("--backpressure", action="store_true")
    parser.add_argument("--leak-check", action="store_true")
    arguments = parser.parse_args()

    if arguments.stress:
        stress(arguments.binary)
    elif arguments.backpressure:
        backpressure(arguments.binary)
    elif arguments.leak_check:
        leak_check(arguments.binary)
    else:
        normal(arguments.binary, arguments.observe)
        backpressure(arguments.binary)
        print("논블로킹 line server 검사: 통과")


if __name__ == "__main__":
    main()
