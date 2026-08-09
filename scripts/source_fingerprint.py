#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
IGNORE_DIRS = {'.git', '.guide', '.workspace', '__pycache__'}
IGNORE_SUFFIXES = {'.pyc', '.pyo', '.log'}


def main() -> int:
    digest = hashlib.sha256()
    for path in sorted(ROOT.rglob('*')):
        relative = path.relative_to(ROOT)
        if any(part in IGNORE_DIRS for part in relative.parts):
            continue
        if path.is_dir() or path.suffix in IGNORE_SUFFIXES:
            continue
        if path.is_symlink():
            digest.update(b'L\0')
            digest.update(str(relative).encode())
            digest.update(b'\0')
            digest.update(os.readlink(path).encode())
            digest.update(b'\0')
            continue
        digest.update(b'F\0')
        digest.update(str(relative).encode())
        digest.update(b'\0')
        digest.update(path.read_bytes())
        digest.update(b'\0')
    print(digest.hexdigest())
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
