#!/usr/bin/env python3
"""NAT 실습에서 관찰 가능한 UDP 요청과 응답을 만듭니다."""

from __future__ import annotations

import argparse
from pathlib import Path
import socket


# [Implementation 5] server가 본 peer와 응답을 남기는 최소 UDP workload를 만듭니다.
def run_server(bind: str, port: int, output: Path, ready: Path) -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.bind((bind, port))
        sock.settimeout(8)
        # ``x`` 모드는 예상 밖의 기존 경로를 따라가지 않고 생성을 거부합니다.
        # bind 이후 marker를 게시하면 셸 드라이버가 실제 준비 경계를 확인할 수
        # 있습니다. UDP에는 연결 handshake나 여기서의 재시도가 없으므로 고정
        # sleep만 사용하면 부하가 큰 호스트에서 유일한 datagram을 잃을 수 있습니다.
        with ready.open("x", encoding="utf-8") as marker:
            marker.write("ready\n")
        payload, peer = sock.recvfrom(1024)
        output.write_text(f"{peer[0]}:{peer[1]} {payload.decode('ascii')}\n", encoding="utf-8")
        sock.sendto(b"ack", peer)
    return 0


def run_client(target: str, port: int) -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.settimeout(8)
        sock.sendto(b"probe", (target, port))
        payload, _ = sock.recvfrom(1024)
        if payload != b"ack":
            raise SystemExit(f"예상하지 않은 응답: {payload!r}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="UDP 요청의 주소 변환 결과를 관찰할 요청과 응답을 만듭니다."
    )
    sub = parser.add_subparsers(dest="mode", required=True, title="실행 역할")
    server = sub.add_parser("server", help="UDP 서버를 실행합니다")
    server.add_argument("--bind", required=True, help="수신 대기할 주소")
    server.add_argument("--port", type=int, required=True, help="수신 대기할 포트")
    server.add_argument("--output", type=Path, required=True, help="관찰 결과 파일")
    server.add_argument(
        "--ready",
        type=Path,
        required=True,
        help="bind 완료 뒤 배타적으로 만들 준비 marker",
    )
    client = sub.add_parser("client", help="UDP 클라이언트를 실행합니다")
    client.add_argument("--target", required=True, help="요청을 보낼 서버 주소")
    client.add_argument("--port", type=int, required=True, help="요청을 보낼 서버 포트")
    args = parser.parse_args()
    if args.mode == "server":
        return run_server(args.bind, args.port, args.output, args.ready)
    return run_client(args.target, args.port)


if __name__ == "__main__":
    raise SystemExit(main())
