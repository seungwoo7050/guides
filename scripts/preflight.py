#!/usr/bin/env python3
"""최종 네트워크 가이드 구조와 휴대 가능한 실행 환경을 확인합니다."""

from __future__ import annotations

from pathlib import Path
import os
import sys

ROOT = Path(__file__).resolve().parents[1]

if sys.version_info < (3, 12):
    raise SystemExit("Python 3.12 이상이 필요합니다")

required_files = [
    ROOT / "prepare.sh",
    ROOT / "verify.sh",
    ROOT / "docs/00-roadmap.md",
    ROOT / "docs/01-link-and-path/01-layers-encapsulation-and-path.md",
    ROOT / "docs/02-internetworking/01-ip-addressing-subnets-and-lpm.md",
    ROOT / "docs/03-transport/01-udp-and-tcp-service-contracts.md",
    ROOT / "docs/04-application-security-and-evidence/01-dns-http-tls-and-quic.md",
    ROOT / "docs/04-application-security-and-evidence/02-network-failure-localization.md",
    ROOT / "docs/90-standards-map.md",
    ROOT / "exercises/protocol-inspector/fixtures/syn-frame.hex",
    ROOT / "exercises/protocol-inspector/reference/protocol_inspector/__init__.py",
    ROOT / "exercises/protocol-inspector/skeleton/protocol_inspector/__init__.py",
    ROOT / "exercises/packet-observation/fixtures/handshake.txt",
    ROOT / "exercises/path-diagnosis/fixtures/healthy.json",
    ROOT / "exercises/path-diagnosis/reference/path_diagnosis/__init__.py",
    ROOT / "exercises/path-diagnosis/skeleton/path_diagnosis/__init__.py",
    ROOT / "examples/window-model/window_model.py",
]
missing = [str(path.relative_to(ROOT)) for path in required_files if not path.is_file()]
if missing:
    raise SystemExit("필수 파일이 없습니다: " + ", ".join(missing))

forbidden_paths = [
    ROOT / "docs/01-layers-encapsulation-and-path.md",
    ROOT / "docs/02-ethernet-mac-and-switching.md",
    ROOT / "docs/03-arp-and-neighbor-discovery.md",
    ROOT / "docs/04-ip-addressing-subnets-and-lpm.md",
    ROOT / "docs/05-ip-forwarding-mtu-and-icmp.md",
    ROOT / "docs/06-nat-connection-tracking-and-firewalls.md",
    ROOT / "docs/07-routing-algorithms-and-protocols.md",
    ROOT / "docs/08-udp-and-tcp-service-contracts.md",
    ROOT / "docs/09-tcp-connection-state-and-sequences.md",
    ROOT / "docs/10-retransmission-rtt-and-sliding-windows.md",
    ROOT / "docs/11-flow-and-congestion-control.md",
    ROOT / "docs/12-dns-http-tls-and-quic.md",
    ROOT / "reference/troubleshooting-path.md",
    ROOT / "reference/standards-map.md",
]
remaining = [str(path.relative_to(ROOT)) for path in forbidden_paths if path.exists()]
if remaining:
    raise SystemExit(
        "prepare가 끝나지 않았습니다. 이전 경로가 남았습니다: " + ", ".join(remaining)
    )

not_executable = [
    str(path.relative_to(ROOT))
    for path in (ROOT / "prepare.sh", ROOT / "verify.sh")
    if not os.access(path, os.X_OK)
]
if not_executable:
    raise SystemExit("실행 권한이 없습니다: " + ", ".join(not_executable))

print(
    "최종 휴대 가능 환경을 확인했습니다: "
    f"Python {sys.version.split()[0]}, 제3자 Python 패키지 없음"
)
