#!/usr/bin/env python3
"""Capstone의 stage별 구현 검사를 실행한다."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parent
DEFAULT_TIMEOUT = 20.0

STAGES: dict[str, list[str] | None] = {
    "data-structures": ["tests.test_algorithms.DataStructureTests"],
    "design-techniques": ["tests.test_algorithms.DesignTechniqueTests"],
    "graphs": ["tests.test_algorithms.GraphTests"],
    "strings": ["tests.test_algorithms.StringTests"],
    "all": None,
}


def safe_implementation(value: str) -> str:
    candidate = (ROOT / value).resolve()
    if candidate == ROOT or ROOT not in candidate.parents:
        raise argparse.ArgumentTypeError("implementation은 capstone 내부 디렉터리여야 합니다.")
    if not (candidate / "algorithms.py").is_file():
        raise argparse.ArgumentTypeError(f"{value}/algorithms.py가 없습니다.")
    return str(candidate.relative_to(ROOT))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--impl",
        default=os.environ.get("EXERCISE_IMPL", "reference"),
        type=safe_implementation,
        help="reference, skeleton, workspace 또는 broken/...",
    )
    parser.add_argument(
        "--stage",
        choices=sorted(STAGES),
        default=os.environ.get("EXERCISE_STAGE", "all"),
    )
    parser.add_argument(
        "--expect",
        choices=("pass", "fail", "not-implemented", "timeout"),
        default=os.environ.get("EXERCISE_EXPECT", "pass"),
    )
    return parser.parse_args()


def run(implementation: str, stage: str) -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy()
    environment["EXERCISE_IMPL_PATH"] = implementation
    selected = STAGES[stage]
    if selected is None:
        command = [
            sys.executable,
            "-m",
            "unittest",
            "discover",
            "-s",
            "tests",
            "-t",
            ".",
            "-v",
        ]
    else:
        command = [sys.executable, "-m", "unittest", "-v", *selected]
    raw_timeout = os.environ.get("EXERCISE_TIMEOUT", str(DEFAULT_TIMEOUT))
    try:
        timeout = float(raw_timeout)
    except ValueError as error:
        raise SystemExit(f"EXERCISE_TIMEOUT은 양수여야 합니다: {raw_timeout}") from error
    if timeout <= 0:
        raise SystemExit(f"EXERCISE_TIMEOUT은 양수여야 합니다: {raw_timeout}")
    try:
        return subprocess.run(
            command,
            cwd=ROOT,
            env=environment,
            text=True,
            capture_output=True,
            check=False,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as error:
        stdout = error.stdout or ""
        stderr = error.stderr or ""
        if isinstance(stdout, bytes):
            stdout = stdout.decode(errors="replace")
        if isinstance(stderr, bytes):
            stderr = stderr.decode(errors="replace")
        return subprocess.CompletedProcess(command, 124, stdout, stderr + "\nTIMEOUT\n")


def main() -> int:
    arguments = parse_args()
    result = run(arguments.impl, arguments.stage)
    output = result.stdout + result.stderr

    if arguments.expect == "timeout":
        if result.returncode != 124 or "TIMEOUT" not in output:
            print(output, file=sys.stderr)
            print("의도한 시간 제한이 발생하지 않았습니다.", file=sys.stderr)
            return 1
        print(f"의도한 시간 제한 확인: impl={arguments.impl}, stage={arguments.stage}")
        return 0

    if result.returncode == 124:
        print(output, file=sys.stderr)
        print("검사가 제한 시간을 초과했습니다.", file=sys.stderr)
        return 124

    if arguments.expect == "pass":
        if result.returncode != 0:
            print(output, file=sys.stderr)
            print(
                f"검사 실패: impl={arguments.impl}, stage={arguments.stage}",
                file=sys.stderr,
            )
            return result.returncode or 1
        print(output, end="")
        return 0

    if result.returncode == 0:
        print(output, file=sys.stderr)
        print(
            f"의도한 실패가 발생하지 않았습니다: impl={arguments.impl}, stage={arguments.stage}",
            file=sys.stderr,
        )
        return 1

    if arguments.expect == "not-implemented" and "NotImplementedError" not in output:
        print(output, file=sys.stderr)
        print("미완성 구현이 NotImplementedError가 아닌 이유로 실패했습니다.", file=sys.stderr)
        return 1

    print(
        f"의도한 실패 확인: impl={arguments.impl}, stage={arguments.stage}, expect={arguments.expect}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
