"""classic PCAP 파일의 전역 헤더와 패킷 레코드를 해석합니다."""

from __future__ import annotations

from dataclasses import dataclass
import struct

from .errors import PacketFormatError


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


_MAGIC = {
    b"\xd4\xc3\xb2\xa1": ("<", "microseconds"),
    b"\xa1\xb2\xc3\xd4": (">", "microseconds"),
    b"\x4d\x3c\xb2\xa1": ("<", "nanoseconds"),
    b"\xa1\xb2\x3c\x4d": (">", "nanoseconds"),
}


# [Implementation 3] byte order와 timestamp 해상도를 정한 뒤 snaplen과 record 길이 경계를 검증합니다.
def parse_pcap(data: bytes) -> Capture:
    if not isinstance(data, bytes):
        raise ValueError("PCAP 입력은 bytes여야 합니다.")
    if len(data) < 24:
        raise PacketFormatError("PCAP 전역 헤더가 잘렸습니다.")
    format_info = _MAGIC.get(data[:4])
    if format_info is None:
        raise PacketFormatError("지원하지 않는 PCAP 매직 값입니다.")
    order, resolution = format_info
    major, minor, _zone, _accuracy, snap_length, link_type = struct.unpack_from(
        f"{order}HHiIII", data, 4
    )
    if (major, minor) != (2, 4):
        raise PacketFormatError(f"지원하지 않는 PCAP 버전입니다: {major}.{minor}")
    if snap_length == 0:
        raise PacketFormatError("snaplen은 0보다 커야 합니다.")

    packets: list[CapturedPacket] = []
    offset = 24
    while offset < len(data):
        if len(data) - offset < 16:
            raise PacketFormatError("PCAP 패킷 헤더가 잘렸습니다.")
        seconds, fraction, included, original = struct.unpack_from(
            f"{order}IIII", data, offset
        )
        offset += 16
        fraction_limit = 1_000_000 if resolution == "microseconds" else 1_000_000_000
        if fraction >= fraction_limit:
            raise PacketFormatError("패킷 시각의 소수부가 해상도 범위를 넘습니다.")
        if included > snap_length:
            raise PacketFormatError("저장 길이가 snaplen을 넘습니다.")
        if included > original:
            raise PacketFormatError("저장 길이가 원래 패킷 길이보다 큽니다.")
        end = offset + included
        if end > len(data):
            raise PacketFormatError("PCAP 패킷 데이터가 잘렸습니다.")
        packets.append(
            CapturedPacket(seconds, fraction, original, data[offset:end])
        )
        offset = end
    return Capture(
        "little" if order == "<" else "big",
        resolution,
        snap_length,
        link_type,
        tuple(packets),
    )
