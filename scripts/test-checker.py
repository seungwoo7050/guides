#!/usr/bin/env python3
"""Prove that the capstone runner accepts and rejects the intended contracts."""

from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
CAPSTONE = ROOT / "exercises/07-verified-algorithms-capstone"
CHECKER = CAPSTONE / "check.py"


def run(
    *arguments: str,
    extra_environment: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy()
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    if extra_environment:
        environment.update(extra_environment)
    return subprocess.run(
        [sys.executable, str(CHECKER), *arguments],
        cwd=CAPSTONE,
        env=environment,
        text=True,
        capture_output=True,
        timeout=30,
        check=False,
    )


def require(condition: bool, label: str, result: subprocess.CompletedProcess[str]) -> None:
    if not condition:
        raise AssertionError(
            f"{label}\nreturncode={result.returncode}\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        )


def expected_success(label: str, *arguments: str, **kwargs: object) -> None:
    result = run(*arguments, **kwargs)
    require(result.returncode == 0, label, result)


def main() -> int:
    cases = 0
    expected_success("reference 전체 계약", "--impl", "reference", "--stage", "all", "--expect", "pass")
    cases += 1

    for stage in ("data-structures", "design-techniques", "graphs", "strings"):
        expected_success(
            f"skeleton {stage} 미구현 경계",
            "--impl",
            "skeleton",
            "--stage",
            stage,
            "--expect",
            "not-implemented",
        )
        cases += 1

    broken_cases = (
        ("broken/off-by-one", "data-structures"),
        ("broken/wrong-greedy", "design-techniques"),
        ("broken/missed-negative-cycle", "graphs"),
        ("broken/empty-pattern", "strings"),
    )
    for implementation, stage in broken_cases:
        expected_success(
            f"{implementation} 결함 검출",
            "--impl",
            implementation,
            "--stage",
            stage,
            "--expect",
            "fail",
        )
        cases += 1

    expected_success(
        "비종료 구현 시간 제한",
        "--impl",
        "broken/non-terminating",
        "--stage",
        "strings",
        "--expect",
        "timeout",
        extra_environment={"EXERCISE_TIMEOUT": "1"},
    )
    cases += 1

    traversal = run("--impl", "../../", "--stage", "all", "--expect", "pass")
    require(traversal.returncode != 0 and "capstone 내부" in traversal.stderr, "경로 이탈 거부", traversal)
    cases += 1

    invalid_timeout = run(
        "--impl",
        "reference",
        "--stage",
        "all",
        "--expect",
        "pass",
        extra_environment={"EXERCISE_TIMEOUT": "0"},
    )
    require(
        invalid_timeout.returncode != 0 and "양수" in invalid_timeout.stderr,
        "잘못된 시간 제한 거부",
        invalid_timeout,
    )
    cases += 1

    print(f"[PASS] checker contracts: {cases}개 positive/negative/timeout/boundary 사례")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
