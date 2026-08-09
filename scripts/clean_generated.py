#!/usr/bin/env python3
"""Remove guide-owned generated state without entering learner workspaces."""

from __future__ import annotations

import os
import shutil
import stat
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
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


def in_workspace(relative: Path) -> bool:
    return (
        len(relative.parts) >= 2
        and relative.parts[0] == "exercises"
        and "workspace" in relative.parts[1:]
    )


def remove_path(path: Path) -> None:
    metadata = path.lstat()
    if stat.S_ISDIR(metadata.st_mode):
        shutil.rmtree(path)
    else:
        path.unlink()


def clean_tree(root: Path) -> list[str]:
    removed: list[str] = []
    guide = root / ".guide"
    if os.path.lexists(guide):
        remove_path(guide)
        removed.append(".guide")

    def visit(directory: Path, prefix: Path) -> None:
        with os.scandir(directory) as iterator:
            children = sorted(iterator, key=lambda child: child.name)
        for child in children:
            relative = prefix / child.name
            if relative.parts[0] == ".git" or in_workspace(relative):
                continue
            path = Path(child.path)
            metadata = child.stat(follow_symlinks=False)
            generated = (
                child.name in GENERATED_DIRECTORIES
                or child.name in GENERATED_FILES
                or path.suffix in GENERATED_SUFFIXES
            )
            if generated:
                remove_path(path)
                removed.append(relative.as_posix())
            elif stat.S_ISDIR(metadata.st_mode):
                visit(path, relative)

    visit(root, Path())
    return removed


def main() -> int:
    removed = clean_tree(ROOT)
    print(f"CLEAN OK removed={len(removed)} learner-workspaces=preserved")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
