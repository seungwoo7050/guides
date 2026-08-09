#!/usr/bin/env python3
"""Run the tracked contract tests against reference, starter, or mutants."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path


HERE = Path(__file__).resolve().parent
CAPSTONE = HERE.parent
ROOT = CAPSTONE.parents[1]
STAGES = tuple(f"{number:02d}" for number in range(1, 11))


def implementation_path(value: str) -> Path:
    if value in {"reference", "starter"}:
        return CAPSTONE / value
    candidate = Path(value)
    if not candidate.is_absolute():
        candidate = ROOT / candidate
    return candidate.resolve()


def run_test(pattern: str, implementation: Path) -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy()
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    environment["CODING_AGENT_IMPLEMENTATION"] = str(implementation)
    paths = [str(implementation), str(CAPSTONE)]
    if environment.get("PYTHONPATH"):
        paths.append(environment["PYTHONPATH"])
    environment["PYTHONPATH"] = os.pathsep.join(paths)
    return subprocess.run(
        [sys.executable, "-B", "-m", "unittest", "discover", "-s", str(HERE), "-p", pattern, "-v"],
        cwd=ROOT,
        env=environment,
        text=True,
        capture_output=True,
        check=False,
    )


def selected_stages(raw: str) -> tuple[str, ...]:
    if raw == "all":
        return STAGES
    if raw == "capstone":
        return ("10",)
    normalized = raw.zfill(2)
    if normalized not in STAGES:
        raise ValueError(f"unknown stage: {raw}")
    # A stage is cumulative by contract.
    return STAGES[: STAGES.index(normalized) + 1]


def emit(completed: subprocess.CompletedProcess[str]) -> None:
    if completed.stdout:
        print(completed.stdout, end="")
    if completed.stderr:
        print(completed.stderr, end="", file=sys.stderr)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--implementation", required=True)
    parser.add_argument("--stage", required=True)
    parser.add_argument("--expect-incomplete", action="store_true")
    args = parser.parse_args(argv)

    if args.implementation == "mutants":
        if args.expect_incomplete:
            parser.error("mutants cannot be combined with --expect-incomplete")
        completed = run_test("test_mutants.py", CAPSTONE / "reference")
        emit(completed)
        if completed.returncode == 0:
            print("MUTANTS OK: every known-bad behavior was rejected")
        return completed.returncode

    implementation = implementation_path(args.implementation)
    if implementation.is_symlink() or not implementation.is_dir():
        print(f"implementation directory is missing or unsafe: {implementation}", file=sys.stderr)
        return 2

    try:
        stages = selected_stages(args.stage)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    failures: list[str] = []
    for stage in stages:
        completed = run_test(f"test_stage_{stage}_*.py", implementation)
        if args.expect_incomplete:
            if completed.returncode == 0:
                emit(completed)
                failures.append(f"stage {stage} unexpectedly passed")
            else:
                combined = (completed.stdout + completed.stderr).lower()
                if not any(marker in combined for marker in ("notimplemented", "todo(stage-", "incomplete", "failure", "error")):
                    emit(completed)
                    failures.append(f"stage {stage} failed without an incomplete-contract signal")
                else:
                    print(f"STARTER stage {stage}: rejected as intentionally incomplete")
        else:
            emit(completed)
            if completed.returncode != 0:
                failures.append(f"stage {stage} failed")
                break

    if failures:
        for failure in failures:
            print(f"ERROR: {failure}", file=sys.stderr)
        return 1
    label = "STARTER CONTRACT OK" if args.expect_incomplete else "REFERENCE OK"
    print(f"{label}: stages={','.join(stages)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
