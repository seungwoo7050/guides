#!/usr/bin/env python3
"""Python exercise의 reference 통과와 skeleton 실패를 함께 검증한다."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PYTHON_EXERCISES = [
    "exercises/02-storage-and-indexes/01-slotted-page",
    "exercises/02-storage-and-indexes/02-bplus-tree",
    "exercises/02-storage-and-indexes/03-buffer-pool-clock",
    "exercises/03-transactions-and-recovery/02-wal-recovery",
    "exercises/04-execution-and-optimization/01-join-algorithms",
    "exercises/05-capstones/02-mini-storage-engine",
]


def run_tests(base: Path, implementation: str) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(base / implementation)
    return subprocess.run(
        [sys.executable, "-m", "unittest", "discover", "-s", str(base / "tests"), "-v"],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        timeout=90,
        check=False,
    )


def main() -> int:
    for rel in PYTHON_EXERCISES:
        base = ROOT / rel
        reference = run_tests(base, "reference")
        if reference.returncode != 0:
            print(f"[FAIL] reference: {rel}", file=sys.stderr)
            print(reference.stdout, file=sys.stderr)
            print(reference.stderr, file=sys.stderr)
            return 1
        print(f"[PASS] reference: {rel}")

        skeleton = run_tests(base, "skeleton")
        if skeleton.returncode == 0:
            print(f"[FAIL] skeleton이 모든 테스트를 통과함: {rel}", file=sys.stderr)
            return 1
        output = f"{skeleton.stdout}\n{skeleton.stderr}"
        infrastructure_errors = ("SyntaxError", "ImportError", "ModuleNotFoundError")
        if any(token in output for token in infrastructure_errors):
            print(f"[FAIL] skeleton infrastructure failure: {rel}", file=sys.stderr)
            print(output, file=sys.stderr)
            return 1
        if "FAIL:" not in output and "NotImplementedError" not in output:
            print(f"[FAIL] skeleton failure reason is not a learning contract: {rel}", file=sys.stderr)
            print(output, file=sys.stderr)
            return 1
        print(f"[PASS] skeleton learning failure contract: {rel}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
