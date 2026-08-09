#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
EXCLUDED_DIRS = {'.git', '.guide', 'build', 'out', '__pycache__', 'workspace'}
EXCLUDED_SUFFIXES = {'.pyc', '.log', '.spv', '.dxil', '.metallib'}


def excluded(relative: Path) -> bool:
    return any(
        part in EXCLUDED_DIRS or part.startswith('build-') or part.startswith('.workspace.')
        for part in relative.parts
    ) or relative.suffix in EXCLUDED_SUFFIXES


def iter_sources(root: Path):
    for path in sorted(root.rglob('*')):
        if not path.is_file():
            continue
        rel = path.relative_to(root)
        if excluded(rel):
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


def git_identity(root: Path = ROOT) -> tuple[str, str, str]:
    head = subprocess.check_output(
        ['git', 'rev-parse', 'HEAD'], cwd=root, text=True
    ).strip()
    branch = subprocess.check_output(
        ['git', 'branch', '--show-current'], cwd=root, text=True
    ).strip()
    raw_index = subprocess.check_output(
        ['git', 'rev-parse', '--git-path', 'index'], cwd=root, text=True
    ).strip()
    index = Path(raw_index)
    if not index.is_absolute():
        index = root / index
    return head, branch, hashlib.sha256(index.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--json', action='store_true')
    parser.add_argument('--check-file', type=Path)
    args = parser.parse_args()
    value, count = fingerprint()
    if args.check_file:
        payload = json.loads(args.check_file.read_text(encoding='utf-8'))
        head, branch, index_hash = git_identity()
        expected = {
            'prepared_schema_version': 2,
            'guide': 'computer-graphics',
            'source_sha256': value,
            'source_file_count': count,
            'head': head,
            'branch': branch,
            'index_sha256': index_hash,
        }
        mismatches = {
            key: {'expected': expected_value, 'actual': payload.get(key)}
            for key, expected_value in expected.items()
            if payload.get(key) != expected_value
        }
        if mismatches:
            print('SOURCE_MARKER_MISMATCH ' + json.dumps(mismatches, sort_keys=True))
            return 1
    if args.json:
        print(json.dumps({'source_sha256': value, 'source_file_count': count}, indent=2))
    else:
        print(value)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
