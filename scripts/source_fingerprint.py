#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parents[1]
EXCLUDED_PARTS = {".git", ".guide", ".workspaces", "__pycache__", ".pytest_cache"}
EXCLUDED_SUFFIXES = {".pyc", ".pyo", ".log", ".tmp"}


def source_files(root: Path = ROOT) -> Iterable[Path]:
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.is_symlink():
            continue
        relative = path.relative_to(root)
        if any(part in EXCLUDED_PARTS for part in relative.parts):
            continue
        if path.suffix in EXCLUDED_SUFFIXES:
            continue
        yield path


def fingerprint(root: Path = ROOT) -> tuple[str, int]:
    digest = hashlib.sha256()
    count = 0
    for path in source_files(root):
        relative = path.relative_to(root).as_posix()
        mode = path.stat().st_mode & 0o777
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(f"{mode:o}".encode("ascii"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
        count += 1
    return digest.hexdigest(), count


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    value, count = fingerprint()
    if args.json:
        print(json.dumps({"sha256": value, "files": count}, sort_keys=True))
    else:
        print(value)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
