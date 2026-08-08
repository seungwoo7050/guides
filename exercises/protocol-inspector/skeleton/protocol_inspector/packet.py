"""Ethernet, IPv4와 TCP 헤더 파서의 미완성 구현입니다."""

from __future__ import annotations

from dataclasses import dataclass
import ipaddress

from .errors import PacketFormatError


@dataclass(frozen=True)
class VlanTag:
    priority: int
    drop_eligible: bool
    vlan_id: int


@dataclass(frozen=True)
class EthernetFrame:
    destination: str
    source: str
    ethertype: int
    payload: bytes
    vlan: VlanTag | None = None


@dataclass(frozen=True)
class IPv4Packet:
    header_length: int
    dscp: int
    ecn: int
    total_length: int
    identification: int
    flags: int
    fragment_offset: int
    ttl: int
    protocol: int
    header_checksum: int
    checksum_valid: bool
    source: ipaddress.IPv4Address
    destination: ipaddress.IPv4Address
    options: bytes
    payload: bytes


@dataclass(frozen=True)
class TCPSegment:
    source_port: int
    destination_port: int
    sequence_number: int
    acknowledgment_number: int
    header_length: int
    flags: tuple[str, ...]
    window_size: int
    checksum: int
    checksum_valid: bool | None
    urgent_pointer: int
    options: bytes
    payload: bytes


@dataclass(frozen=True)
class DecodedPacket:
    ethernet: EthernetFrame
    ipv4: IPv4Packet | None
    tcp: TCPSegment | None


def parse_ethernet(data: bytes) -> EthernetFrame:
    """Ethernet II와 선택적인 802.1Q 태그를 해석하도록 완성합니다."""

    raise NotImplementedError("최소 길이와 VLAN 태그 경계를 먼저 검사하세요")


def parse_ipv4(data: bytes) -> IPv4Packet:
    """IHL과 total length를 신뢰하기 전에 경계를 검사하도록 완성합니다."""

    raise NotImplementedError("버전, IHL, total length와 헤더 체크섬을 처리하세요")


def parse_tcp(
    data: bytes,
    *,
    source: str | ipaddress.IPv4Address | None = None,
    destination: str | ipaddress.IPv4Address | None = None,
) -> TCPSegment:
    """data offset, 플래그, 옵션과 체크섬을 해석하도록 완성합니다."""

    raise NotImplementedError("고정 헤더 뒤의 옵션과 페이로드 경계를 나누세요")


def decode_ethernet_ipv4_tcp(data: bytes) -> DecodedPacket:
    """EtherType과 IP protocol을 확인하며 계층별 파서를 연결하도록 완성합니다."""

    raise NotImplementedError("지원하지 않는 상위 프로토콜은 원시 payload로 남기세요")
