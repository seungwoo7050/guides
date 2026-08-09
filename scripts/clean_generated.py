#!/usr/bin/env python3
"""Remove only guide-owned generated state; never traverse learner work."""
from __future__ import annotations

from pathlib import Path
import shutil

from path_safety import UnsafePathError, require_no_symlink_components

ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / ".guide/distributed-systems"


def main() -> int:
    try:
        require_no_symlink_components(TARGET, boundary=ROOT)
    except UnsafePathError as exc:
        raise SystemExit(f"unsafe cleanup path: {exc}") from exc
    if TARGET.exists():
        if not TARGET.is_dir():
            raise SystemExit(f"cleanup target is not a directory: {TARGET}")
        shutil.rmtree(TARGET)
    parent = TARGET.parent
    try:
        require_no_symlink_components(parent, boundary=ROOT)
    except UnsafePathError as exc:
        raise SystemExit(f"unsafe cleanup path: {exc}") from exc
    if parent.is_dir() and not any(parent.iterdir()):
        parent.rmdir()
    print("CLEANED .guide/distributed-systems; .workspace preserved")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
