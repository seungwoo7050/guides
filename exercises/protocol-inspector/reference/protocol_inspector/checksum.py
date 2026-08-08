"""인터넷 체크섬과 IPv4 TCP 의사 헤더 체크섬을 계산합니다."""

from __future__ import annotations

import ipaddress


def internet_checksum(data: bytes) -> int:
    """16비트 1의 보수 합에 대한 1의 보수를 반환합니다.

    반환값을 체크섬 필드에 넣을 수 있습니다. 이미 체크섬이 들어 있는
    전체 헤더를 전달했을 때 반환값이 0이면 체크섬이 일치합니다.
    """

    if len(data) % 2:
        data += b"\x00"

    total = 0
    for offset in range(0, len(data), 2):
        total += int.from_bytes(data[offset : offset + 2], "big")
        total = (total & 0xFFFF) + (total >> 16)

    while total >> 16:
        total = (total & 0xFFFF) + (total >> 16)
    return (~total) & 0xFFFF


def checksum_is_valid(data: bytes) -> bool:
    """체크섬 필드를 포함한 바이트열의 인터넷 체크섬을 확인합니다."""

    return internet_checksum(data) == 0


def tcp_checksum_ipv4(
    source: str | ipaddress.IPv4Address,
    destination: str | ipaddress.IPv4Address,
    segment: bytes,
) -> int:
    """IPv4 의사 헤더를 포함해 TCP 체크섬을 계산합니다."""

    source_address = ipaddress.IPv4Address(source)
    destination_address = ipaddress.IPv4Address(destination)
    if len(segment) > 0xFFFF:
        raise ValueError("TCP 세그먼트 길이는 65535바이트를 넘을 수 없습니다")

    pseudo_header = (
        source_address.packed
        + destination_address.packed
        + b"\x00"
        + b"\x06"
        + len(segment).to_bytes(2, "big")
    )
    return internet_checksum(pseudo_header + segment)
