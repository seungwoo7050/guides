#!/usr/bin/env python3
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CHECK = ROOT / "tests/check.py"


def run(path: Path, expected_returncode: int, expected_text: str, mode: str = "secure") -> None:
    result = subprocess.run(
        [sys.executable, str(CHECK), "--implementation", str(path), "--expect", mode],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    output = result.stdout + result.stderr
    if result.returncode != expected_returncode:
        raise AssertionError(f"{path.name}: exit={result.returncode}, expected={expected_returncode}\n{output}")
    if expected_text not in output:
        raise AssertionError(f"{path.name}: expected output {expected_text!r}\n{output}")


def main() -> int:
    run(ROOT / "skeleton/ledgerlab_policy.py", 0, "LAB-VULN-CROSS-JOB", "vulnerable")
    run(ROOT / "skeleton/ledgerlab_policy.py", 1, "[FAIL] LAB-DENY-CROSS-OWNER")
    run(ROOT / "reference/ledgerlab_policy.py", 0, "LAB RESULT PASS")
    run(ROOT / "tests/mutants/deny_all.py", 1, "[FAIL] LAB-NORMAL-OWNER")
    run(ROOT / "tests/mutants/cross_owner_allowed.py", 1, "[FAIL] LAB-DENY-CROSS-OWNER")
    run(ROOT / "tests/mutants/prefix_bypass.py", 1, "[FAIL] LAB-DENY-PREFIX-CONFUSION")
    run(ROOT / "tests/mutants/no_detection.py", 1, "[FAIL] LAB-DETECT-POSITIVE")
    print("LAB QUALITY OK reference=pass skeleton=reject mutants=4")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
