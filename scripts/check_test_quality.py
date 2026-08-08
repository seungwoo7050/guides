#!/usr/bin/env python3
"""Known-bad mutations must be rejected by the public exercise tests."""

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
REFERENCE = EXERCISE / "reference"
TESTS = EXERCISE / "tests"


@dataclass(frozen=True, slots=True)
class Mutation:
    name: str
    path: str
    before: str
    after: str
    pattern: str
    expected_test: str


MUTATIONS = (
    Mutation(
        name="stderr comparison removed",
        path="command_checker/comparison.py",
        before="if stderr != case.stderr:",
        after="if False and stderr != case.stderr:",
        pattern="test_stage_03_*.py",
        expected_test="test_three_channels_are_compared_independently",
    ),
    Mutation(
        name="boolean timeout accepted",
        path="command_checker/specification.py",
        before="if isinstance(timeout, bool) or not isinstance(timeout, (int, float)):",
        after="if not isinstance(timeout, (int, float)):",
        pattern="test_stage_04_*.py",
        expected_test="test_bool_is_not_a_numeric_timeout_or_limit",
    ),
    Mutation(
        name="output limit disabled",
        path="command_checker/process.py",
        before="if len(chunk) > remaining_capacity:",
        after="if False and len(chunk) > remaining_capacity:",
        pattern="test_stage_07_*.py",
        expected_test="test_stdout_and_stderr_limits_stop_collection",
    ),
    Mutation(
        name="parallel result order reversed",
        path="command_checker/runner.py",
        before="return tuple(executor.map(lambda case: run_case(case, command), cases))",
        after=(
            "return tuple(reversed(tuple(executor.map("
            "lambda case: run_case(case, command), cases))))"
        ),
        pattern="test_stage_08_*.py",
        expected_test="test_parallel_completion_keeps_input_order",
    ),
    Mutation(
        name="invalid XML controls preserved",
        path="command_checker/reports.py",
        before='else "\\uFFFD"',
        after="else character",
        pattern="test_stage_08_*.py",
        expected_test="test_junit_replaces_invalid_xml_control_characters",
    ),
)


def apply_mutation(root: Path, mutation: Mutation) -> None:
    target = root / mutation.path
    text = target.read_text(encoding="utf-8")
    count = text.count(mutation.before)
    if count != 1:
        raise RuntimeError(
            f"mutation anchor mismatch for {mutation.name}: "
            f"expected 1 occurrence, found {count} in {mutation.path}"
        )
    target.write_text(text.replace(mutation.before, mutation.after, 1), encoding="utf-8")


def rejected(mutation: Mutation) -> bool:
    with tempfile.TemporaryDirectory(prefix="guide-python-mutation-") as directory:
        implementation = Path(directory) / "implementation"
        shutil.copytree(REFERENCE, implementation)
        apply_mutation(implementation, mutation)

        environment = os.environ.copy()
        environment["EXERCISE_IMPL_ROOT"] = str(implementation)
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "unittest",
                "discover",
                "-s",
                str(TESTS),
                "-p",
                mutation.pattern,
                "-v",
            ],
            cwd=ROOT,
            env=environment,
            text=True,
            capture_output=True,
            check=False,
            timeout=30,
        )

    combined = result.stdout + result.stderr
    if result.returncode == 0:
        print(f"FAIL  mutation survived: {mutation.name}", file=sys.stderr)
        return False
    if mutation.expected_test not in combined:
        print(
            f"FAIL  mutation failed for an unexpected reason: {mutation.name}",
            file=sys.stderr,
        )
        print(combined, file=sys.stderr)
        return False
    print(f"PASS  mutation rejected: {mutation.name}")
    return True


def main() -> int:
    failures = 0
    for mutation in MUTATIONS:
        try:
            if not rejected(mutation):
                failures += 1
        except (OSError, RuntimeError, subprocess.SubprocessError) as error:
            print(f"FAIL  mutation setup: {mutation.name}: {error}", file=sys.stderr)
            failures += 1

    if failures:
        print(f"테스트 품질 검사 실패: {failures}건", file=sys.stderr)
        return 1
    print(f"테스트 품질 검사 통과: {len(MUTATIONS)}개 결함을 모두 검출했습니다.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
