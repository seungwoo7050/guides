#!/usr/bin/env python3
"""Render or check the exact canonical source path manifest."""
from __future__ import annotations

import argparse
from pathlib import Path
import sys

sys.dont_write_bytecode = True
from source_fingerprint import ROOT, source_files  # noqa: E402

MANIFEST = ROOT / "config/repository-files.txt"


def content() -> str:
    paths = [
        path.relative_to(ROOT).as_posix() for path in source_files()
        if path.relative_to(ROOT).as_posix() != "config/repository-files.txt"
    ]
    return "# canonical source files; this manifest excludes itself\n" + "\n".join(paths) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    expected = content()
    if args.check:
        if not MANIFEST.is_file() or MANIFEST.read_text(encoding="utf-8") != expected:
            raise SystemExit("repository manifest differs; run python3 scripts/render_manifest.py")
        print("MANIFEST OK")
        return 0
    MANIFEST.write_text(expected, encoding="utf-8")
    print(f"MANIFEST RENDERED paths={expected.count(chr(10)) - 1}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
