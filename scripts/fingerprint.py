#!/usr/bin/env python3
"""Compatibility entry point for the source fingerprint command."""

from __future__ import annotations

import argparse
from pathlib import Path

from repository_state import fingerprint


def source_fingerprint(root: Path) -> str:
    return fingerprint(root, "source")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", nargs="?", default=".")
    arguments = parser.parse_args()
    print(source_fingerprint(Path(arguments.root)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
