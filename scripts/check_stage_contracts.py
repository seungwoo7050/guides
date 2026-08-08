#!/usr/bin/env python3
"""Verify exact skeleton boundaries and cumulative stage regression."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXERCISE = ROOT / "exercises" / "command-checker"
SKELETON = EXERCISE / "skeleton"
REFERENCE = EXERCISE / "reference"


@dataclass(frozen=True, slots=True)
class Boundary:
    stage: int
    code: str
    message: str


BOUNDARIES = (
    Boundary(1, "from command_checker.cli import build_parser; build_parser()",
             "stage 01: ArgumentParser를 구성하십시오."),
    Boundary(2, "from command_checker.model import Case; Case(name='probe')",
             "stage 02: 불변 Case 모델을 완성하십시오."),
    Boundary(3, "from command_checker.comparison import compare_observation; "
             "compare_observation(None, returncode=0, stdout='', stderr='')",
             "stage 03: 결과 비교를 구현하십시오."),
    Boundary(4, "from pathlib import Path; from command_checker.specification import load_cases; "
             "load_cases(Path('missing.json'))",
             "stage 04: JSON 명세 검증을 구현하십시오."),
    Boundary(5, "from command_checker.process import run_case; run_case(None, ())",
             "stage 05: 외부 프로세스 실행을 구현하십시오."),
    Boundary(6, "from command_checker.runner import validate_executable; validate_executable('python3')",
             "stage 06: 실행 파일 검증을 구현하십시오."),
    Boundary(7, "from command_checker.process import _collect_process; "
             "_collect_process(None, b'', timeout=1.0, output_limit=1)",
             "stage 07: 제한된 프로세스 수집을 구현하십시오."),
    Boundary(8, "from command_checker.reports import render_json; render_json(())",
             "stage 08: JSON 보고서를 구현하십시오."),
)


def environment() -> dict[str, str]:
    result = os.environ.copy()
    for name in ("PYTHONHOME", "PYTHONPATH", "EXERCISE_IMPL", "EXERCISE_IMPL_ROOT"):
        result.pop(name, None)
    result["PYTHONDONTWRITEBYTECODE"] = "1"
    return result


def check_boundary(boundary: Boundary) -> bool:
    try:
        result = subprocess.run(
            [sys.executable, "-B", "-c", boundary.code],
            cwd=SKELETON,
            env=environment(),
            text=True,
            capture_output=True,
            timeout=10,
            check=False,
        )
    except (OSError, subprocess.SubprocessError) as error:
        print(f"FAIL stage {boundary.stage:02d}: probe 실행 오류: {error}", file=sys.stderr)
        return False
    expected = f"NotImplementedError: {boundary.message}"
    lines = (result.stdout + result.stderr).rstrip().splitlines()
    if result.returncode != 1 or not lines or lines[-1] != expected or lines.count(expected) != 1:
        print(
            f"FAIL stage {boundary.stage:02d}: 정확한 NotImplementedError 경계가 아닙니다.",
            file=sys.stderr,
        )
        print(result.stdout + result.stderr, file=sys.stderr)
        return False
    print(f"PASS stage {boundary.stage:02d}: {boundary.message}")
    return True


def check_cumulative_regression() -> bool:
    with tempfile.TemporaryDirectory(prefix="guide-stage-regression-") as directory:
        implementation = Path(directory) / "implementation"
        shutil.copytree(REFERENCE, implementation)
        cli = implementation / "command_checker" / "cli.py"
        text = cli.read_text(encoding="utf-8")
        before = 'parser.add_argument("--cases", required=True, type=Path, help="JSON 사례 파일")'
        after = 'parser.add_argument("--casez", required=True, type=Path, help="JSON 사례 파일")'
        if text.count(before) != 1:
            print("FAIL cumulative regression: mutation anchor mismatch", file=sys.stderr)
            return False
        cli.write_text(text.replace(before, after, 1), encoding="utf-8")
        mutated_environment = environment()
        mutated_environment["EXERCISE_IMPL_ROOT"] = str(implementation)
        try:
            result = subprocess.run(
                [
                    "make", "--no-print-directory", "stage-08",
                    "EXERCISE_IMPL=reference", f"PYTHON={sys.executable}",
                ],
                cwd=ROOT,
                env=mutated_environment,
                text=True,
                capture_output=True,
                timeout=45,
                check=False,
            )
        except (OSError, subprocess.SubprocessError) as error:
            print(f"FAIL cumulative regression: make 실행 오류: {error}", file=sys.stderr)
            return False
    output = result.stdout + result.stderr
    if result.returncode == 0 or "test_help_uses_stdout_and_zero" not in output:
        print("FAIL cumulative regression: stage-08이 손상된 stage-01을 거부하지 않았습니다.", file=sys.stderr)
        print(output, file=sys.stderr)
        return False
    print("PASS cumulative regression: stage-08 rejected a stage-01 mutation")
    return True


def main() -> int:
    boundaries_ok = all([check_boundary(boundary) for boundary in BOUNDARIES])
    cumulative_ok = check_cumulative_regression()
    if not boundaries_ok or not cumulative_ok:
        return 1
    print("STAGE CONTRACTS: PASS (8 exact boundaries, cumulative regression)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
