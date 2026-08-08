#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("usage: manifest_check.py MANIFEST.json", file=sys.stderr)
        return 2

    document = json.loads(Path(argv[1]).read_text(encoding="utf-8"))
    for entry in document["repositories"]:
        repo = Path(entry["path"])
        head = subprocess.run(
            ["git", "-C", str(repo), "rev-parse", "HEAD"],
            check=True,
            text=True,
            stdout=subprocess.PIPE,
        ).stdout.strip()
        if head != entry["commit"]:
            print(f"ERROR: {entry['name']}: commit mismatch", file=sys.stderr)
            return 1

    print("release manifest verified")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
