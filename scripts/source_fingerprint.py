#!/usr/bin/env python3
"""Compute a stable fingerprint of the distributed-systems guide source tree."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
EXCLUDED_DIRS = {".git", ".guide", ".workspace", "__pycache__"}
EXCLUDED_SUFFIXES = {".pyc", ".pyo", ".log"}


def source_files() -> list[Path]:
    files: list[Path] = []
    for path in ROOT.rglob("*"):
        relative = path.relative_to(ROOT)
        if any(part in EXCLUDED_DIRS for part in relative.parts):
            continue
        if path.is_symlink():
            raise ValueError(f"source symlink is not allowed: {relative}")
        if not path.is_file() or path.suffix in EXCLUDED_SUFFIXES:
            continue
        files.append(path)
    return sorted(files, key=lambda p: p.relative_to(ROOT).as_posix())


def fingerprint() -> dict[str, Any]:
    digest = hashlib.sha256()
    records: list[dict[str, Any]] = []
    for path in source_files():
        relative = path.relative_to(ROOT).as_posix()
        data = path.read_bytes()
        mode = os.stat(path).st_mode & 0o777
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(f"{mode:o}".encode("ascii"))
        digest.update(b"\0")
        digest.update(data)
        digest.update(b"\0")
        records.append({
            "path": relative,
            "mode": f"{mode:o}",
            "size": len(data),
            "sha256": hashlib.sha256(data).hexdigest(),
        })
    return {
        "source_sha256": digest.hexdigest(),
        "file_count": len(records),
        "files": records,
    }


def main() -> int:
    print(json.dumps(fingerprint(), ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
