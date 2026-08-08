import argparse
import os
import select
import signal
import socket
import subprocess
import time


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


class Peer:
    def __init__(self, port):
        self.socket = socket.create_connection(("127.0.0.1", port), timeout=2)
        self.socket.settimeout(2)
        self.buffer = b""

    def response(self):
        while b"\r\n\r\n" not in self.buffer:
            chunk = self.socket.recv(4096)
            if not chunk:
                raise RuntimeError("응답 머리글을 받기 전에 연결이 끝났습니다")
            self.buffer += chunk

        header_bytes, self.buffer = self.buffer.split(b"\r\n\r\n", 1)
        lines = header_bytes.decode("ascii").split("\r\n")
        status = int(lines[0].split()[1])
        headers = {}
        for line in lines[1:]:
            name, value = line.split(":", 1)
            headers[name.lower()] = value.strip()

        if "content-length" not in headers:
            raise RuntimeError("응답에 Content-Length가 없습니다")
        try:
            length = int(headers["content-length"])
        except ValueError as error:
            raise RuntimeError("잘못된 Content-Length 응답입니다") from error
        if length < 0:
            raise RuntimeError("음수 Content-Length 응답입니다")

        while len(self.buffer) < length:
            chunk = self.socket.recv(4096)
            if not chunk:
                raise RuntimeError("응답 본문을 받기 전에 연결이 끝났습니다")
            self.buffer += chunk

        body = self.buffer[:length]
        self.buffer = self.buffer[length:]
        return status, headers, body

    def close(self):
        self.socket.close()


def assert_no_response(peer, timeout=0.05):
    readable, _, exceptional = select.select([peer.socket], [], [peer.socket], timeout)
    if exceptional:
        raise AssertionError("부분 HTTP 요청 뒤 socket 오류가 발생했습니다")
    if readable:
        data = peer.socket.recv(1, socket.MSG_PEEK)
        if not data:
            raise AssertionError("부분 HTTP 요청 뒤 연결이 닫혔습니다")
        raise AssertionError("HTTP 머리글이 끝나기 전에 서버가 응답했습니다")


def normal(binary, observe=False):
    process, port = start(binary)
    peer = None
    try:
        peer = Peer(port)
        peer.socket.sendall(b"GET /hea")
        assert_no_response(peer)
        peer.socket.sendall(b"lth HTTP/1.1\r\nHost: x\r\n\r\n")
        status, _, body = peer.response()
        assert status == 200 and body == b"ok\n"

        # 두 요청을 한 번의 TCP 쓰기로 보내 파이프라이닝과 연결 유지를 검증합니다.
        peer.socket.sendall(
            b"GET / HTTP/1.1\r\nHost: x\r\n\r\n"
            b"POST /echo HTTP/1.1\r\nHost: x\r\n"
            b"Content-Length: 5\r\n\r\nhello"
        )
        assert peer.response()[2] == b"hello\n"
        assert peer.response()[2] == b"hello"

        peer.socket.sendall(
            b"DELETE /resource HTTP/1.1\r\n"
            b"Host: x\r\nConnection: close\r\n\r\n"
        )
        status, _, body = peer.response()
        assert status == 204 and body == b""
        assert peer.socket.recv(1) == b""

        if observe:
            print(f"{port}번 포트에서 분할 파싱, 파이프라이닝과 연결 유지를 확인했습니다")
    finally:
        if peer is not None:
            peer.close()
        stop(process)


def failure_cases(binary):
    process, port = start(binary)
    try:
        cases = [
            (b"GET / HTTP/9.9\r\nHost: x\r\n\r\n", 400),
            (b"GET / HTTP/1.1\r\n\r\n", 400),
            (
                b"POST / HTTP/1.1\r\nHost: x\r\n"
                b"Content-Length: nope\r\n\r\n",
                400,
            ),
        ]
        for request, expected in cases:
            peer = Peer(port)
            try:
                peer.socket.sendall(request)
                status, _, _ = peer.response()
                assert status == expected
                assert peer.socket.recv(1) == b""
            finally:
                peer.close()

        peer = Peer(port)
        try:
            peer.socket.sendall(
                b"GET /missing HTTP/1.1\r\n"
                b"Host: x\r\nConnection: close\r\n\r\n"
            )
            status, _, body = peer.response()
            assert status == 404 and body == "찾을 수 없습니다\n".encode()
        finally:
            peer.close()

        print("HTTP 서버 실패 경로 검사: 통과")
    finally:
        stop(process)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("binary")
    parser.add_argument("--observe", action="store_true")
    parser.add_argument("--failures", action="store_true")
    args = parser.parse_args()

    if args.failures:
        failure_cases(args.binary)
    else:
        normal(args.binary, args.observe)
        print("HTTP 서버 검사: 통과")


if __name__ == "__main__":
    main()
