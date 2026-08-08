#!/usr/bin/env python3
"""Create stable source manifests and fingerprints for guide-algorithms."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import stat
import sys

IGNORED_PARTS = {
    ".git",
    ".guide",
    ".pytest_cache",
    ".venv",
    "__pycache__",
    "build",
    "dist",
    "htmlcov",
    "workspace",
}
IGNORED_NAMES = {".DS_Store"}


def file_digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def records(root: Path) -> list[dict[str, object]]:
    result: list[dict[str, object]] = []
    for directory, names, files in os.walk(root, topdown=True, followlinks=False):
        base = Path(directory)
        traversable: list[str] = []
        for name in sorted(names):
            if name in IGNORED_PARTS or name in IGNORED_NAMES:
                continue
            path = base / name
            metadata = path.lstat()
            relative = path.relative_to(root).as_posix()
            if stat.S_ISLNK(metadata.st_mode):
                result.append(
                    {
                        "path": relative,
                        "mode": stat.S_IMODE(metadata.st_mode),
                        "type": "symlink",
                        "target": os.readlink(path),
                    }
                )
            else:
                result.append(
                    {
                        "path": relative,
                        "mode": stat.S_IMODE(metadata.st_mode),
                        "type": "directory",
                    }
                )
                traversable.append(name)
        names[:] = traversable
        for name in sorted(files):
            if name in IGNORED_NAMES or name.endswith((".pyc", ".pyo")):
                continue
            path = base / name
            relative = path.relative_to(root).as_posix()
            metadata = path.lstat()
            record: dict[str, object] = {
                "path": relative,
                "mode": stat.S_IMODE(metadata.st_mode),
            }
            if stat.S_ISREG(metadata.st_mode):
                record.update(
                    type="file",
                    size=metadata.st_size,
                    sha256=file_digest(path),
                )
            elif stat.S_ISLNK(metadata.st_mode):
                record.update(type="symlink", target=os.readlink(path))
            else:
                record.update(type="special", device=metadata.st_rdev)
            result.append(record)
    return result


def encoded(root: Path) -> bytes:
    return json.dumps(
        records(root),
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)
    manifest = subparsers.add_parser("manifest")
    manifest.add_argument("--root", type=Path, required=True)
    manifest.add_argument("--output", type=Path, required=True)
    fingerprint = subparsers.add_parser("fingerprint")
    fingerprint.add_argument("--root", type=Path, required=True)
    arguments = parser.parse_args()
    root = arguments.root.resolve(strict=True)
    payload = encoded(root)
    if arguments.command == "fingerprint":
        print(hashlib.sha256(payload).hexdigest())
        return 0
    output = arguments.output
    temporary = output.with_name(output.name + f".tmp.{os.getpid()}")
    temporary.parent.mkdir(parents=True, exist_ok=True)
    temporary.write_bytes(payload + b"\n")
    temporary.replace(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
