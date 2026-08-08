#!/usr/bin/env python3
"""Create deterministic source manifests for guide-operating-systems."""

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
    "build-sanitize",
    "htmlcov",
    "workspace",
}
IGNORED_NAMES = {".DS_Store"}
IGNORED_PREFIXES = (".checker-mutant.", ".workspace-copy.")


def file_digest(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def ignored_name(name: str) -> bool:
    return name in IGNORED_NAMES or name in IGNORED_PARTS or name.startswith(IGNORED_PREFIXES)


def record_for(path: Path, root: Path) -> dict[str, object]:
    metadata = path.lstat()
    record: dict[str, object] = {
        "path": path.relative_to(root).as_posix(),
        "mode": stat.S_IMODE(metadata.st_mode),
    }
    if stat.S_ISREG(metadata.st_mode):
        record.update(type="file", size=metadata.st_size, sha256=file_digest(path))
    elif stat.S_ISLNK(metadata.st_mode):
        record.update(type="symlink", target=os.readlink(path))
    else:
        record.update(type="special", device=metadata.st_rdev)
    return record


def records(root: Path) -> list[dict[str, object]]:
    result: list[dict[str, object]] = []
    for directory, names, files in os.walk(root, topdown=True, followlinks=False):
        base = Path(directory)
        traversable: list[str] = []
        for name in sorted(name for name in names if not ignored_name(name)):
            path = base / name
            metadata = path.lstat()
            if stat.S_ISLNK(metadata.st_mode):
                result.append(record_for(path, root))
            else:
                result.append(
                    {
                        "path": path.relative_to(root).as_posix(),
                        "mode": stat.S_IMODE(metadata.st_mode),
                        "type": "directory",
                    }
                )
                traversable.append(name)
        names[:] = traversable
        for name in sorted(files):
            if ignored_name(name) or name.endswith((".pyc", ".pyo")):
                continue
            path = base / name
            result.append(record_for(path, root))
    return sorted(result, key=lambda item: str(item["path"]))


def encoded(root: Path) -> bytes:
    return json.dumps(
        records(root),
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def git_directory(root: Path) -> Path:
    candidate = root / ".git"
    if candidate.is_dir() and not candidate.is_symlink():
        return candidate
    if candidate.is_file() and not candidate.is_symlink():
        prefix = "gitdir: "
        value = candidate.read_text(encoding="utf-8").strip()
        if not value.startswith(prefix):
            raise ValueError(".git file 형식이 올바르지 않습니다")
        directory = Path(value.removeprefix(prefix))
        return directory.resolve() if directory.is_absolute() else (root / directory).resolve()
    raise ValueError("Git metadata 디렉터리를 찾을 수 없습니다")


def index_fingerprint(root: Path) -> str:
    index = git_directory(root) / "index"
    if not index.is_file() or index.is_symlink():
        return "missing"
    metadata = index.stat()
    payload = {
        "mode": stat.S_IMODE(metadata.st_mode),
        "sha256": file_digest(index),
        "size": metadata.st_size,
    }
    return hashlib.sha256(
        json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    ).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)
    manifest = subparsers.add_parser("manifest")
    manifest.add_argument("--root", type=Path, required=True)
    manifest.add_argument("--output", type=Path, required=True)
    fingerprint = subparsers.add_parser("fingerprint")
    fingerprint.add_argument("--root", type=Path, required=True)
    index = subparsers.add_parser("index")
    index.add_argument("--root", type=Path, required=True)
    index_path = subparsers.add_parser("index-path")
    index_path.add_argument("--root", type=Path, required=True)
    arguments = parser.parse_args()
    root = arguments.root.resolve(strict=True)
    if arguments.command == "index-path":
        try:
            print(git_directory(root) / "index")
        except (OSError, UnicodeError, ValueError) as error:
            print(f"Git index path 오류: {error}", file=sys.stderr)
            return 2
        return 0
    if arguments.command == "index":
        try:
            print(index_fingerprint(root))
        except (OSError, UnicodeError, ValueError) as error:
            print(f"Git index fingerprint 오류: {error}", file=sys.stderr)
            return 2
        return 0
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
