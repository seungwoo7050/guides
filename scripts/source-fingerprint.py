#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import stat
from pathlib import Path

EXCLUDED_DIRS = {".git", ".guide", "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache"}
EXCLUDED_NAMES = {".DS_Store"}


def excluded(relative: Path) -> bool:
    if any(part in EXCLUDED_DIRS or part == "workspace" for part in relative.parts):
        return True
    if relative.name in EXCLUDED_NAMES or relative.suffix in {".pyc", ".pyo"}:
        return True
    return False


def fingerprint(root: Path) -> tuple[str, int]:
    root = root.resolve()
    digest = hashlib.sha256()
    count = 0
    for path in sorted(root.rglob("*"), key=lambda item: item.relative_to(root).as_posix()):
        relative = path.relative_to(root)
        if excluded(relative):
            continue
        metadata = path.lstat()
        mode = stat.S_IMODE(metadata.st_mode)
        if path.is_symlink():
            kind = "symlink"
            payload = os.readlink(path).encode("utf-8", "surrogateescape")
        elif path.is_file():
            kind = "file"
            payload = path.read_bytes()
        elif path.is_dir():
            kind = "directory"
            payload = b""
        else:
            kind = "other"
            payload = b""
        digest.update(relative.as_posix().encode("utf-8"))
        digest.update(b"\0")
        digest.update(kind.encode("ascii"))
        digest.update(b"\0")
        digest.update(f"{mode:o}".encode("ascii"))
        digest.update(b"\0")
        digest.update(payload)
        digest.update(b"\0")
        count += 1
    return digest.hexdigest(), count


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    value, count = fingerprint(args.root)
    if args.json:
        print(json.dumps({"source_sha256": value, "entries": count}, sort_keys=True))
    else:
        print(value)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
