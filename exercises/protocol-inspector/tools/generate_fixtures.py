#!/usr/bin/env python3
"""검사에 사용하는 Ethernet/IPv4/TCP SYN 프레임을 결정적으로 생성합니다."""

from __future__ import annotations

from pathlib import Path
import sys

EXERCISE = Path(__file__).resolve().parents[1]
REFERENCE = EXERCISE / "reference"
sys.path.insert(0, str(REFERENCE))

from protocol_inspector.checksum import internet_checksum, tcp_checksum_ipv4


def build_syn_frame() -> bytes:
    source_ip = bytes([192, 0, 2, 10])
    destination_ip = bytes([198, 51, 100, 20])

    tcp = bytearray()
    tcp += (49152).to_bytes(2, "big")
    tcp += (443).to_bytes(2, "big")
    tcp += (0x01020304).to_bytes(4, "big")
    tcp += (0).to_bytes(4, "big")
    tcp += bytes([0x60, 0x02])
    tcp += (64240).to_bytes(2, "big")
    tcp += b"\x00\x00"
    tcp += b"\x00\x00"
    tcp += bytes.fromhex("020405b4")
    tcp[16:18] = tcp_checksum_ipv4(
        "192.0.2.10", "198.51.100.20", bytes(tcp)
    ).to_bytes(2, "big")

    ipv4 = bytearray()
    ipv4 += bytes([0x45, 0x00])
    ipv4 += (20 + len(tcp)).to_bytes(2, "big")
    ipv4 += (0x1234).to_bytes(2, "big")
    ipv4 += (0x4000).to_bytes(2, "big")
    ipv4 += bytes([64, 6])
    ipv4 += b"\x00\x00"
    ipv4 += source_ip
    ipv4 += destination_ip
    ipv4[10:12] = internet_checksum(bytes(ipv4)).to_bytes(2, "big")

    ethernet = bytes.fromhex("0200000000020200000000010800")
    return ethernet + bytes(ipv4) + bytes(tcp)


def format_hex(data: bytes) -> str:
    rows = [
        data[offset : offset + 16].hex(" ")
        for offset in range(0, len(data), 16)
    ]
    return "# Ethernet II + IPv4 + TCP SYN, FCS 제외\n" + "\n".join(rows) + "\n"


def main() -> int:
    target = EXERCISE / "fixtures/syn-frame.hex"
    target.write_text(format_hex(build_syn_frame()), encoding="utf-8")
    print(target.relative_to(EXERCISE))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
