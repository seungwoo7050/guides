#!/usr/bin/env python3
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    files = sorted((ROOT / "examples").glob("*.py"))
    if not files:
        print("[FAIL] 실행할 예제가 없습니다.", file=sys.stderr)
        return 1
    for file in files:
        result = subprocess.run(
            [sys.executable, str(file)],
            cwd=ROOT,
            text=True,
            capture_output=True,
            timeout=30,
            check=False,
        )
        if result.returncode != 0:
            print(f"[FAIL] {file.relative_to(ROOT)}", file=sys.stderr)
            print(result.stdout, file=sys.stderr)
            print(result.stderr, file=sys.stderr)
            return 1
        print(f"[PASS] {file.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
