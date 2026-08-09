#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import stat
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXCLUDED_DIRS = {'.git', '.guide', '.workspace', '__pycache__'}
EXCLUDED_FILES = {'.DS_Store'}


def source_files(root: Path = ROOT) -> list[Path]:
    files: list[Path] = []
    for path in root.rglob('*'):
        rel = path.relative_to(root)
        if any(part in EXCLUDED_DIRS for part in rel.parts):
            continue
        if path.is_file() and path.name not in EXCLUDED_FILES:
            files.append(path)
    return sorted(files, key=lambda p: p.relative_to(root).as_posix())


def fingerprint(root: Path = ROOT) -> tuple[str, int]:
    digest = hashlib.sha256()
    files = source_files(root)
    for path in files:
        rel = path.relative_to(root).as_posix()
        mode = stat.S_IMODE(path.stat().st_mode)
        digest.update(rel.encode('utf-8'))
        digest.update(b'\0')
        digest.update(f'{mode:o}'.encode('ascii'))
        digest.update(b'\0')
        digest.update(path.read_bytes())
        digest.update(b'\0')
    return digest.hexdigest(), len(files)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--json', action='store_true')
    args = parser.parse_args()
    value, count = fingerprint()
    if args.json:
        print(json.dumps({'sha256': value, 'files': count}, ensure_ascii=False))
    else:
        print(value)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
