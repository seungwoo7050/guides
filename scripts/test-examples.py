#!/usr/bin/env python3
"""Run C observation examples with bounded time and observable-result checks."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = ROOT / "examples"


def run(build: Path, program: str, *arguments: str) -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy()
    environment.setdefault("ASAN_OPTIONS", "detect_leaks=0:halt_on_error=1")
    environment.setdefault("UBSAN_OPTIONS", "halt_on_error=1:print_stacktrace=1")
    return subprocess.run(
        [str(build / program), *arguments],
        cwd=EXAMPLES,
        env=environment,
        text=True,
        capture_output=True,
        timeout=10,
        check=False,
    )


def require(condition: bool, label: str, result: subprocess.CompletedProcess[str]) -> None:
    if not condition:
        raise AssertionError(
            f"{label}\nreturncode={result.returncode}\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        )


def fields(output: str) -> dict[str, str]:
    return dict(re.findall(r"\b([a-z_]+)=([^\s]+)", output))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--build-dir", default="build")
    arguments = parser.parse_args()
    build = (EXAMPLES / arguments.build_dir).resolve()
    try:
        build.relative_to(EXAMPLES)
    except ValueError as error:
        raise SystemExit("build directory는 examples 안에 있어야 합니다") from error

    syscall = run(build, "syscall-boundary")
    require(syscall.returncode == 0 and "errno=2" in syscall.stdout, "system call 경계", syscall)

    split = run(build, "lost-update", "split", "100")
    split_fields = fields(split.stdout)
    require(
        split.returncode == 0
        and split_fields.get("expected") == "200"
        and split_fields.get("actual") == "100",
        "결정론적 lost update",
        split,
    )
    atomic = run(build, "lost-update", "fetch-add", "100")
    atomic_fields = fields(atomic.stdout)
    require(
        atomic.returncode == 0
        and atomic_fields.get("expected") == "200"
        and atomic_fields.get("actual") == "200",
        "atomic fetch-add",
        atomic,
    )

    bounded = run(build, "bounded-buffer", "100")
    bounded_fields = fields(bounded.stdout)
    require(
        bounded.returncode == 0
        and bounded_fields.get("produced") == "100"
        and bounded_fields.get("consumed") == "100"
        and bounded_fields.get("sums_match") == "yes",
        "bounded buffer 결과",
        bounded,
    )

    dining = run(build, "dining-cycle", "100")
    require(
        dining.returncode == 0 and fields(dining.stdout).get("all_completed") == "yes",
        "전역 lock order 완료",
        dining,
    )

    cow = run(build, "cow-observer")
    require(
        cow.returncode == 0
        and re.search(r"child .*value=99", cow.stdout) is not None
        and re.search(r"parent .*value=41 unchanged=yes", cow.stdout) is not None,
        "fork 뒤 COW 관찰",
        cow,
    )

    faults = run(build, "page-fault-observer", "128")
    fault_fields = fields(faults.stdout)
    require(
        faults.returncode == 0
        and fault_fields.get("touched_pages") == "128"
        and int(fault_fields.get("minor_fault_delta", "-1")) >= 0,
        "page fault 관찰",
        faults,
    )

    invalid_cases = (
        ("lost-update", ("unknown", "1")),
        ("bounded-buffer", ("0",)),
        ("dining-cycle", ("0",)),
        ("page-fault-observer", ("0",)),
    )
    for program, values in invalid_cases:
        result = run(build, program, *values)
        require(result.returncode == 2 and "사용법" in result.stderr, f"{program} 입력 경계", result)

    print("[PASS] C examples: observable results 6개 + invalid inputs 4개")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
