#!/usr/bin/env python3
"""Capstone의 stage별 구현 검사를 실행한다."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import os
from pathlib import Path
import re
import signal
import stat
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parent
DEFAULT_TIMEOUT = 20.0

STAGES: dict[str, list[str] | None] = {
    "data-structures": ["tests.test_algorithms.DataStructureTests"],
    "design-techniques": ["tests.test_algorithms.DesignTechniqueTests"],
    "graphs": ["tests.test_algorithms.GraphTests"],
    "strings": ["tests.test_algorithms.StringTests"],
    "all": None,
}
INFRASTRUCTURE_FAILURES = (
    "ImportError",
    "ModuleNotFoundError",
    "SyntaxError",
    "NotImplementedError",
)


@dataclass(frozen=True)
class ExecutionResult:
    returncode: int
    stdout: str
    stderr: str
    timed_out: bool


class CheckerInterrupted(Exception):
    def __init__(self, signum: int) -> None:
        super().__init__(signum)
        self.signum = signum


def owned_group_exists(process: subprocess.Popen[str]) -> bool:
    process.poll()
    try:
        os.killpg(process.pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def wait_owned_group_gone(process: subprocess.Popen[str], seconds: float) -> bool:
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        if not owned_group_exists(process):
            return True
        time.sleep(0.02)
    return not owned_group_exists(process)


def terminate_owned_group(
    process: subprocess.Popen[str],
    first_signal: signal.Signals = signal.SIGTERM,
) -> None:
    if not owned_group_exists(process):
        return
    try:
        os.killpg(process.pid, first_signal)
    except ProcessLookupError:
        return
    if wait_owned_group_gone(process, 1):
        return
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except ProcessLookupError:
        return
    if not wait_owned_group_gone(process, 2):
        raise RuntimeError("checker가 생성한 process group이 종료 뒤에 남았습니다.")


def safe_implementation(value: str) -> str:
    relative = Path(value)
    if (
        not value
        or relative.is_absolute()
        or any(part in {"", ".", ".."} for part in relative.parts)
    ):
        raise argparse.ArgumentTypeError("implementation은 capstone 내부 디렉터리여야 합니다.")

    candidate = ROOT
    for part in relative.parts:
        candidate = candidate / part
        try:
            metadata = candidate.lstat()
        except FileNotFoundError as error:
            detail = f"{value}/algorithms.py가 없습니다."
            if relative == Path("workspace"):
                detail += (
                    " 저장소 루트에서 scripts/new-workspace.sh "
                    "exercises/07-verified-algorithms-capstone을 실행하세요."
                )
            raise argparse.ArgumentTypeError(detail) from error
        if stat.S_ISLNK(metadata.st_mode):
            raise argparse.ArgumentTypeError(
                f"implementation 경로에 symbolic link를 사용할 수 없습니다: {value}"
            )
        if not stat.S_ISDIR(metadata.st_mode):
            raise argparse.ArgumentTypeError(f"implementation이 directory가 아닙니다: {value}")

    source = candidate / "algorithms.py"
    try:
        source_metadata = source.lstat()
    except FileNotFoundError as error:
        detail = f"{value}/algorithms.py가 없습니다."
        if relative == Path("workspace"):
            detail += (
                " 저장소 루트에서 scripts/new-workspace.sh "
                "exercises/07-verified-algorithms-capstone을 실행하세요."
            )
        raise argparse.ArgumentTypeError(detail) from error
    if stat.S_ISLNK(source_metadata.st_mode):
        raise argparse.ArgumentTypeError(
            f"implementation source에 symbolic link를 사용할 수 없습니다: {value}/algorithms.py"
        )
    if not stat.S_ISREG(source_metadata.st_mode):
        raise argparse.ArgumentTypeError(
            f"implementation source는 regular file이어야 합니다: {value}/algorithms.py"
        )
    resolved = candidate.resolve(strict=True)
    if resolved == ROOT or ROOT not in resolved.parents:
        raise argparse.ArgumentTypeError("implementation은 capstone 내부 디렉터리여야 합니다.")
    return relative.as_posix()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--impl",
        default="workspace",
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


def run(implementation: str, stage: str) -> ExecutionResult:
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
    process = subprocess.Popen(
        command,
        cwd=ROOT,
        env=environment,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        start_new_session=True,
    )
    previous_handlers = {
        signum: signal.getsignal(signum)
        for signum in (signal.SIGHUP, signal.SIGINT, signal.SIGTERM)
    }

    def interrupt(signum: int, _frame: object) -> None:
        raise CheckerInterrupted(signum)

    for signum in previous_handlers:
        signal.signal(signum, interrupt)
    try:
        stdout, stderr = process.communicate(timeout=timeout)
        terminate_owned_group(process)
        return ExecutionResult(process.returncode, stdout, stderr, False)
    except CheckerInterrupted as error:
        terminate_owned_group(process, signal.Signals(error.signum))
        process.communicate()
        raise SystemExit(128 + error.signum) from None
    except subprocess.TimeoutExpired:
        terminate_owned_group(process)
        stdout, stderr = process.communicate()
        return ExecutionResult(process.returncode, stdout, stderr + "\nTIMEOUT\n", True)
    finally:
        for signum, handler in previous_handlers.items():
            signal.signal(signum, handler)


def main() -> int:
    arguments = parse_args()
    result = run(arguments.impl, arguments.stage)
    output = result.stdout + result.stderr

    if arguments.expect == "timeout":
        if not result.timed_out:
            print(output, file=sys.stderr)
            print("의도한 시간 제한이 발생하지 않았습니다.", file=sys.stderr)
            return 1
        print(f"의도한 시간 제한 확인: impl={arguments.impl}, stage={arguments.stage}")
        return 0

    if result.timed_out:
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

    if arguments.expect == "fail":
        has_failure = re.search(r"^FAIL: ", output, flags=re.MULTILINE) is not None
        has_error = (
            re.search(r"^ERROR: ", output, flags=re.MULTILINE) is not None
            or re.search(r"^FAILED \([^\n]*errors=", output, flags=re.MULTILINE)
            is not None
        )
        failure_summary = re.search(
            r"^FAILED \([^\n]*failures=[1-9][0-9]*",
            output,
            flags=re.MULTILINE,
        )
        if not has_failure or has_error or failure_summary is None:
            print(output, file=sys.stderr)
            print(
                "assertion failure가 아닌 unittest ERROR를 논리 계약 위반으로 인정할 수 없습니다.",
                file=sys.stderr,
            )
            return 1
        infrastructure_failure = next(
            (marker for marker in INFRASTRUCTURE_FAILURES if marker in output),
            None,
        )
        if infrastructure_failure is not None:
            print(output, file=sys.stderr)
            print(
                "논리 계약 위반이 아니라 infrastructure 오류로 실패했습니다: "
                f"{infrastructure_failure}",
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
