#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import stat


EXCLUDED_DIRS = {
    ".git",
    ".guide",
    "build",
    "out",
    "__pycache__",
    "workspace",
}
EXCLUDED_SUFFIXES = {".pyc", ".log", ".spv", ".dxil", ".metallib"}


def excluded(relative: Path) -> bool:
    return any(
        part in EXCLUDED_DIRS or part.startswith("build-") or part.startswith(".workspace.")
        for part in relative.parts
    ) or relative.suffix in EXCLUDED_SUFFIXES


def manifest(root: Path) -> list[dict[str, object]]:
    entries: list[dict[str, object]] = []
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root)
        if excluded(relative):
            continue
        metadata = path.lstat()
        if stat.S_ISLNK(metadata.st_mode):
            entries.append({
                "path": relative.as_posix(),
                "kind": "symlink",
                "target": os.readlink(path),
            })
        elif stat.S_ISREG(metadata.st_mode):
            entries.append({
                "path": relative.as_posix(),
                "kind": "file",
                "mode": stat.S_IMODE(metadata.st_mode),
                "size": metadata.st_size,
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            })
    return entries


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--output", type=Path)
    parser.add_argument("--reject-symlinks", action="store_true")
    args = parser.parse_args()
    root = args.root.resolve(strict=True)
    entries = manifest(root)
    if args.reject_symlinks:
        links = [entry["path"] for entry in entries if entry["kind"] == "symlink"]
        if links:
            raise SystemExit(f"source symlinks are not allowed: {', '.join(map(str, links))}")
    text = json.dumps(entries, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(text, encoding="utf-8")
    else:
        print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
