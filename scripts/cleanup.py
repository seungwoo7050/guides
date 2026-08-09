#!/usr/bin/env python3
"""Remove only verifier-owned local artifacts from this repository."""
from __future__ import annotations

import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def remove_path(path: Path) -> None:
    if path.is_symlink() or path.is_file():
        path.unlink()
    elif path.is_dir():
        shutil.rmtree(path)


def main() -> int:
    owned_marker = ROOT / ".guide" / "game-development"
    remove_path(owned_marker)
    guide_root = ROOT / ".guide"
    if guide_root.is_dir() and not any(guide_root.iterdir()):
        guide_root.rmdir()

    for path in sorted(ROOT.rglob("__pycache__"), reverse=True):
        if ".git" not in path.parts and ".guide" not in path.parts:
            remove_path(path)
    for suffix in ("*.pyc", "*.pyo"):
        for path in ROOT.rglob(suffix):
            if ".git" not in path.parts and ".guide" not in path.parts:
                remove_path(path)
    print("CLEAN_OK scope=.guide/game-development,python-cache")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
