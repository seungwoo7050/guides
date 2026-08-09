#!/usr/bin/env python3
from __future__ import annotations

import argparse
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(description="Remove one explicitly named in-repository learner workspace")
    parser.add_argument("target")
    args = parser.parse_args()
    raw = Path(args.target)
    target = (Path.cwd() / raw) if not raw.is_absolute() else raw
    workspace_root = ROOT / ".workspaces"
    if target.is_symlink():
        raise SystemExit(f"symlink workspace는 제거하지 않습니다: {target}")
    resolved = target.resolve(strict=False)
    allowed = workspace_root.resolve(strict=False)
    try:
        relative = resolved.relative_to(allowed)
    except ValueError:
        raise SystemExit(f".workspaces 밖 target은 제거하지 않습니다: {resolved}")
    if not relative.parts:
        raise SystemExit(".workspaces 전체 제거는 허용하지 않습니다")
    if not resolved.is_dir():
        raise SystemExit(f"workspace directory가 없습니다: {resolved}")
    shutil.rmtree(resolved)
    print(f"PURGED {resolved}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
