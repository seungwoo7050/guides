#!/usr/bin/env python3
"""Copy canonical source into an empty isolated verification directory."""
from __future__ import annotations

import argparse
from pathlib import Path
import shutil

EXCLUDES = shutil.ignore_patterns(
    ".git", ".guide", ".workspace", "__pycache__", "*.pyc", "*.pyo", "*.log"
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("source")
    parser.add_argument("destination")
    args = parser.parse_args()
    source = Path(args.source).resolve(strict=True)
    destination = Path(args.destination).resolve()
    if destination.exists() or destination.is_symlink():
        raise SystemExit("destination must not exist")
    shutil.copytree(source, destination, symlinks=True, ignore=EXCLUDES)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
