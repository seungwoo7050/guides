#!/usr/bin/env python3
"""Create stable source manifests, fingerprints, copies, and index fingerprints."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import stat
import subprocess
from pathlib import Path

IGNORED_NAMES = {".git", ".guide", ".verify", "__pycache__", ".pytest_cache", "workspace"}
IGNORED_FILES = {"capture.txt"}


def ignored(relative: Path) -> bool:
    return any(part in IGNORED_NAMES for part in relative.parts) or relative.name in IGNORED_FILES


def source_manifest(root: Path) -> list[dict[str, object]]:
    result: list[dict[str, object]] = []
    for directory, names, files in os.walk(root, topdown=True, followlinks=False):
        base = Path(directory)
        relative_base = base.relative_to(root)
        traversable: list[str] = []
        for name in sorted(names):
            relative = relative_base / name
            if ignored(relative):
                continue
            path = base / name
            metadata = path.lstat()
            mode = stat.S_IMODE(metadata.st_mode)
            if stat.S_ISLNK(metadata.st_mode):
                result.append(
                    {
                        "path": relative.as_posix(),
                        "type": "symlink",
                        "mode": mode,
                        "target": os.readlink(path),
                    }
                )
            else:
                result.append(
                    {"path": relative.as_posix(), "type": "directory", "mode": mode}
                )
                traversable.append(name)
        names[:] = traversable
        for name in sorted(files):
            path = base / name
            relative = path.relative_to(root)
            if ignored(relative):
                continue
            metadata = path.lstat()
            mode = stat.S_IMODE(metadata.st_mode)
            if stat.S_ISLNK(metadata.st_mode):
                result.append(
                    {"path": relative.as_posix(), "type": "symlink", "mode": mode, "target": os.readlink(path)}
                )
                continue
            if not stat.S_ISREG(metadata.st_mode):
                result.append({"path": relative.as_posix(), "type": "other", "mode": mode})
                continue
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            result.append(
                {
                    "path": relative.as_posix(),
                    "type": "file",
                    "mode": mode,
                    "size": metadata.st_size,
                    "sha256": digest,
                }
            )
    return sorted(result, key=lambda item: str(item["path"]))


def serialized_manifest(root: Path) -> bytes:
    return (json.dumps(source_manifest(root), ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode()


def index_fingerprint(root: Path) -> str:
    process = subprocess.run(
        ["git", "-C", str(root), "rev-parse", "--git-path", "index"],
        env={**os.environ, "GIT_OPTIONAL_LOCKS": "0"},
        check=True,
        capture_output=True,
        text=True,
    )
    path = Path(process.stdout.strip())
    if not path.is_absolute():
        path = root / path
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else "missing"


def copy_source(root: Path, destination: Path) -> None:
    if destination.exists() or destination.is_symlink():
        raise SystemExit(f"copy destination already exists: {destination}")

    def ignore(directory: str, names: list[str]) -> set[str]:
        base = Path(directory)
        relative_base = base.relative_to(root)
        return {name for name in names if ignored(relative_base / name)}

    shutil.copytree(root, destination, symlinks=True, ignore=ignore)


def main() -> int:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)
    for name in ("manifest", "fingerprint", "index-fingerprint"):
        command = subparsers.add_parser(name)
        command.add_argument("--root", required=True, type=Path)
        if name == "manifest":
            command.add_argument("--output", required=True, type=Path)
    copy = subparsers.add_parser("copy")
    copy.add_argument("--root", required=True, type=Path)
    copy.add_argument("--destination", required=True, type=Path)
    args = parser.parse_args()
    root = args.root.resolve()
    if args.command == "manifest":
        args.output.write_bytes(serialized_manifest(root))
    elif args.command == "fingerprint":
        print(hashlib.sha256(serialized_manifest(root)).hexdigest())
    elif args.command == "index-fingerprint":
        print(index_fingerprint(root))
    else:
        copy_source(root, args.destination)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
