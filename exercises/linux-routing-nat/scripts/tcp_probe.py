#!/usr/bin/env python3
"""SYN 재전송 실습에서 한 번의 TCP 연결을 만듭니다."""

from __future__ import annotations

import argparse
import socket


def run_server(bind: str, port: int) -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
        listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        listener.bind((bind, port))
        listener.listen(1)
        listener.settimeout(12)
        connection, _ = listener.accept()
        with connection:
            connection.settimeout(5)
            data = connection.recv(16)
            if data != b"probe":
                raise SystemExit(f"예상하지 않은 요청 페이로드입니다: {data!r}")
            connection.sendall(b"ack")
    return 0


def run_client(target: str, port: int, timeout: float) -> int:
    with socket.create_connection((target, port), timeout=timeout) as connection:
        connection.settimeout(5)
        connection.sendall(b"probe")
        if connection.recv(16) != b"ack":
            raise SystemExit("예상한 ACK 페이로드를 받지 못했습니다")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="TCP 연결을 한 번 실행해 SYN 재전송 실험을 돕습니다."
    )
    sub = parser.add_subparsers(dest="mode", required=True, title="실행 역할")
    server = sub.add_parser("server", help="TCP 서버를 실행합니다")
    server.add_argument("--bind", required=True, help="수신 대기할 주소")
    server.add_argument("--port", type=int, required=True, help="수신 대기할 포트")
    client = sub.add_parser("client", help="TCP 클라이언트를 실행합니다")
    client.add_argument("--target", required=True, help="접속할 서버 주소")
    client.add_argument("--port", type=int, required=True, help="접속할 서버 포트")
    client.add_argument("--timeout", type=float, default=10, help="연결 제한 시간(초)")
    args = parser.parse_args()
    if args.mode == "server":
        return run_server(args.bind, args.port)
    return run_client(args.target, args.port, args.timeout)


if __name__ == "__main__":
    raise SystemExit(main())
