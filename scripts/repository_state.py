#!/usr/bin/env python3
"""Stable source manifests and preparation fingerprints for the guide."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import stat
import subprocess
from pathlib import Path


GENERATED_FILES = {".DS_Store"}


def generated_directory(relative: Path) -> bool:
    parts = relative.parts
    if not parts:
        return False
    if parts[0] in {".git", ".guide"}:
        return True
    for index, part in enumerate(parts):
        prefix = parts[:index]
        if part == "target":
            if not prefix:
                return True
            if prefix == ("exercises", "test-support"):
                return True
            if prefix and prefix[0] == "exercises" and prefix[-1] in {"reference", "skeleton"}:
                return True
        if part in {"__pycache__", ".pytest_cache"} and prefix and prefix[0] in {
            "scripts", "exercises"
        }:
            return True
    return False


def ignored(path: Path, root: Path) -> bool:
    relative = path.relative_to(root)
    if generated_directory(relative):
        return True
    if path.name in GENERATED_FILES:
        return True
    if (
        path.suffix in {".pyc", ".pyo"}
        and relative.parts
        and relative.parts[0] in {"scripts", "exercises"}
    ):
        return True
    return False


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def entries(root: Path) -> list[dict[str, object]]:
    result: list[dict[str, object]] = []
    for path in sorted(root.rglob("*"), key=lambda item: item.relative_to(root).as_posix()):
        if ignored(path, root):
            continue
        relative = path.relative_to(root).as_posix()
        metadata = path.lstat()
        mode = stat.S_IMODE(metadata.st_mode)
        if path.is_symlink():
            result.append({"path": relative, "kind": "symlink", "mode": mode, "target": os.readlink(path)})
        elif path.is_file():
            result.append({"path": relative, "kind": "file", "mode": mode, "sha256": sha256_file(path)})
        elif path.is_dir():
            result.append({"path": relative, "kind": "directory", "mode": mode})
    return result


def preparation_fingerprint(root: Path, paths: list[str]) -> str:
    digest = hashlib.sha256()
    for raw in sorted(paths):
        path = (root / raw).resolve()
        try:
            path.relative_to(root)
        except ValueError as error:
            raise SystemExit(f"fingerprint path escapes the repository: {raw}") from error
        if not path.is_file():
            raise SystemExit(f"fingerprint input is missing: {raw}")
        digest.update(raw.encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def git_index_state(root: Path) -> dict[str, str] | None:
    git_environment = {**os.environ, "GIT_OPTIONAL_LOCKS": "0"}
    probe = subprocess.run(
        ["git", "-C", str(root), "rev-parse", "--is-inside-work-tree"],
        check=False,
        capture_output=True,
        env=git_environment,
    )
    if probe.returncode != 0:
        return None
    index_path_output = subprocess.run(
        ["git", "-C", str(root), "rev-parse", "--git-path", "index"],
        check=True,
        capture_output=True,
        text=True,
        env=git_environment,
    ).stdout.strip()
    index_path = Path(index_path_output)
    if not index_path.is_absolute():
        index_path = root / index_path
    if not index_path.is_file():
        raise SystemExit(f"Git index file is missing: {index_path}")
    raw_bytes_sha256 = sha256_file(index_path)
    staged_entries = subprocess.run(
        ["git", "-C", str(root), "ls-files", "--stage", "-z"],
        check=True,
        capture_output=True,
        env=git_environment,
    ).stdout
    return {
        "raw_bytes_sha256": raw_bytes_sha256,
        "staged_entries_sha256": hashlib.sha256(staged_entries).hexdigest(),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)

    manifest = subparsers.add_parser("manifest")
    manifest.add_argument("--root", required=True, type=Path)
    manifest.add_argument("--output", required=True, type=Path)

    fingerprint = subparsers.add_parser("fingerprint")
    fingerprint.add_argument("--root", required=True, type=Path)
    fingerprint.add_argument("paths", nargs="+")

    arguments = parser.parse_args()
    root = arguments.root.resolve()
    if arguments.command == "manifest":
        arguments.output.write_text(
            json.dumps(
                {
                    "entries": entries(root),
                    "git_index": git_index_state(root),
                },
                ensure_ascii=False,
                separators=(",", ":"),
            ) + "\n",
            encoding="utf-8",
        )
        return 0

    print(preparation_fingerprint(root, arguments.paths))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
