#!/usr/bin/env python3
"""Deterministic, non-following fingerprints for guide source trees."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import stat
from dataclasses import dataclass
from pathlib import Path
from typing import Collection, Iterator

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_EXCLUDED_DIRS = frozenset({'.git', '.guide', '.workspace', '__pycache__'})
DEFAULT_EXCLUDED_FILES = frozenset({'.DS_Store'})


class UnsafeTreeError(RuntimeError):
    """Raised when a tree contains a link or non-regular filesystem entry."""


@dataclass(frozen=True)
class FileRecord:
    path: Path
    relative: str
    mode: int


@dataclass(frozen=True)
class DirectoryRecord:
    relative: str
    mode: int


def _walk(
    root: Path,
    excluded_dirs: Collection[str],
    excluded_files: Collection[str],
) -> Iterator[FileRecord]:
    root = root.resolve(strict=True)
    for directory, dirnames, filenames in os.walk(root, topdown=True, followlinks=False):
        directory_path = Path(directory)
        at_root = directory_path == root
        retained_dirs: list[str] = []
        for name in sorted(dirnames):
            path = directory_path / name
            relative = path.relative_to(root).as_posix()
            mode = path.lstat().st_mode
            if stat.S_ISLNK(mode):
                raise UnsafeTreeError(f'symlink directory is not allowed: {relative}')
            if not stat.S_ISDIR(mode):
                raise UnsafeTreeError(f'non-directory entry encountered while walking: {relative}')
            if name in excluded_dirs:
                if name == '__pycache__' or at_root:
                    continue
                raise UnsafeTreeError(f'reserved excluded directory below repository root: {relative}')
            retained_dirs.append(name)
        dirnames[:] = retained_dirs

        for name in sorted(filenames):
            path = directory_path / name
            relative = path.relative_to(root).as_posix()
            mode = path.lstat().st_mode
            if stat.S_ISLNK(mode):
                raise UnsafeTreeError(f'symlink file is not allowed: {relative}')
            if not stat.S_ISREG(mode):
                raise UnsafeTreeError(f'non-regular file is not allowed: {relative}')
            if name in excluded_files:
                continue
            if name in excluded_dirs:
                if name != '.git' or not at_root:
                    raise UnsafeTreeError(f'excluded directory name is a file: {relative}')
                continue
            yield FileRecord(path=path, relative=relative, mode=stat.S_IMODE(mode))


def source_records(
    root: Path = ROOT,
    *,
    excluded_dirs: Collection[str] = DEFAULT_EXCLUDED_DIRS,
    excluded_files: Collection[str] = DEFAULT_EXCLUDED_FILES,
) -> list[FileRecord]:
    """Return sorted regular files without following any symlink."""
    return sorted(
        _walk(root, excluded_dirs, excluded_files),
        key=lambda item: item.relative,
    )


def directory_records(
    root: Path = ROOT,
    *,
    excluded_dirs: Collection[str] = DEFAULT_EXCLUDED_DIRS,
) -> list[DirectoryRecord]:
    root = root.resolve(strict=True)
    records: list[DirectoryRecord] = []
    for directory, dirnames, _filenames in os.walk(root, topdown=True, followlinks=False):
        directory_path = Path(directory)
        at_root = directory_path == root
        retained: list[str] = []
        for name in sorted(dirnames):
            path = directory_path / name
            relative = path.relative_to(root).as_posix()
            mode = path.lstat().st_mode
            if stat.S_ISLNK(mode):
                raise UnsafeTreeError(f'symlink directory is not allowed: {relative}')
            if not stat.S_ISDIR(mode):
                raise UnsafeTreeError(f'non-directory entry encountered while walking: {relative}')
            if name in excluded_dirs:
                if name == '__pycache__' or at_root:
                    continue
                raise UnsafeTreeError(f'reserved excluded directory below repository root: {relative}')
            retained.append(name)
            records.append(DirectoryRecord(relative=relative, mode=stat.S_IMODE(mode)))
        dirnames[:] = retained
    return sorted(records, key=lambda item: item.relative)


def fingerprint(
    root: Path = ROOT,
    *,
    excluded_dirs: Collection[str] = DEFAULT_EXCLUDED_DIRS,
    excluded_files: Collection[str] = DEFAULT_EXCLUDED_FILES,
) -> tuple[str, int]:
    digest = hashlib.sha256()
    files = source_records(
        root,
        excluded_dirs=excluded_dirs,
        excluded_files=excluded_files,
    )
    directories = directory_records(root, excluded_dirs=excluded_dirs)
    digest.update(b'platform-engineering-source-tree-v2\0')

    def frame(value: bytes) -> None:
        digest.update(len(value).to_bytes(8, 'big'))
        digest.update(value)

    digest.update(len(directories).to_bytes(8, 'big'))
    for record in directories:
        frame(b'directory')
        frame(record.relative.encode('utf-8'))
        frame(f'{record.mode:o}'.encode('ascii'))

    digest.update(len(files).to_bytes(8, 'big'))
    for record in files:
        frame(b'file')
        frame(record.relative.encode('utf-8'))
        frame(f'{record.mode:o}'.encode('ascii'))
        flags = os.O_RDONLY
        if hasattr(os, 'O_NOFOLLOW'):
            flags |= os.O_NOFOLLOW
        try:
            descriptor = os.open(record.path, flags)
        except OSError as exc:
            raise UnsafeTreeError(f'cannot safely open source file: {record.relative}: {exc}') from exc
        try:
            metadata = os.fstat(descriptor)
            if not stat.S_ISREG(metadata.st_mode):
                raise UnsafeTreeError(f'source changed to a non-regular file: {record.relative}')
            if stat.S_IMODE(metadata.st_mode) != record.mode:
                raise UnsafeTreeError(f'source mode changed while fingerprinting: {record.relative}')
            size = metadata.st_size
            digest.update(size.to_bytes(8, 'big'))
            consumed = 0
            with os.fdopen(descriptor, 'rb') as stream:
                descriptor = -1
                while chunk := stream.read(1024 * 1024):
                    consumed += len(chunk)
                    digest.update(chunk)
            if consumed != size:
                raise UnsafeTreeError(f'source size changed while fingerprinting: {record.relative}')
        finally:
            if descriptor >= 0:
                os.close(descriptor)
    return digest.hexdigest(), len(files)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--json', action='store_true')
    args = parser.parse_args()
    try:
        value, count = fingerprint()
    except (OSError, UnsafeTreeError) as exc:
        print(f'ERROR: {exc}', file=os.sys.stderr)
        return 1
    if args.json:
        print(json.dumps({'sha256': value, 'files': count}, ensure_ascii=False))
    else:
        print(value)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
