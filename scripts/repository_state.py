#!/usr/bin/env python3
"""Read deterministic repository state without following symlinks or writing files."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import stat
import subprocess
from pathlib import Path

GENERATED_DIRECTORIES = {
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".tox",
    ".venv",
    "__pycache__",
    "htmlcov",
}
GENERATED_FILES = {".coverage", ".DS_Store"}
GENERATED_SUFFIXES = {".pyc", ".pyo"}


def is_workspace(relative: Path) -> bool:
    """Return whether *relative* is in a learner-owned exercise workspace."""

    return (
        len(relative.parts) >= 2
        and relative.parts[0] == "exercises"
        and "workspace" in relative.parts[1:]
    )


def is_generated(relative: Path) -> bool:
    return (
        any(part in GENERATED_DIRECTORIES for part in relative.parts)
        or relative.name in GENERATED_FILES
        or relative.suffix in GENERATED_SUFFIXES
    )


def _entry(path: Path, relative: Path, metadata: os.stat_result) -> dict[str, object]:
    result: dict[str, object] = {
        "path": relative.as_posix(),
        "mode": f"{stat.S_IMODE(metadata.st_mode):04o}",
    }
    if stat.S_ISLNK(metadata.st_mode):
        result["kind"] = "symlink"
        result["target"] = os.readlink(path)
    elif stat.S_ISDIR(metadata.st_mode):
        result["kind"] = "directory"
    elif stat.S_ISREG(metadata.st_mode):
        result["kind"] = "file"
        result["size"] = metadata.st_size
        result["sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
    else:
        result["kind"] = "other"
    return result


def entries(root: Path, scope: str = "source") -> list[dict[str, object]]:
    """Return a sorted manifest for source or learner workspace state."""

    root = root.resolve(strict=True)
    if scope not in {"source", "workspace", "all"}:
        raise ValueError(f"unknown scope: {scope}")
    result: list[dict[str, object]] = []

    def visit(directory: Path, prefix: Path) -> None:
        with os.scandir(directory) as iterator:
            children = sorted(iterator, key=lambda child: child.name)
        for child in children:
            relative = prefix / child.name
            if relative.parts[0] in {".git", ".guide"}:
                continue
            workspace = is_workspace(relative)
            generated = is_generated(relative)
            if scope == "source" and (workspace or generated):
                continue
            if scope == "workspace" and not workspace:
                if child.is_dir(follow_symlinks=False):
                    visit(Path(child.path), relative)
                continue

            metadata = child.stat(follow_symlinks=False)
            path = Path(child.path)
            result.append(_entry(path, relative, metadata))
            if stat.S_ISDIR(metadata.st_mode):
                visit(path, relative)

    visit(root, Path())
    return result


def digest(payload: object) -> str:
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def fingerprint(root: Path, scope: str = "source") -> str:
    return digest(entries(root, scope))


def index_path(root: Path) -> Path:
    environment = os.environ.copy()
    environment["GIT_OPTIONAL_LOCKS"] = "0"
    result = subprocess.run(
        [
            "git",
            "-C",
            str(root),
            "rev-parse",
            "--path-format=absolute",
            "--git-path",
            "index",
        ],
        check=True,
        capture_output=True,
        env=environment,
        text=True,
    )
    return Path(result.stdout.strip())


def index_fingerprint(root: Path) -> str:
    path = index_path(root)
    metadata = path.lstat()
    if not stat.S_ISREG(metadata.st_mode):
        raise RuntimeError(f"Git index is not a regular file: {path}")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "command",
        choices=("source", "workspace", "all", "index", "manifest"),
    )
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    arguments = parser.parse_args()
    root = arguments.root.resolve(strict=True)
    if arguments.command == "index":
        print(index_fingerprint(root))
        return 0
    scope = "source" if arguments.command == "manifest" else arguments.command
    state = entries(root, scope)
    if arguments.command != "manifest":
        print(digest(state))
        return 0
    if arguments.output is None:
        parser.error("manifest requires --output")
    arguments.output.write_text(
        json.dumps(state, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
