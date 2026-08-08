#!/usr/bin/env python3
"""각 누적 단계가 해당 skeleton 미구현 경계를 실제로 노출하는지 검사합니다."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXERCISE = ROOT / "exercises/processor-model"
CASES = [
    ("stage-01 bits", "BitsTests", "TODO: represent_integer"),
    ("stage-02 ISA", "IsaTests", "TODO: _execute"),
    ("stage-03 performance", "PerformanceTests", "TODO: cpu_time"),
    ("stage-04 control", "ControlTests", "TODO: signals"),
    ("stage-05 pipeline", "PipelineTests", "TODO: simulate"),
    ("stage-06 cache", "CacheTests", "TODO: run"),
    ("stage-07 VM", "VirtualMemoryTests", "TODO: run"),
    ("stage-08 predictor", "BranchPredictorTests", "TODO: 2비트"),
    ("stage-08 ROB", "ReorderBufferTests", "TODO: 명령을 빈"),
    ("stage-10 coherence", "CoherenceTests", "TODO: run"),
]


def main() -> int:
    environment = os.environ.copy()
    environment["EXERCISE_IMPL"] = "skeleton"
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    for label, test_class, token in CASES:
        result = subprocess.run(
            [sys.executable, "-m", "unittest", f"tests.test_processor_model.{test_class}", "-v"],
            cwd=EXERCISE, env=environment, check=False, capture_output=True, text=True, timeout=20,
        )
        output = result.stdout + result.stderr
        if result.returncode == 0 or token not in output:
            raise AssertionError(f"{label}이 지정된 미구현 경계를 거부하지 못했습니다.\n{output}")
        print(f"[PASS] designated skeleton failure: {label}")
    reference = environment.copy()
    reference["EXERCISE_IMPL"] = "reference"
    result = subprocess.run(
        [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"],
        cwd=EXERCISE, env=reference, check=False, capture_output=True, text=True, timeout=45,
    )
    if result.returncode != 0:
        raise AssertionError(result.stdout + result.stderr)
    print(f"[PASS] reference test suite rejects all designated skeleton boundaries: {len(CASES)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
