#!/usr/bin/env python3
import argparse
import os
import select
import signal
import socket
import subprocess
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ROUTES = ROOT / "config" / "routes.conf"
INVALID_ROUTES = ROOT / "config" / "invalid.conf"
ECHO_CGI = ROOT / "helpers" / "echo_cgi.py"
SLOW_CGI = ROOT / "helpers" / "slow_cgi.py"
LARGE_CGI = ROOT / "helpers" / "large_cgi.py"
MEDIUM_CGI = ROOT / "helpers" / "medium_cgi.py"


def failed_start(process: subprocess.Popen[str]) -> str:
    if process.poll() is None:
        process.terminate()
    try:
        process.wait(timeout=1)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait()
    assert process.stderr is not None
    return process.stderr.read()


def start(binary: str, cgi: Path = ECHO_CGI, timeout_ms: int = 1000):
    process = subprocess.Popen(
        [binary, "0", str(ROUTES), str(cgi), str(timeout_ms)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    assert process.stdout is not None
    ready, _, _ = select.select([process.stdout], [], [], 5)
    if not ready:
        raise RuntimeError(f"server startup timeout: {failed_start(process)}")
    line = process.stdout.readline().strip()
    if not line.startswith("PORT "):
        raise RuntimeError(f"invalid startup line {line!r}: {failed_start(process)}")
    return process, int(line.split()[1])


def stop(process: subprocess.Popen[str]) -> None:
    if process.poll() is None:
        process.send_signal(signal.SIGTERM)
    try:
        process.wait(timeout=3)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait()
        raise AssertionError("server did not terminate after SIGTERM")
    if process.returncode != 0:
        assert process.stderr is not None
        raise RuntimeError(process.stderr.read())


class Peer:
    def __init__(self, port: int):
        self.socket = socket.create_connection(("127.0.0.1", port), timeout=3)
        self.socket.settimeout(3)
        self.buffer = b""

    def response(self):
        while b"\r\n\r\n" not in self.buffer:
            chunk = self.socket.recv(4096)
            if not chunk:
                raise RuntimeError("connection closed before response headers")
            self.buffer += chunk
        header_bytes, self.buffer = self.buffer.split(b"\r\n\r\n", 1)
        lines = header_bytes.decode("ascii").split("\r\n")
        status = int(lines[0].split()[1])
        headers = {}
        for line in lines[1:]:
            name, value = line.split(":", 1)
            headers[name.lower()] = value.strip()
        length = int(headers["content-length"])
        while len(self.buffer) < length:
            chunk = self.socket.recv(4096)
            if not chunk:
                raise RuntimeError("connection closed before response body")
            self.buffer += chunk
        body, self.buffer = self.buffer[:length], self.buffer[length:]
        return status, headers, body

    def send(self, method: str, path: str, body: bytes = b"", close: bool = False):
        connection = b"close" if close else b"keep-alive"
        request = (
            method.encode() + b" " + path.encode() + b" HTTP/1.1\r\n"
            b"Host: localhost\r\nContent-Length: " + str(len(body)).encode() +
            b"\r\nConnection: " + connection + b"\r\n\r\n" + body
        )
        self.socket.sendall(request)
        return self.response()

    def close(self):
        self.socket.close()


def request_once(port: int, method: str, path: str, body: bytes = b""):
    peer = Peer(port)
    try:
        return peer.send(method, path, body, close=True)
    finally:
        peer.close()


def normal(binary: str) -> None:
    process, port = start(binary)
    peer = None
    try:
        peer = Peer(port)
        peer.socket.sendall(b"GET /hea")
        readable, _, exceptional = select.select([peer.socket], [], [peer.socket], 0.05)
        assert not readable and not exceptional
        peer.socket.sendall(
            b"lth HTTP/1.1\r\nHost: localhost\r\nContent-Length: 0\r\n\r\n"
        )
        status, _, body = peer.response()
        assert status == 200 and body == b"ok\n"

        peer.socket.sendall(
            b"POST /echo HTTP/1.1\r\nHost: localhost\r\nContent-Length: 5\r\n\r\nhello"
            b"POST /cgi HTTP/1.1\r\nHost: localhost\r\nContent-Length: 5\r\n\r\nworld"
        )
        assert peer.response()[2] == b"hello"
        status, _, body = peer.response()
        assert status == 200 and body == b"WORLD"

        status, headers, body = peer.send("GET", "/missing", close=True)
        assert status == 404 and body == b"not found\n"
        assert headers["connection"] == "close"
        assert peer.socket.recv(1) == b""
    finally:
        if peer is not None:
            peer.close()
        stop(process)


def assert_server_recovers(process, port):
    status, _, body = request_once(port, "GET", "/health")
    assert status == 200 and body == b"ok\n"
    assert process.poll() is None


def cgi_failure(binary: str, executable: Path, expected_status: int,
                timeout_ms: int = 1000) -> None:
    process, port = start(binary, executable, timeout_ms)
    try:
        status, _, _ = request_once(port, "POST", "/cgi", b"payload")
        assert status == expected_status
        assert_server_recovers(process, port)
    finally:
        stop(process)


def failures(binary: str) -> None:
    process, port = start(binary)
    peer = None
    try:
        peer = Peer(port)
        peer.socket.sendall(b"GET /health HTTP/9.9\r\nHost: x\r\n\r\n")
        status, _, body = peer.response()
        assert status == 400 and body == b"bad request\n"
        assert peer.socket.recv(1) == b""
    finally:
        if peer is not None:
            peer.close()
        stop(process)

    cgi_failure(binary, SLOW_CGI, 504, timeout_ms=100)
    cgi_failure(binary, LARGE_CGI, 502)
    cgi_failure(binary, ROOT / "helpers" / "missing-cgi", 502)

    process, port = start(binary, MEDIUM_CGI)
    try:
        status, _, body = request_once(port, "POST", "/cgi", b"payload")
        assert status == 200 and len(body) == 128 * 1024
    finally:
        stop(process)

    invalid = subprocess.run(
        [binary, "0", str(INVALID_ROUTES), str(ECHO_CGI), "300"],
        text=True, capture_output=True, timeout=3,
    )
    assert invalid.returncode == 2
    assert "route path must start with /" in invalid.stderr

    bad_argument = subprocess.run(
        [binary, "not-a-port", str(ROUTES), str(ECHO_CGI), "300"],
        text=True, capture_output=True, timeout=3,
    )
    assert bad_argument.returncode == 2
    assert "port is out of range" in bad_argument.stderr


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("binary")
    parser.add_argument("--normal", action="store_true")
    parser.add_argument("--failures", action="store_true")
    args = parser.parse_args()
    binary = os.path.realpath(args.binary)
    if args.normal:
        normal(binary)
    elif args.failures:
        failures(binary)
    else:
        normal(binary)
        failures(binary)


if __name__ == "__main__":
    main()
