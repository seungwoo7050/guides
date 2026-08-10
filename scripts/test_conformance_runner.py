#!/usr/bin/env python3
"""Black-box regression tests for the public Mica conformance runner."""

from __future__ import annotations

import argparse
import shlex
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence


ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "exercises" / "08-mica-capstone" / "check_submission.py"
ADAPTER = ROOT / "scripts" / "testdata" / "conformance" / "adapter.py"


@dataclass(frozen=True)
class MutantCase:
    name: str
    stage: str
    timeout: float = 5.0


MUTANTS = (
    MutantCase("eof-only", "lex"),
    MutantCase("empty-module", "parse"),
    MutantCase("partial-node", "parse"),
    MutantCase("wrong-source-id", "source"),
    MutantCase("split-utf8", "source"),
    MutantCase("wrong-phase", "lex"),
    MutantCase("nan", "source"),
    MutantCase("wrong-run", "run"),
    MutantCase("accept-invalid-bytecode", "vm"),
    MutantCase("vm-mismatch", "vm"),
    MutantCase("non-idempotent-format", "format"),
    MutantCase("unsafe-lint-fix", "format"),
    MutantCase("timeout", "source", timeout=0.25),
    MutantCase("output-flood", "source"),
)


def adapter_command(mutant: str | None = None) -> str:
    argv = [sys.executable, str(ADAPTER)]
    if mutant is not None:
        argv.extend(["--mutant", mutant])
    return shlex.join(argv)


def invoke(stage: str, *, mutant: str | None = None, timeout: float = 5.0) -> subprocess.CompletedProcess[str]:
    argv = [
        sys.executable,
        str(RUNNER),
        "--workspace",
        str(ROOT),
        "--command",
        adapter_command(mutant),
        "--stage",
        stage,
        "--timeout",
        str(timeout),
    ]
    try:
        return subprocess.run(
            argv,
            cwd=ROOT,
            text=True,
            encoding="utf-8",
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=max(20.0, timeout * 10),
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise AssertionError(f"outer test timeout for stage={stage} mutant={mutant}") from exc


def assert_positive() -> None:
    for stage in ("all", "vm", "format"):
        result = invoke(stage)
        if result.returncode != 0:
            raise AssertionError(
                f"positive adapter failed stage {stage}\nstdout={result.stdout[-4000:]!r}\n"
                f"stderr={result.stderr[-4000:]!r}"
            )
        print(f"PASS positive adapter stage={stage}")


def assert_mutant(case: MutantCase) -> None:
    result = invoke(case.stage, mutant=case.name, timeout=case.timeout)
    if result.returncode == 0:
        raise AssertionError(
            f"runner accepted mutant {case.name!r} at stage {case.stage!r}\n"
            f"stdout={result.stdout[-2000:]!r}\nstderr={result.stderr[-2000:]!r}"
        )
    print(f"PASS rejected mutant={case.name} stage={case.stage}")


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--positive-only",
        action="store_true",
        help="run only the fixture-backed positive paths",
    )
    parser.add_argument(
        "--mutant",
        action="append",
        choices=[case.name for case in MUTANTS],
        help="run only the named mutant (repeatable); positive paths still run first",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    assert_positive()
    if args.positive_only:
        return 0
    selected = set(args.mutant or [])
    cases = [case for case in MUTANTS if not selected or case.name in selected]
    for case in cases:
        assert_mutant(case)
    print(f"PASS conformance runner regression suite ({len(cases)} mutants)")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        raise SystemExit(1)
