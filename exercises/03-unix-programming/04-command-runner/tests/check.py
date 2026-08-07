#!/usr/bin/env python3
from __future__ import annotations

import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile


def run(program: str, line: str, timeout: float = 8.0) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [program, line],
        text=True,
        capture_output=True,
        timeout=timeout,
        check=False,
    )


def run_with_closed_standard_fds(
    program: str,
    line: str,
    *,
    close_stdin: bool,
    close_stdout: bool,
    timeout: float = 8.0,
) -> subprocess.CompletedProcess[str]:
    def close_selected_fds() -> None:
        if close_stdin:
            os.close(0)
        if close_stdout:
            os.close(1)

    return subprocess.run(
        [program, line],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        text=True,
        timeout=timeout,
        check=False,
        preexec_fn=close_selected_fds,
    )


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def assert_syntax_error(runner: str, line: str) -> None:
    result = run(runner, line)
    require(result.returncode == 2, f"문법 오류 상태 실패 {line!r}: {result.returncode}")
    require(result.stdout == "", f"문법 오류가 stdout에 출력을 생성함: {line!r}")
    require("문법 오류:" in result.stderr, f"문법 진단 누락: {line!r}: {result.stderr!r}")


def main() -> int:
    if len(sys.argv) != 8:
        print("runner and six helper paths required", file=sys.stderr)
        return 2
    runner, print_args, emit, expect, exit_with, terminate_with, mark_file = sys.argv[1:]

    result = run(runner, f"{print_args} one 'two three' \"\" ab\"cd\" escaped\\ space")
    require(result.returncode == 0, f"인자 실행 실패: {result.stderr}")
    require(
        result.stdout
        == "argc=5\narg[0]=<one>\narg[1]=<two three>\narg[2]=<>\n"
        "arg[3]=<abcd>\narg[4]=<escaped space>\n",
        f"인용 결과 불일치: {result.stdout!r}",
    )
    require(result.stderr == "", f"예상하지 않은 stderr: {result.stderr!r}")

    result = run(runner, f"{print_args} '' \"a\\\"b\"")
    require(result.returncode == 0, f"빈 인자·escape 실패: {result.stderr!r}")
    require(result.stdout == "argc=2\narg[0]=<>\narg[1]=<a\"b>\n", result.stdout)

    result = run(runner, f"{print_args} 'a|b' a\\|b '<' \\; \"x&y\" \\>")
    require(result.returncode == 0, f"인용된 제어 문자 실패: {result.stderr!r}")
    require(
        result.stdout
        == "argc=6\narg[0]=<a|b>\narg[1]=<a|b>\narg[2]=<<>\n"
        "arg[3]=<;>\narg[4]=<x&y>\narg[5]=<>>\n",
        f"제어 문자 literal 불일치: {result.stdout!r}",
    )

    result = run(runner, f"\t{print_args}\talpha   beta\t")
    require(result.returncode == 0, f"공백 분리 실패: {result.stderr!r}")
    require(result.stdout == "argc=2\narg[0]=<alpha>\narg[1]=<beta>\n", result.stdout)

    result = run(runner, f"{emit} 4194304 | {expect} 4194304", timeout=20.0)
    require(result.returncode == 0, f"대용량 pipeline 실패: {result.returncode} {result.stderr}")

    for close_stdin, close_stdout in ((True, False), (False, True), (True, True)):
        result = run_with_closed_standard_fds(
            runner,
            f"{emit} 128 | {expect} 128",
            close_stdin=close_stdin,
            close_stdout=close_stdout,
        )
        require(
            result.returncode == 0,
            "표준 FD 재사용 실패: "
            f"stdin={close_stdin} stdout={close_stdout} "
            f"status={result.returncode} stderr={result.stderr!r}",
        )

    result = run(runner, f"{exit_with} 37")
    require(result.returncode == 37, f"종료 상태 전달 실패: {result.returncode}")

    result = run(runner, f"{emit} 0 | {exit_with} 29")
    require(result.returncode == 29, f"마지막 pipeline 상태 실패: {result.returncode}")

    result = run(runner, f"{exit_with} 41 | {expect} 0")
    require(result.returncode == 0, f"왼쪽 실패가 마지막 상태를 덮음: {result.returncode}")

    result = run(runner, f"{terminate_with} {signal.SIGTERM}")
    require(result.returncode == 128 + signal.SIGTERM, f"signal 상태 실패: {result.returncode}")

    result = run(runner, f"{emit} 0 | {terminate_with} {signal.SIGTERM}")
    require(result.returncode == 128 + signal.SIGTERM, f"pipeline signal 상태 실패: {result.returncode}")

    result = run(runner, "./definitely-not-a-command")
    require(result.returncode == 127, f"없는 명령 상태 실패: {result.returncode}")
    require("명령 실행 실패" in result.stderr, f"exec 진단 누락: {result.stderr!r}")

    with tempfile.TemporaryDirectory(prefix="guide-c-runner-") as temp:
        temp_path = Path(temp)
        non_executable = temp_path / "not-executable"
        non_executable.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
        non_executable.chmod(0o600)
        result = run(runner, str(non_executable))
        require(result.returncode == 126, f"실행 불가 상태 실패: {result.returncode}")
        require("명령 실행 실패" in result.stderr, f"실행 불가 진단 누락: {result.stderr!r}")

        marker = temp_path / "marker"
        assert_syntax_error(runner, f"{mark_file} {marker} |")
        require(not marker.exists(), "끝 pipe 문법 오류 뒤 child 부수효과가 생겼습니다")
        assert_syntax_error(runner, f"{mark_file} {marker} > ignored")
        require(not marker.exists(), "지원하지 않는 연산자 뒤 child 부수효과가 생겼습니다")

    bad_lines = [
        "",
        "   \t",
        "| x",
        "x |",
        "x || y",
        "x | y | z",
        "'unterminated",
        '"unterminated',
        "x \\",
        "x < input",
        "x > output",
        "x; y",
        "x & y",
    ]
    for line in bad_lines:
        assert_syntax_error(runner, line)

    result = subprocess.run([runner], text=True, capture_output=True, check=False)
    require(result.returncode == 2, f"사용법 상태 실패: {result.returncode}")
    require(result.stdout == "", f"사용법 오류가 stdout에 출력을 생성함: {result.stdout!r}")
    require("사용법:" in result.stderr, f"사용법 진단 누락: {result.stderr!r}")

    print("command-runner 검사 통과")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
