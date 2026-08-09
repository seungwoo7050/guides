#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Iterable

EXCLUDED_PARTS = {
    ".git",
    ".guide",
    ".workspaces",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".venv",
    "build",
    "dist",
}
EXCLUDED_SUFFIXES = {".pyc", ".pyo", ".log", ".tmp"}


def source_files(root: Path) -> Iterable[Path]:
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.is_symlink():
            continue
        relative = path.relative_to(root)
        if any(part in EXCLUDED_PARTS or part.endswith(".egg-info") for part in relative.parts):
            continue
        if path.suffix in EXCLUDED_SUFFIXES:
            continue
        yield path


def fingerprint(root: Path) -> tuple[str, int]:
    digest = hashlib.sha256()
    count = 0
    for path in source_files(root):
        relative = path.relative_to(root).as_posix()
        mode = path.stat().st_mode & 0o777
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(f"{mode:o}".encode("ascii"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
        count += 1
    return digest.hexdigest(), count


def manifest(root: Path) -> list[dict[str, object]]:
    result: list[dict[str, object]] = []
    for path in source_files(root):
        result.append(
            {
                "path": path.relative_to(root).as_posix(),
                "mode": path.stat().st_mode & 0o777,
                "size": path.stat().st_size,
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            }
        )
    return result


def run_git(root: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(root), *args],
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env={**os.environ, "GIT_OPTIONAL_LOCKS": "0"},
    ).stdout.rstrip("\n")


def index_fingerprint(root: Path) -> str:
    raw = Path(run_git(root, "rev-parse", "--git-path", "index"))
    path = raw if raw.is_absolute() else root / raw
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else "missing"


def repository_snapshot(root: Path) -> dict[str, object]:
    value, count = fingerprint(root)
    return {
        "source_fingerprint": value,
        "source_files": count,
        "head_commit": run_git(root, "rev-parse", "HEAD"),
        "index_fingerprint": index_fingerprint(root),
        "git_status": run_git(root, "status", "--porcelain=v1", "--untracked-files=normal").splitlines(),
    }


def copy_repository(root: Path, destination: Path) -> None:
    if destination.exists() or destination.is_symlink():
        raise ValueError(f"destination already exists: {destination}")

    def ignore(_directory: str, names: list[str]) -> set[str]:
        ignored: set[str] = set()
        for name in names:
            if name in EXCLUDED_PARTS or name.endswith(".egg-info"):
                ignored.add(name)
            elif Path(name).suffix in EXCLUDED_SUFFIXES:
                ignored.add(name)
        return ignored

    shutil.copytree(root, destination, symlinks=True, ignore=ignore)


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("fingerprint", "manifest", "snapshot"):
        command = sub.add_parser(name)
        command.add_argument("--root", type=Path, required=True)
        command.add_argument("--output", type=Path)
    copy = sub.add_parser("copy")
    copy.add_argument("--root", type=Path, required=True)
    copy.add_argument("--destination", type=Path, required=True)
    args = parser.parse_args()

    root = args.root.resolve()
    if args.command == "fingerprint":
        value, _ = fingerprint(root)
        print(value)
        return 0
    if args.command == "copy":
        copy_repository(root, args.destination.resolve())
        return 0
    data: object = manifest(root) if args.command == "manifest" else repository_snapshot(root)
    encoded = json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(encoded, encoding="utf-8")
    else:
        sys.stdout.write(encoded)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
