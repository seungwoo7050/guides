#!/usr/bin/env python3
"""Create a learner workspace without overwriting existing work."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
STARTER = ROOT / "exercises" / "10-capstone-local-coding-agent" / "starter"


def tree_fingerprint(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(root.rglob("*"), key=lambda item: item.relative_to(root).as_posix()):
        relative = path.relative_to(root).as_posix()
        if path.is_symlink():
            raise RuntimeError(f"starter contains a symlink: {relative}")
        if not path.is_file():
            continue
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def create_workspace(destination: Path) -> Path:
    destination = destination.absolute()
    if destination.is_symlink() or os.path.lexists(destination):
        raise FileExistsError(f"refusing to overwrite existing destination: {destination}")
    if not STARTER.is_dir():
        raise FileNotFoundError(f"starter is missing: {STARTER}")

    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(tempfile.mkdtemp(prefix=f".{destination.name}.", dir=destination.parent))
    try:
        shutil.copytree(STARTER, temporary / "content", symlinks=False)
        manifest = {
            "guide": "agentic-systems",
            "profile": "local-coding-agent",
            "contract_version": "1.0",
            "starter_sha256": tree_fingerprint(STARTER),
        }
        (temporary / "content" / ".starter-manifest.json").write_text(
            json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        os.replace(temporary / "content", destination)
    finally:
        shutil.rmtree(temporary, ignore_errors=True)
    return destination


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--destination",
        type=Path,
        default=ROOT / ".workspace" / "local-coding-agent",
        help="new directory to create (existing paths and symlinks are refused)",
    )
    args = parser.parse_args(argv)
    try:
        destination = create_workspace(args.destination)
    except (FileExistsError, FileNotFoundError, RuntimeError, OSError) as exc:
        print(f"workspace error: {exc}", file=sys.stderr)
        return 2
    print(f"created learner workspace: {destination}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
