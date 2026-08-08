#!/usr/bin/env python3
"""Hash source bytes, modes, directories, and symlink targets deterministically."""

from __future__ import annotations

import hashlib
import os
import stat
import sys
from pathlib import Path

EXCLUDED_ROOT_NAMES = {".git", ".guide"}


def add_field(digest, value: bytes) -> None:
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
        dirnames.sort()
        filenames.sort()
        entries = [*(current / name for name in dirnames), *(current / name for name in filenames)]
        for path in sorted(entries, key=lambda item: item.relative_to(root).as_posix()):
            relative = path.relative_to(root).as_posix().encode()
            metadata = path.lstat()
            mode = f"{stat.S_IMODE(metadata.st_mode):o}".encode()
            if path.is_symlink():
                kind, payload = b"symlink", os.readlink(path).encode()
            elif path.is_file():
                kind, payload = b"file", hashlib.sha256(path.read_bytes()).digest()
            elif path.is_dir():
                kind, payload = b"dir", b""
            else:
                kind, payload = b"other", b""
            for field in (relative, kind, mode, payload):
                add_field(digest, field)
            count += 1
    return digest.hexdigest(), count


def main() -> int:
    root = Path(sys.argv[1]).resolve()
    value, count = fingerprint(root)
    print(f"sha256:{value};entries:{count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
