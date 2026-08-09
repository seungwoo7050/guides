#!/usr/bin/env python3
"""Compute a deterministic fingerprint of source bytes, modes and symlinks."""

from __future__ import annotations

import argparse
import hashlib
import os
from pathlib import Path

IGNORED_PARTS = {'.git', '.guide', 'workspace', '__pycache__', '.pytest_cache'}
IGNORED_SUFFIXES = {'.pyc', '.pyo', '.log'}


def included(relative: Path) -> bool:
    if any(part in IGNORED_PARTS for part in relative.parts):
        return False
    if relative.suffix in IGNORED_SUFFIXES:
        return False
    if relative.name in {'.DS_Store', '.coverage'}:
        return False
    return True


def source_fingerprint(root: Path) -> str:
    root = root.resolve()
    digest = hashlib.sha256()
    entries: list[Path] = []
    for path in root.rglob('*'):
        relative = path.relative_to(root)
        if included(relative):
            entries.append(path)
    for path in sorted(entries, key=lambda item: item.relative_to(root).as_posix()):
        relative = path.relative_to(root)
        stat = path.lstat()
        digest.update(relative.as_posix().encode('utf-8'))
        digest.update(b'\0')
        if path.is_dir() and not path.is_symlink():
            # Archive tools do not preserve setgid and all directory permission bits
            # consistently. Directory existence is source; directory mode is not.
            digest.update(b'D\0')
        elif path.is_symlink():
            digest.update(b'L\0')
            digest.update(oct(stat.st_mode & 0o7777).encode('ascii'))
            digest.update(b'\0')
            digest.update(os.readlink(path).encode('utf-8'))
        elif path.is_file():
            digest.update(b'F\0')
            digest.update(oct(stat.st_mode & 0o7777).encode('ascii'))
            digest.update(b'\0')
            digest.update(path.read_bytes())
        else:
            digest.update(b'O\0')
            digest.update(oct(stat.st_mode & 0o7777).encode('ascii'))
        digest.update(b'\0')
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('root', nargs='?', default='.')
    args = parser.parse_args()
    print(source_fingerprint(Path(args.root)))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
