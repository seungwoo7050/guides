#!/usr/bin/env python3
"""Each public stage must reject the intentionally incomplete skeleton clearly."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TESTS = ROOT / "exercises/command-checker/tests"
FORBIDDEN = ("ImportError", "ModuleNotFoundError", "SyntaxError", "collection failure")


def main() -> int:
    environment = os.environ.copy()
    environment["EXERCISE_IMPL"] = "skeleton"
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    failures = 0
    for stage in range(1, 9):
        pattern = f"test_stage_{stage:02d}_*.py"
        try:
            result = subprocess.run(
                [sys.executable, "-B", "-m", "unittest", "discover", "-s", str(TESTS),
                 "-p", pattern, "-v"],
                cwd=ROOT, env=environment, text=True, capture_output=True,
                timeout=45, check=False,
            )
        except subprocess.TimeoutExpired:
            print(f"FAIL stage {stage:02d}: 검사 자체가 45초를 초과했습니다.", file=sys.stderr)
            failures += 1
            continue
        output = result.stdout + result.stderr
        if result.returncode == 0:
            print(f"FAIL stage {stage:02d}: skeleton이 통과했습니다.", file=sys.stderr)
            failures += 1
        elif any(fragment in output for fragment in FORBIDDEN):
            print(f"FAIL stage {stage:02d}: 교육적 미완성이 아닌 로딩/문법 오류입니다.", file=sys.stderr)
            print(output, file=sys.stderr)
            failures += 1
        elif not any(token in output for token in ("FAIL", "ERROR", "NotImplementedError")):
            print(f"FAIL stage {stage:02d}: 실패 이유가 출력되지 않았습니다.", file=sys.stderr)
            failures += 1
        else:
            print(f"PASS stage {stage:02d}: skeleton failure contract")
    if failures:
        return 1
    print("STAGE CONTRACTS: PASS (8)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
