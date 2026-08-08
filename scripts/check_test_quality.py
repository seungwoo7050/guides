#!/usr/bin/env python3
"""알려진 오답 구현이 공개 검사를 통과하지 못하는지 확인합니다."""

from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
EXERCISE = ROOT / "exercises/path-diagnosis"
env = os.environ.copy()
env["PYTHONPATH"] = str(EXERCISE / "broken")
result = subprocess.run(
    [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"],
    cwd=EXERCISE,
    env=env,
    text=True,
    capture_output=True,
    check=False,
    timeout=60,
)
combined = result.stdout + result.stderr
if result.returncode == 0:
    print("알려진 오답 구현이 모든 검사를 통과했습니다.", file=sys.stderr)
    raise SystemExit(1)
if "AssertionError" not in combined and "FAIL:" not in combined:
    print("오답 구현이 계약 위반이 아닌 환경 오류로 실패했습니다.", file=sys.stderr)
    print(combined, file=sys.stderr)
    raise SystemExit(1)
if "ImportError" in combined or "ModuleNotFoundError" in combined or "SyntaxError" in combined:
    print("오답 구현의 패키지 구조 또는 구문이 깨졌습니다.", file=sys.stderr)
    print(combined, file=sys.stderr)
    raise SystemExit(1)
print("알려진 오답 구현을 공개 검사가 거부하는지 확인했습니다.")
