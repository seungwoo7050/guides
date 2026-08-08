"""classic PCAP 파일의 전역 헤더와 패킷 레코드를 해석합니다."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CapturedPacket:
    timestamp_seconds: int
    timestamp_fraction: int
    original_length: int
    data: bytes


@dataclass(frozen=True)
class Capture:
    byte_order: str
    timestamp_resolution: str
    snap_length: int
    link_type: int
    packets: tuple[CapturedPacket, ...]


def parse_pcap(data: bytes) -> Capture:
    raise NotImplementedError("TODO: PCAP 전역 헤더와 패킷 레코드를 해석하세요.")
