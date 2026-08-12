"""프로토콜 실습 모듈을 실행하는 명령줄 인터페이스입니다."""

from __future__ import annotations

import argparse
from dataclasses import asdict
import json
from pathlib import Path
from typing import Any

from .checksum import internet_checksum
from .packet import decode_ethernet_ipv4_tcp
from .pcap import parse_pcap
from .routing import Route, RoutingTable
from .tcp_state import EndpointRole, TCPEndpoint, TCPEvent


def _load_hex(path: Path) -> bytes:
    chunks: list[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        body = line.split("#", 1)[0].strip().replace(" ", "")
        if body:
            chunks.append(body)
    return bytes.fromhex("".join(chunks))


def _jsonable(value: Any) -> Any:
    if isinstance(value, bytes):
        return value.hex()
    if hasattr(value, "compressed"):
        return str(value)
    if isinstance(value, tuple):
        return list(value)
    if isinstance(value, dict):
        return {key: _jsonable(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_jsonable(item) for item in value]
    return value


# [Implementation 6] domain 결과를 안정적인 JSON·text·exit status adapter로 노출합니다.
def command_decode(args: argparse.Namespace) -> int:
    decoded = decode_ethernet_ipv4_tcp(_load_hex(args.path))
    payload = {
        "ethernet": _jsonable(asdict(decoded.ethernet)),
        "ipv4": _jsonable(asdict(decoded.ipv4)) if decoded.ipv4 else None,
        "tcp": _jsonable(asdict(decoded.tcp)) if decoded.tcp else None,
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


def command_checksum(args: argparse.Namespace) -> int:
    data = bytes.fromhex(args.hex.replace(" ", ""))
    print(f"0x{internet_checksum(data):04x}")
    return 0


def command_pcap(args: argparse.Namespace) -> int:
    capture = parse_pcap(args.path.read_bytes())
    print(
        json.dumps(
            {
                "byte_order": capture.byte_order,
                "timestamp_resolution": capture.timestamp_resolution,
                "snap_length": capture.snap_length,
                "link_type": capture.link_type,
                "packets": [
                    {
                        "timestamp_seconds": packet.timestamp_seconds,
                        "timestamp_fraction": packet.timestamp_fraction,
                        "captured_length": len(packet.data),
                        "original_length": packet.original_length,
                        "data": packet.data.hex(),
                    }
                    for packet in capture.packets
                ],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


def command_route(args: argparse.Namespace) -> int:
    rows = json.loads(args.table.read_text(encoding="utf-8"))
    table = RoutingTable()
    for row in rows:
        table.add(
            Route.from_strings(
                row["network"],
                row["interface"],
                next_hop=row.get("next_hop"),
                metric=int(row.get("metric", 0)),
            )
        )
    route = table.lookup(args.destination)
    if route is None:
        print("no-route")
        return 1
    print(
        json.dumps(
            {
                "network": str(route.network),
                "interface": route.interface,
                "next_hop": str(route.next_hop) if route.next_hop else None,
                "metric": route.metric,
            },
            ensure_ascii=False,
        )
    )
    return 0


def command_tcp(args: argparse.Namespace) -> int:
    endpoint = TCPEndpoint(EndpointRole(args.role))
    print(endpoint.state.value)
    for raw_event in args.events.split(","):
        event = TCPEvent(raw_event.strip())
        print(endpoint.apply(event).value)
    return 0


# [Implementation 6-1] 하위 명령의 입력 계약을 등록하고 handler 조립점을 하나로 둡니다.
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m protocol_inspector",
        description="프레임 해석, 체크섬, 경로 조회와 TCP 상태 전이를 검증합니다.",
    )
    subparsers = parser.add_subparsers(
        dest="command",
        required=True,
        title="하위 명령",
    )

    decode = subparsers.add_parser("decode", help="Ethernet/IPv4/TCP 프레임을 해석합니다")
    decode.add_argument("path", type=Path, help="16진수 프레임 파일 경로")
    decode.set_defaults(handler=command_decode)

    checksum = subparsers.add_parser("checksum", help="인터넷 체크섬을 계산합니다")
    checksum.add_argument("hex", help="체크섬을 계산할 16진수 바이트열")
    checksum.set_defaults(handler=command_checksum)

    pcap = subparsers.add_parser("pcap", help="classic PCAP 레코드를 해석합니다")
    pcap.add_argument("path", type=Path, help="PCAP 파일 경로")
    pcap.set_defaults(handler=command_pcap)

    route = subparsers.add_parser("route", help="최장 프리픽스 일치를 수행합니다")
    route.add_argument("--table", type=Path, required=True, help="JSON 경로 테이블")
    route.add_argument("--destination", required=True, help="조회할 IPv4 목적지 주소")
    route.set_defaults(handler=command_route)

    tcp = subparsers.add_parser("tcp", help="TCP 상태 전이를 실행합니다")
    tcp.add_argument(
        "--role",
        choices=[role.value for role in EndpointRole],
        required=True,
        help="연결 종단점의 역할",
    )
    tcp.add_argument("--events", required=True, help="쉼표로 구분한 TCP 사건 목록")
    tcp.set_defaults(handler=command_tcp)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    return int(args.handler(args))
