#!/usr/bin/env python3
"""Stable source byte/mode/symlink manifests for non-destructive checks."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess
from typing import Any

EXCLUDED_DIRS = {".git", ".guide", ".workspace", "__pycache__"}
EXCLUDED_SUFFIXES = {".pyc", ".pyo", ".log"}


def records(root: Path) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for path in sorted(root.rglob("*"), key=lambda item: item.relative_to(root).as_posix()):
        relative = path.relative_to(root)
        if any(part in EXCLUDED_DIRS for part in relative.parts):
            continue
        if path.is_symlink():
            result.append({"path": relative.as_posix(), "type": "symlink", "target": os.readlink(path)})
            continue
        if path.is_dir():
            continue
        if not path.is_file() or path.suffix in EXCLUDED_SUFFIXES:
            continue
        data = path.read_bytes()
        result.append({
            "path": relative.as_posix(),
            "type": "file",
            "mode": f"{os.stat(path).st_mode & 0o777:o}",
            "size": len(data),
            "sha256": hashlib.sha256(data).hexdigest(),
        })
    return result


def fingerprint(items: list[dict[str, Any]]) -> str:
    encoded = json.dumps(items, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def exact_tree_records(path: Path, label: str) -> list[dict[str, Any]]:
    """Describe one path exactly, including directories, links, and ignored files."""
    if not path.exists() and not path.is_symlink():
        return [{"path": label, "type": "absent"}]
    result: list[dict[str, Any]] = []

    def visit(current: Path, relative: str) -> None:
        metadata = current.lstat()
        mode = f"{stat.S_IMODE(metadata.st_mode):o}"
        if stat.S_ISLNK(metadata.st_mode):
            result.append({
                "path": relative, "type": "symlink", "mode": mode,
                "target": os.readlink(current),
            })
            return
        if stat.S_ISDIR(metadata.st_mode):
            result.append({"path": relative, "type": "directory", "mode": mode})
            for child in sorted(current.iterdir(), key=lambda item: item.name):
                visit(child, f"{relative}/{child.name}")
            return
        if stat.S_ISREG(metadata.st_mode):
            data = current.read_bytes()
            result.append({
                "path": relative, "type": "file", "mode": mode,
                "size": len(data), "sha256": hashlib.sha256(data).hexdigest(),
            })
            return
        result.append({"path": relative, "type": "special", "mode": mode})

    visit(path, label)
    return result


def git_index_state(root: Path) -> dict[str, Any]:
    """Hash logical index entries, stages, modes, symlink blobs, and flags."""
    commands = (
        ["git", "-C", str(root), "ls-files", "--stage", "-z"],
        ["git", "-C", str(root), "ls-files", "-v", "-z"],
    )
    payloads: list[bytes] = []
    for command in commands:
        completed = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
        if completed.returncode != 0:
            raise SystemExit("cannot inspect Git index")
        payloads.append(completed.stdout)
    return {
        "stage_sha256": hashlib.sha256(payloads[0]).hexdigest(),
        "stage_bytes": len(payloads[0]),
        "flags_sha256": hashlib.sha256(payloads[1]).hexdigest(),
        "flags_bytes": len(payloads[1]),
    }


def write_payload(payload: str, output: str | None) -> None:
    if output:
        Path(output).write_text(payload, encoding="utf-8")
    else:
        print(payload, end="")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "command", choices=("manifest", "fingerprint", "workspace", "git-index")
    )
    parser.add_argument("--root", required=True)
    parser.add_argument("--output")
    args = parser.parse_args()
    root = Path(args.root).resolve(strict=True)
    if args.command == "workspace":
        payload = json.dumps(
            exact_tree_records(root / ".workspace", ".workspace"),
            ensure_ascii=False, indent=2, sort_keys=True,
        ) + "\n"
        write_payload(payload, args.output)
        return 0
    if args.command == "git-index":
        payload = json.dumps(
            git_index_state(root), ensure_ascii=False, indent=2, sort_keys=True,
        ) + "\n"
        write_payload(payload, args.output)
        return 0
    items = records(root)
    if args.command == "fingerprint":
        print(fingerprint(items))
        return 0
    payload = json.dumps(items, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    write_payload(payload, args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
