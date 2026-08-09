#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXCLUDED_DIRS = {'.git', '.guide', 'build', 'out', '__pycache__'}
EXCLUDED_SUFFIXES = {'.pyc', '.log'}


def iter_sources(root: Path):
    for path in sorted(root.rglob('*')):
        if not path.is_file():
            continue
        rel = path.relative_to(root)
        if any(part in EXCLUDED_DIRS for part in rel.parts):
            continue
        if path.suffix in EXCLUDED_SUFFIXES:
            continue
        yield rel, path


def fingerprint(root: Path = ROOT) -> tuple[str, int]:
    digest = hashlib.sha256()
    count = 0
    for rel, path in iter_sources(root):
        data = path.read_bytes()
        digest.update(rel.as_posix().encode('utf-8'))
        digest.update(b'\0')
        digest.update(str(len(data)).encode('ascii'))
        digest.update(b'\0')
        digest.update(data)
        digest.update(b'\0')
        count += 1
    return digest.hexdigest(), count


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--json', action='store_true')
    parser.add_argument('--check-file', type=Path)
    args = parser.parse_args()
    value, count = fingerprint()
    if args.check_file:
        payload = json.loads(args.check_file.read_text(encoding='utf-8'))
        expected = payload.get('source_sha256')
        if expected != value:
            print(f'SOURCE_FINGERPRINT_MISMATCH expected={expected} actual={value}')
            return 1
    if args.json:
        print(json.dumps({'source_sha256': value, 'source_file_count': count}, indent=2))
    else:
        print(value)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
