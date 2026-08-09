#!/usr/bin/env python3
from __future__ import annotations

import shutil
import stat
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STATE_ROOT = ROOT / ".guide"
TARGET = STATE_ROOT / "mobile-app"


def fail(message: str) -> None:
    raise SystemExit(f"CLEAN ERROR: {message}")


def main() -> None:
    if STATE_ROOT.is_symlink():
        fail(f"state root symlink는 삭제하지 않습니다: {STATE_ROOT}")
    if STATE_ROOT.exists() and not STATE_ROOT.is_dir():
        fail(f"state root가 directory가 아닙니다: {STATE_ROOT}")
    if TARGET.is_symlink():
        fail(f"target symlink는 삭제하지 않습니다: {TARGET}")
    if not TARGET.exists():
        print(f"CLEAN OK absent={TARGET}")
        return
    metadata = TARGET.lstat()
    if not stat.S_ISDIR(metadata.st_mode):
        fail(f"target가 directory가 아닙니다: {TARGET}")
    shutil.rmtree(TARGET)
    print(f"CLEAN OK removed={TARGET}")


if __name__ == "__main__":
    main()
