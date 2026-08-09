#!/usr/bin/env python3
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LABS = [
    ROOT / "exercises/01-source-and-diagnostics/check.py",
    ROOT / "exercises/02-lexer-parser-and-ast/check.py",
    ROOT / "exercises/03-resolution-types-and-flow/check.py",
    ROOT / "exercises/04-interpreter-and-vm/check.py",
]


def main() -> int:
    for lab in LABS:
        result = subprocess.run(
            [sys.executable, str(lab)],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=15,
            check=False,
        )
        if result.returncode != 0 or "PASS" not in result.stdout:
            print(
                f"ERROR lab failed: {lab.relative_to(ROOT)}\n"
                f"stdout={result.stdout}\nstderr={result.stderr}",
                file=sys.stderr,
            )
            return 1
        print(result.stdout.strip())
    print(f"PASS labs count={len(LABS)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
