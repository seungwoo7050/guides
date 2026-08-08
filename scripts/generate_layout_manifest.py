#!/usr/bin/env python3
"""Regenerate the sorted exact source-file layout manifest."""

from __future__ import annotations

from pathlib import Path
import sys

sys.dont_write_bytecode = True
from repository_state import source_manifest

ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "scripts/layout-manifest.txt"


def main() -> int:
    paths = sorted(
        str(entry["path"])
        for entry in source_manifest(ROOT)
        if entry["type"] != "directory"
    )
    if "scripts/layout-manifest.txt" not in paths:
        paths.append("scripts/layout-manifest.txt")
        paths.sort()
    TARGET.write_text("\n".join(paths) + "\n", encoding="utf-8")
    print(f"layout manifest: {len(paths)} files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
