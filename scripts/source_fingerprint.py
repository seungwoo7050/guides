#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import stat
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXCLUDED_PARTS = {".git", ".guide", "__pycache__"}
EXCLUDED_FILES = {".DS_Store"}
CAPSTONE_WORK = Path("projects/synthetic-service-security-review/work")
FINGERPRINT_VERSION = 2


def included(path: Path) -> bool:
    rel = path.relative_to(ROOT)
    if any(part in EXCLUDED_PARTS for part in rel.parts):
        return False
    if path.name in EXCLUDED_FILES:
        return False
    if rel == CAPSTONE_WORK or CAPSTONE_WORK in rel.parents:
        return False
    if len(rel.parts) >= 3 and rel.parts[0] == "exercises" and rel.parts[2] == "work":
        return False
    return path.is_file() or path.is_symlink()


def fingerprint() -> str:
    digest = hashlib.sha256()
    digest.update(f"cybersecurity-source-v{FINGERPRINT_VERSION}\0".encode("ascii"))
    paths = sorted(
        (path for path in ROOT.rglob("*") if included(path)),
        key=lambda path: path.relative_to(ROOT).as_posix(),
    )
    for path in paths:
        rel = path.relative_to(ROOT).as_posix()
        rel_bytes = rel.encode("utf-8")
        metadata = path.lstat()
        if stat.S_ISLNK(metadata.st_mode):
            raise ValueError(f"source symlink는 허용하지 않습니다: {rel}")
        if not stat.S_ISREG(metadata.st_mode):
            continue
        mode = f"{stat.S_IMODE(metadata.st_mode):04o}".encode("ascii")
        data = path.read_bytes()
        digest.update(len(rel_bytes).to_bytes(8, "big"))
        digest.update(rel_bytes)
        digest.update(len(mode).to_bytes(8, "big"))
        digest.update(mode)
        digest.update(len(data).to_bytes(8, "big"))
        digest.update(data)
    return digest.hexdigest()


def check_marker(path: Path) -> None:
    candidate = path if path.is_absolute() else ROOT / path
    try:
        relative = candidate.relative_to(ROOT)
    except ValueError as exc:
        raise ValueError(f"prepare marker가 저장소 밖입니다: {path}") from exc
    if ".." in relative.parts:
        raise ValueError(f"prepare marker 경로에 상위 이동이 있습니다: {path}")
    current = ROOT
    for part in relative.parts:
        current = current / part
        if current.is_symlink():
            raise ValueError(f"prepare marker 경로가 symlink입니다: {current}")
    if not candidate.is_file():
        raise ValueError(f"prepare marker가 없습니다: {candidate}")
    try:
        marker = json.loads(candidate.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"prepare marker를 읽을 수 없습니다: {exc}") from exc
    if marker.get("guide") != "cybersecurity":
        raise ValueError("prepare marker의 guide가 cybersecurity가 아닙니다.")
    if marker.get("fingerprint_version") != FINGERPRINT_VERSION:
        raise ValueError("prepare marker의 fingerprint version이 다릅니다. ./prepare.sh를 다시 실행하십시오.")
    expected = marker.get("source_sha256")
    if not isinstance(expected, str) or len(expected) != 64:
        raise ValueError("prepare marker의 source_sha256이 유효하지 않습니다.")
    actual = fingerprint()
    if actual != expected:
        raise ValueError(
            "prepare 이후 source가 변경됐습니다. ./prepare.sh를 다시 실행하십시오.\n"
            f"expected={expected}\nactual={actual}"
        )
    print(f"SOURCE OK {actual}")


def main() -> int:
    parser = argparse.ArgumentParser(description="가이드 source fingerprint를 계산하거나 marker와 비교합니다.")
    parser.add_argument("--check-marker", type=Path)
    args = parser.parse_args()
    try:
        if args.check_marker is not None:
            check_marker(args.check_marker)
        else:
            print(fingerprint())
    except (OSError, ValueError) as exc:
        print(f"SOURCE ERROR: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
