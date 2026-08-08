#!/usr/bin/env python3
"""Hash repository source state without touching it."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import stat
import subprocess
from pathlib import Path

EXCLUDED_PARTS = {".git", ".guide", ".venv", ".pytest_cache", "__pycache__"}
EXCLUDED_SUFFIXES = {".log", ".pyc", ".pyo"}


def source_entries(root: Path, *, include_workspace: bool = False) -> list[dict[str, object]]:
    """Return a deterministic manifest without following any symlink."""
    entries: list[dict[str, object]] = []

    def visit(directory: Path, prefix: Path) -> None:
        with os.scandir(directory) as iterator:
            children = sorted(iterator, key=lambda item: item.name)
        for child in children:
            relative = prefix / child.name
            in_workspace = "workspace" in relative.parts
            if (any(part in EXCLUDED_PARTS for part in relative.parts)
                    and not (include_workspace and in_workspace)):
                continue
            if not include_workspace and in_workspace:
                continue
            metadata = child.stat(follow_symlinks=False)
            path = Path(child.path)
            if (stat.S_ISREG(metadata.st_mode) and path.suffix in EXCLUDED_SUFFIXES
                    and not (include_workspace and in_workspace)):
                continue
            entry: dict[str, object] = {
                "path": relative.as_posix(),
                "mode": f"{stat.S_IMODE(metadata.st_mode):04o}",
            }
            if stat.S_ISLNK(metadata.st_mode):
                entry["kind"] = "symlink"
                entry["target"] = os.readlink(path)
            elif stat.S_ISDIR(metadata.st_mode):
                entry["kind"] = "directory"
            elif stat.S_ISREG(metadata.st_mode):
                entry["kind"] = "file"
                entry["size"] = metadata.st_size
                entry["sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
            else:
                entry["kind"] = "other"
            entries.append(entry)
            if stat.S_ISDIR(metadata.st_mode):
                visit(path, relative)

    visit(root, Path())
    return entries


def digest(payload: object) -> str:
    encoded = json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def index_fingerprint(root: Path) -> str:
    environment = os.environ.copy()
    environment["GIT_OPTIONAL_LOCKS"] = "0"
    result = subprocess.run(
        ["git", "-C", str(root), "rev-parse", "--path-format=absolute", "--git-path", "index"],
        check=True,
        capture_output=True,
        env=environment,
        text=True,
    )
    index = Path(result.stdout.strip())
    metadata = index.lstat()
    if not stat.S_ISREG(metadata.st_mode):
        raise RuntimeError(f"Git index is not a regular file: {index}")
    return hashlib.sha256(index.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("fingerprint", "index", "manifest"))
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    parser.add_argument(
        "--include-workspace",
        action="store_true",
        help="include learner workspace paths and generated suffixes in fingerprints",
    )
    arguments = parser.parse_args()
    root = arguments.root.resolve()
    if arguments.command == "index":
        print(index_fingerprint(root))
        return 0
    entries = source_entries(root, include_workspace=arguments.include_workspace)
    if arguments.command == "fingerprint":
        print(digest(entries))
        return 0
    if arguments.output is None:
        parser.error("manifest requires --output")
    arguments.output.write_text(
        json.dumps(entries, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
