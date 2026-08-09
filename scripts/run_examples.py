#!/usr/bin/env python3
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = [
    ROOT / "examples/diagnostic-renderer/render.py",
    ROOT / "examples/pratt-parser/pratt.py",
    ROOT / "examples/dataflow-fixed-point/dataflow.py",
    ROOT / "examples/bytecode-vm/vm.py",
]


def main() -> int:
    for example in EXAMPLES:
        proc = subprocess.run(
            [sys.executable, str(example), "--self-test"],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=10,
        )
        if proc.returncode != 0 or "PASS" not in proc.stdout:
            print(
                f"ERROR example failed: {example.relative_to(ROOT)}\n"
                f"stdout={proc.stdout}\nstderr={proc.stderr}",
                file=sys.stderr,
            )
            return 1
        print(proc.stdout.strip())
    print(f"PASS examples count={len(EXAMPLES)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
