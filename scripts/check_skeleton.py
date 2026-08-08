#!/usr/bin/env python3
"""모든 학습자 skeleton이 미구현 지점에서 예상대로 실패하는지 확인합니다."""

from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
CASES = [
    (
        "프로토콜 검사기",
        ROOT / "exercises/protocol-inspector",
        "홀수 길이 패딩, end-around carry와 1의 보수를 구현하세요",
        "test_known_even_length_vector",
    ),
    (
        "경로 진단",
        ROOT / "exercises/path-diagnosis",
        "JSON 파일 읽기와 오류 변환을 구현하세요",
        "test_all_published_fixtures_are_valid",
    ),
]

for label, exercise, expected_error, expected_test in CASES:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(exercise / "skeleton")
    result = subprocess.run(
        [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"],
        cwd=exercise,
        env=env,
        text=True,
        capture_output=True,
        check=False,
        timeout=60,
    )
    combined = result.stdout + result.stderr
    if result.returncode == 0:
        print(f"{label} skeleton 검사가 예상과 달리 통과했습니다.", file=sys.stderr)
        raise SystemExit(1)
    if "NotImplementedError" not in combined:
        print(f"{label} skeleton 실패가 미구현 함수에서 발생하지 않았습니다.", file=sys.stderr)
        print(combined, file=sys.stderr)
        raise SystemExit(1)
    if expected_error not in combined or expected_test not in combined:
        print(f"{label} skeleton이 약속한 첫 체크포인트에서 실패하지 않았습니다.", file=sys.stderr)
        print(combined, file=sys.stderr)
        raise SystemExit(1)
    if "ImportError" in combined or "ModuleNotFoundError" in combined:
        print(f"{label} skeleton의 공개 구조가 깨졌습니다.", file=sys.stderr)
        print(combined, file=sys.stderr)
        raise SystemExit(1)
    print(f"{label} skeleton의 예상 실패를 확인했습니다.")
