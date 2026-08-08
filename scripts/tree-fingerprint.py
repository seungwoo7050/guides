#!/usr/bin/env python3
"""Source bytes, modes, directories and symlink targets의 결정적 지문을 계산합니다."""

from __future__ import annotations

import hashlib
import os
import stat
import sys
from pathlib import Path

EXCLUDED_ROOT_NAMES = {".git", ".guide"}
EXCLUDED_DIRECTORY_NAMES = {
    ".pytest_cache",
    ".venv",
    "__pycache__",
    "build",
    "workspace",
}
EXCLUDED_FILE_SUFFIXES = {".pyc", ".pyo"}


def add_field(digest: "hashlib._Hash", value: bytes) -> None:
    digest.update(len(value).to_bytes(8, "big"))
    digest.update(value)


def fingerprint(root: Path) -> tuple[str, int]:
    digest = hashlib.sha256()
    count = 0
    for dirpath, dirnames, filenames in os.walk(root, topdown=True, followlinks=False):
        current = Path(dirpath)
        if current == root:
            dirnames[:] = [name for name in dirnames if name not in EXCLUDED_ROOT_NAMES]
            filenames[:] = [name for name in filenames if name not in EXCLUDED_ROOT_NAMES]
        dirnames[:] = [name for name in dirnames if name not in EXCLUDED_DIRECTORY_NAMES]
        filenames[:] = [
            name for name in filenames if Path(name).suffix not in EXCLUDED_FILE_SUFFIXES
        ]
        dirnames.sort()
        filenames.sort()
        entries = [*(current / name for name in dirnames), *(current / name for name in filenames)]
        for path in sorted(entries, key=lambda item: item.relative_to(root).as_posix()):
            metadata = path.lstat()
            if path.is_symlink():
                kind, payload = b"symlink", os.readlink(path).encode()
            elif path.is_file():
                kind, payload = b"file", hashlib.sha256(path.read_bytes()).digest()
            elif path.is_dir():
                kind, payload = b"dir", b""
            else:
                kind, payload = b"other", b""
            for field in (
                path.relative_to(root).as_posix().encode(),
                kind,
                f"{stat.S_IMODE(metadata.st_mode):o}".encode(),
                payload,
            ):
                add_field(digest, field)
            count += 1
    return digest.hexdigest(), count


def main() -> int:
    value, count = fingerprint(Path(sys.argv[1]).resolve())
    print(f"sha256:{value};entries:{count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
