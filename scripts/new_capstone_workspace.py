#!/usr/bin/env python3
"""Atomically publish a fresh learner copy without overwriting existing work."""
from __future__ import annotations

import argparse
import os
from pathlib import Path
import shutil
import tempfile

from path_safety import UnsafePathError, lexical_write_path, require_no_symlink_components

ROOT = Path(__file__).resolve().parents[1]
STARTER = ROOT / "capstone/starter"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("target", nargs="?", default=str(ROOT / ".workspace/replicated-kv"))
    args = parser.parse_args()
    raw = Path(args.target)
    try:
        target, boundary = lexical_write_path(raw, base=ROOT)
        require_no_symlink_components(target, boundary=boundary)
    except UnsafePathError as exc:
        raise SystemExit(f"unsafe workspace path: {exc}") from exc
    if target.exists() or target.is_symlink():
        raise SystemExit(f"대상이 이미 존재합니다: {target}")
    parent = target.parent
    parent.mkdir(parents=True, exist_ok=True)
    try:
        require_no_symlink_components(parent, boundary=boundary)
        require_no_symlink_components(target, boundary=boundary)
    except UnsafePathError as exc:
        raise SystemExit(f"unsafe workspace path: {exc}") from exc
    temporary = Path(tempfile.mkdtemp(prefix=f".{target.name}.tmp.", dir=parent))
    published = False
    try:
        shutil.copytree(STARTER, temporary, dirs_exist_ok=True, symlinks=False)
        try:
            require_no_symlink_components(target, boundary=boundary)
        except UnsafePathError as exc:
            raise SystemExit(f"unsafe workspace path: {exc}") from exc
        if target.exists() or target.is_symlink():
            raise SystemExit(f"대상이 준비 중 생성되었습니다: {target}")
        os.rename(temporary, target)
        published = True
    finally:
        if not published and temporary.exists():
            shutil.rmtree(temporary)
    print(f"CREATED {target}")
    print(f"RUN python3 scripts/check-capstone-workspace.py {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
