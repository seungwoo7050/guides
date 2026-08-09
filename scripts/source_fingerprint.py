#!/usr/bin/env python3
"""Create or verify a deterministic fingerprint of guide source files."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import stat
import sys
from pathlib import Path
from typing import Iterable

EXCLUDED_NAMES = {
    ".git",
    ".guide",
    ".venv",
    "__pycache__",
    "build",
    "workspace",
}
EXCLUDED_SUFFIXES = {".pyc", ".log"}


def is_excluded(relative: Path) -> bool:
    if any(part in EXCLUDED_NAMES for part in relative.parts):
        return True
    return relative.suffix in EXCLUDED_SUFFIXES


def iter_entries(root: Path) -> Iterable[Path]:
    for current, directories, filenames in os.walk(root, topdown=True, followlinks=False):
        current_path = Path(current)
        relative_dir = current_path.relative_to(root)
        directories[:] = sorted(
            name
            for name in directories
            if not is_excluded(relative_dir / name)
        )
        for name in sorted(filenames):
            path = current_path / name
            relative = path.relative_to(root)
            if not is_excluded(relative):
                yield path
        # os.walk does not yield directory symlinks after pruning in a portable way.
        for name in sorted(os.listdir(current_path)):
            path = current_path / name
            if path.is_symlink() and path.is_dir():
                relative = path.relative_to(root)
                if not is_excluded(relative):
                    yield path


def calculate(root: Path) -> dict[str, object]:
    digest = hashlib.sha256()
    files = 0
    symlinks = 0
    for path in sorted(iter_entries(root), key=lambda item: item.relative_to(root).as_posix()):
        relative = path.relative_to(root).as_posix()
        info = path.lstat()
        mode = stat.S_IMODE(info.st_mode)
        if path.is_symlink():
            kind = "symlink"
            payload = os.readlink(path).encode("utf-8", errors="surrogateescape")
            symlinks += 1
        elif path.is_file():
            kind = "file"
            payload = path.read_bytes()
            files += 1
        else:
            continue
        digest.update(kind.encode())
        digest.update(b"\0")
        digest.update(f"{mode:o}".encode())
        digest.update(b"\0")
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(payload)
        digest.update(b"\0")
    return {
        "algorithm": "sha256",
        "source_sha256": digest.hexdigest(),
        "files": files,
        "symlinks": symlinks,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--write", type=Path)
    group.add_argument("--check", type=Path)
    group.add_argument("--print", action="store_true", dest="print_result")
    args = parser.parse_args()

    root = args.root.resolve()
    result = calculate(root)
    result.update({
        "guide": "embedded-systems",
        "python": ".".join(map(str, sys.version_info[:3])),
    })

    if args.write is not None:
        marker = args.write if args.write.is_absolute() else root / args.write
        marker.parent.mkdir(parents=True, exist_ok=True)
        marker.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(f"PREPARED {marker}")
        print(f"SOURCE SHA256 {result['source_sha256']}")
        return 0

    if args.check is not None:
        marker = args.check if args.check.is_absolute() else root / args.check
        try:
            expected = json.loads(marker.read_text(encoding="utf-8"))
        except FileNotFoundError:
            print(f"ERROR: 준비 marker가 없습니다: {marker}", file=sys.stderr)
            return 1
        except (OSError, json.JSONDecodeError) as exc:
            print(f"ERROR: marker를 읽을 수 없습니다: {exc}", file=sys.stderr)
            return 1
        if expected.get("source_sha256") != result["source_sha256"]:
            print("ERROR: prepare 뒤 source가 변경됐습니다. ./prepare.sh를 다시 실행하십시오.", file=sys.stderr)
            print(f"EXPECTED {expected.get('source_sha256')}", file=sys.stderr)
            print(f"ACTUAL   {result['source_sha256']}", file=sys.stderr)
            return 1
        print(f"FINGERPRINT OK {result['source_sha256']}")
        return 0

    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
