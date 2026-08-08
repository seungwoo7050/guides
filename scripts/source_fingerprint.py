#!/usr/bin/env python3
"""Compatibility entry point for the guide source fingerprint."""

from __future__ import annotations

import argparse
from pathlib import Path

from guide_state import capture, source_entries


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", nargs="?", type=Path)
    parser.add_argument("--manifest", type=Path)
    arguments = parser.parse_args()
    root = (arguments.root or Path(__file__).resolve().parents[1]).resolve()
    if arguments.manifest:
        arguments.manifest.write_text(
            "\n".join(repr(entry) for entry in source_entries(root)) + "\n",
            encoding="utf-8",
        )
    print(capture(root))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
