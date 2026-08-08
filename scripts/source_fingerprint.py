#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import os
import stat
from pathlib import Path

EXCLUDED_DIRECTORIES = {".git", ".guide", "target", "__pycache__"}


def rows(root: Path) -> list[bytes]:
    result: list[bytes] = []
    for current, directory_names, file_names in os.walk(
        root, topdown=True, followlinks=False
    ):
        current_path = Path(current)
        kept_directories: list[str] = []
        for name in sorted(directory_names):
            if name in EXCLUDED_DIRECTORIES:
                continue
            path = current_path / name
            relative = path.relative_to(root).as_posix()
            mode = stat.S_IMODE(path.lstat().st_mode)
            if path.is_symlink():
                target = os.readlink(path).encode("utf-8", "surrogateescape")
                result.append(
                    b"LINK\0" + f"{mode:04o}".encode() + b"\0"
                    + relative.encode("utf-8", "surrogateescape") + b"\0"
                    + target + b"\0"
                )
            else:
                result.append(f"DIR\0{mode:04o}\0{relative}\0".encode())
                kept_directories.append(name)
        directory_names[:] = kept_directories
        for name in sorted(file_names):
            path = current_path / name
            if path.suffix == ".pyc":
                continue
            relative = path.relative_to(root).as_posix()
            mode = stat.S_IMODE(path.lstat().st_mode)
            if path.is_symlink():
                payload = os.readlink(path).encode("utf-8", "surrogateescape")
                kind = b"LINK"
            elif path.is_file():
                payload = hashlib.sha256(path.read_bytes()).hexdigest().encode()
                kind = b"FILE"
            else:
                payload = b""
                kind = b"OTHER"
            result.append(
                kind + b"\0" + f"{mode:04o}".encode() + b"\0"
                + relative.encode("utf-8", "surrogateescape") + b"\0"
                + payload + b"\0"
            )
    return sorted(result)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", nargs="?", type=Path)
    parser.add_argument("--manifest", type=Path)
    arguments = parser.parse_args()
    root = (arguments.root or Path(__file__).resolve().parents[1]).resolve()
    manifest_rows = rows(root)
    digest = hashlib.sha256(b"".join(manifest_rows)).hexdigest()
    if arguments.manifest:
        arguments.manifest.write_bytes(b"\n".join(manifest_rows) + b"\n")
    print(digest)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
