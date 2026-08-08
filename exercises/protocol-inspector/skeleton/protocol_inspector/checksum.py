"""인터넷 체크섬을 직접 구현하는 미완성 구현입니다."""

from __future__ import annotations

import ipaddress


def internet_checksum(data: bytes) -> int:
    """16비트 1의 보수 체크섬을 반환하도록 완성합니다."""

    raise NotImplementedError("홀수 길이 패딩, end-around carry와 1의 보수를 구현하세요")


def checksum_is_valid(data: bytes) -> bool:
    """체크섬 필드를 포함한 바이트열을 검증하도록 완성합니다."""

    raise NotImplementedError("계산 결과가 0인지 확인하세요")


def tcp_checksum_ipv4(
    source: str | ipaddress.IPv4Address,
    destination: str | ipaddress.IPv4Address,
    segment: bytes,
) -> int:
    """IPv4 의사 헤더를 포함한 TCP 체크섬을 계산하도록 완성합니다."""

    raise NotImplementedError("출발지, 목적지, 프로토콜과 길이를 의사 헤더에 넣으세요")
