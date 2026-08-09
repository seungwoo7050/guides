#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXCLUDED_DIRS = {'.git', '.guide', '__pycache__'}
EXCLUDED_FILES = {'.DS_Store'}


def main() -> int:
    digest = hashlib.sha256()
    files: list[Path] = []
    for path in ROOT.rglob('*'):
        rel = path.relative_to(ROOT)
        if any(part in EXCLUDED_DIRS for part in rel.parts):
            continue
        if path.name in EXCLUDED_FILES or not path.is_file():
            continue
        files.append(path)
    for path in sorted(files, key=lambda p: p.relative_to(ROOT).as_posix()):
        rel = path.relative_to(ROOT).as_posix().encode('utf-8')
        mode = oct(path.stat().st_mode & 0o777).encode('ascii')
        data = path.read_bytes()
        digest.update(len(rel).to_bytes(8, 'big'))
        digest.update(rel)
        digest.update(mode)
        digest.update(len(data).to_bytes(8, 'big'))
        digest.update(data)
    print(digest.hexdigest())
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
