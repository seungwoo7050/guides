#!/usr/bin/env python3
from __future__ import annotations

import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    shutil.rmtree(ROOT / ".guide", ignore_errors=True)
    removed = 0
    for directory in sorted(ROOT.rglob("__pycache__"), reverse=True):
        if ".git" not in directory.parts and ".workspaces" not in directory.parts:
            shutil.rmtree(directory, ignore_errors=True)
            removed += 1
    for path in ROOT.rglob("*"):
        if path.is_file() and path.suffix in {".pyc", ".pyo"} and ".workspaces" not in path.parts:
            path.unlink()
            removed += 1
    print(f"CLEANED generated={removed}; preserved={ROOT / '.workspaces'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
