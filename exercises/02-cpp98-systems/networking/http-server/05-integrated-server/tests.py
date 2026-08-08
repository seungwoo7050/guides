import argparse
import os
import select
import signal
import socket
import subprocess
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parent
ROUTES = ROOT / "config" / "routes.conf"
INVALID_ROUTES = ROOT / "config" / "invalid.conf"
ECHO_CGI = ROOT / "helpers" / "echo_cgi.py"
SLOW_CGI = ROOT / "helpers" / "slow_cgi.py"
LARGE_CGI = ROOT / "helpers" / "large_cgi.py"
MEDIUM_CGI = ROOT / "helpers" / "medium_cgi.py"


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
            raise RuntimeError(f"통합 서버 시작 메시지가 {timeout}초 안에 오지 않았습니다: {error}")
        ready, _, _ = select.select([descriptor], [], [], remaining)
        if not ready:
            continue
        chunk = os.read(descriptor, 4096)
        if not chunk:
            break
        data.extend(chunk)
    return bytes(data).split(b"\n", 1)[0].decode("utf-8", errors="replace").strip()


def start(binary, cgi=ECHO_CGI, timeout_ms=1000):
    process = subprocess.Popen(
        [binary, "0", str(ROUTES), str(cgi), str(timeout_ms)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    line = read_startup_line(process)
    if not line.startswith("PORT "):
        error = terminate_failed_start(process)
        raise RuntimeError(f"통합 서버가 시작되지 않았습니다: {line} {error}")
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
        raise AssertionError("통합 서버가 SIGTERM을 처리하지 않았습니다")
    if process.returncode != 0:
        raise RuntimeError(process.stderr.read())


class Peer:
    def __init__(self, port):
        self.socket = socket.create_connection(("127.0.0.1", port), timeout=3)
        self.socket.settimeout(3)
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

    def send(self, method, path, body=b"", close=False):
        connection = b"close" if close else b"keep-alive"
        request = (
            method.encode()
            + b" "
            + path.encode()
            + b" HTTP/1.1\r\nHost: localhost\r\nContent-Length: "
            + str(len(body)).encode()
            + b"\r\nConnection: "
            + connection
            + b"\r\n\r\n"
            + body
        )
        self.socket.sendall(request)
        return self.response()

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
        raise AssertionError("HTTP 머리글이 끝나기 전에 통합 서버가 응답했습니다")


def normal(binary, observe=False):
    process, port = start(binary)
    peer = None
    try:
        peer = Peer(port)
        peer.socket.sendall(b"GET /hea")
        assert_no_response(peer)
        peer.socket.sendall(
            b"lth HTTP/1.1\r\nHost: localhost\r\n"
            b"Content-Length: 0\r\n\r\n"
        )
        status, _, body = peer.response()
        assert status == 200 and body == b"ok\n"

        peer.socket.sendall(
            b"POST /echo HTTP/1.1\r\nHost: localhost\r\n"
            b"Content-Length: 5\r\n\r\nhello"
            b"POST /cgi HTTP/1.1\r\nHost: localhost\r\n"
            b"Content-Length: 5\r\n\r\nworld"
        )
        assert peer.response()[2] == b"hello"
        status, _, body = peer.response()
        assert status == 200 and body == b"WORLD"

        status, _, body = peer.send("GET", "/missing", close=True)
        assert status == 404 and body == "찾을 수 없습니다\n".encode()
        assert peer.socket.recv(1) == b""

        if observe:
            print(f"{port}번 포트에서 파서·라우터·poll·CGI 연결을 확인했습니다")
    finally:
        if peer is not None:
            peer.close()
        stop(process)


def request_once(port, method, path, body=b""):
    peer = Peer(port)
    try:
        return peer.send(method, path, body, close=True)
    finally:
        peer.close()


def assert_server_recovers(process, port):
    status, _, body = request_once(port, "GET", "/health")
    assert status == 200 and body == b"ok\n"
    assert process.poll() is None


def cgi_failure(binary, executable, expected_status, timeout_ms=1000):
    process, port = start(binary, executable, timeout_ms)
    try:
        status, _, _ = request_once(port, "POST", "/cgi", b"payload")
        assert status == expected_status
        assert_server_recovers(process, port)
    finally:
        stop(process)


def failures(binary):
    process, port = start(binary)
    peer = None
    try:
        peer = Peer(port)
        peer.socket.sendall(b"GET /health HTTP/9.9\r\nHost: x\r\n\r\n")
        status, _, _ = peer.response()
        assert status == 400
        assert peer.socket.recv(1) == b""
    finally:
        if peer is not None:
            peer.close()
        stop(process)

    cgi_failure(binary, SLOW_CGI, 504, timeout_ms=100)
    cgi_failure(binary, LARGE_CGI, 502)
    cgi_failure(binary, ROOT / "helpers" / "missing-cgi", 502)

    medium_process, medium_port = start(binary, MEDIUM_CGI)
    try:
        status, _, body = request_once(medium_port, "POST", "/cgi", b"payload")
        assert status == 200 and len(body) == 128 * 1024
    finally:
        stop(medium_process)

    bad_config = subprocess.run(
        [binary, "0", str(INVALID_ROUTES), str(ECHO_CGI), "300"],
        text=True,
        capture_output=True,
        timeout=3,
    )
    assert bad_config.returncode == 2
    assert "경로는 /로 시작해야 합니다" in bad_config.stderr

    bad_usage = subprocess.run(
        [binary, "not-a-port", str(ROUTES), str(ECHO_CGI), "300"],
        text=True,
        capture_output=True,
        timeout=3,
    )
    assert bad_usage.returncode == 2
    assert "포트 값이 허용 범위를 벗어났습니다" in bad_usage.stderr
    print("통합 HTTP 서버 실패 경로 검사: 통과")


def skeleton(binary):
    result = subprocess.run(
        [binary, "0", str(ROUTES), str(ECHO_CGI), "300"],
        text=True,
        capture_output=True,
        timeout=3,
    )
    assert result.returncode == 78
    assert "하나의 서버 흐름으로 연결해 주세요" in result.stderr
    print("통합 HTTP 서버 skeleton의 미구현 상태를 확인했습니다")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("binary")
    parser.add_argument("--observe", action="store_true")
    parser.add_argument("--failures", action="store_true")
    parser.add_argument("--skeleton", action="store_true")
    arguments = parser.parse_args()

    if arguments.skeleton:
        skeleton(arguments.binary)
    elif arguments.failures:
        failures(arguments.binary)
    else:
        normal(arguments.binary, arguments.observe)
        print("통합 HTTP 서버 검사: 통과")


if __name__ == "__main__":
    main()
