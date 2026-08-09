#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import shutil
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "exercises/08-mica-capstone/skeleton"


def within(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False


def main() -> int:
    parser = argparse.ArgumentParser(description="Create a non-overwriting Mica learner workspace")
    parser.add_argument("target", nargs="?", default=str(ROOT / ".workspaces/mica"))
    args = parser.parse_args()
    raw = Path(args.target)
    target = (Path.cwd() / raw).resolve(strict=False) if not raw.is_absolute() else raw.resolve(strict=False)
    workspace_root = (ROOT / ".workspaces").resolve(strict=False)
    root = ROOT.resolve()

    if target == root or target == workspace_root:
        raise SystemExit(f"workspace target is too broad: {target}")
    if within(target, root) and not within(target, workspace_root):
        raise SystemExit(f"repository 내부 target은 .workspaces 아래만 허용합니다: {target}")
    if target.exists() or target.is_symlink():
        raise SystemExit(f"workspace target already exists: {target}")

    target.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=f".{target.name}.tmp-", dir=target.parent))
    candidate = staging / "workspace"
    try:
        shutil.copytree(SOURCE, candidate, symlinks=False)
        os.replace(candidate, target)
    finally:
        shutil.rmtree(staging, ignore_errors=True)
    print(f"CREATED {target}")
    print(
        "NEXT "
        f"PYTHONPATH={target}/src python3 -m mica check "
        f"{ROOT}/exercises/08-mica-capstone/fixtures/valid/literal-main.mica --json"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
