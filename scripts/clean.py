#!/usr/bin/env python3
from __future__ import annotations

import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REMOVABLE_DIRS = {".guide", "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache"}


def inside_workspace(path: Path) -> bool:
    try:
        relative = path.relative_to(ROOT)
    except ValueError:
        return False
    return "workspace" in relative.parts


def main() -> int:
    removed = 0
    for path in sorted(ROOT.rglob("*"), key=lambda item: len(item.parts), reverse=True):
        if inside_workspace(path):
            continue
        if path.is_dir() and path.name in REMOVABLE_DIRS:
            shutil.rmtree(path)
            removed += 1
        elif path.is_file() and path.suffix in {".pyc", ".pyo"}:
            path.unlink()
            removed += 1
    guide = ROOT / ".guide"
    if guide.exists() and not inside_workspace(guide):
        shutil.rmtree(guide)
        removed += 1
    print(f"CLEAN OK removed={removed} workspace=preserved")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
