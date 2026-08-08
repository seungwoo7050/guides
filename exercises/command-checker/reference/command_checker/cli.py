"""명령줄 인자, 사용자 진단과 최종 조립입니다."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Sequence

from .model import ExecutionError, SpecificationError
from .reports import write_json_report, write_junit_report
from .runner import exit_status, print_results, run_cases, validate_executable
from .specification import load_cases


class KoreanArgumentParser(argparse.ArgumentParser):
    def format_usage(self) -> str:
        return super().format_usage().replace("usage:", "사용법:", 1)

    def format_help(self) -> str:
        return (
            super()
            .format_help()
            .replace("usage:", "사용법:", 1)
            .replace("options:", "옵션:", 1)
            .replace("positional arguments:", "위치 인자:", 1)
        )

    def error(self, message: str) -> None:
        self.print_usage(sys.stderr)
        self.exit(2, f"{self.prog}: 오류: {message}\n")


def build_parser() -> argparse.ArgumentParser:
    parser = KoreanArgumentParser(
        prog="command-checker",
        description="JSON 명세에 따라 명령줄 프로그램을 검사합니다.",
    )
    parser.add_argument("--cases", required=True, type=Path, help="JSON 사례 파일")
    parser.add_argument("--jobs", type=int, default=1, help="동시에 실행할 사례 수")
    parser.add_argument("--json-report", type=Path, help="JSON 보고서 경로")
    parser.add_argument("--junit-report", type=Path, help="JUnit XML 보고서 경로")
    parser.add_argument(
        "command",
        nargs=argparse.REMAINDER,
        help="-- 뒤에 작성하는 검사 대상 명령",
    )
    return parser


def parse_arguments(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = build_parser()
    arguments = parser.parse_args(argv)
    if arguments.command and arguments.command[0] == "--":
        arguments.command = arguments.command[1:]
    if not arguments.command:
        parser.error("-- 뒤에 실행할 명령을 작성해 주세요.")
    if arguments.jobs < 1:
        parser.error("--jobs는 1 이상이어야 합니다.")
    return arguments


def main(argv: Sequence[str] | None = None) -> int:
    arguments = parse_arguments(argv)

    try:
        cases = load_cases(arguments.cases)
        validate_executable(arguments.command[0])
        results = run_cases(cases, arguments.command, arguments.jobs)
    except (SpecificationError, ExecutionError) as error:
        print(error, file=sys.stderr)
        return 2

    print_results(results, stdout=sys.stdout, stderr=sys.stderr)

    try:
        if arguments.json_report is not None:
            write_json_report(arguments.json_report, results)
        if arguments.junit_report is not None:
            write_junit_report(arguments.junit_report, results)
    except OSError as error:
        print(f"보고서를 저장할 수 없습니다: {error}", file=sys.stderr)
        return 2

    passed = sum(result.passed for result in results)
    failed = len(results) - passed
    print(f"요약: 통과 {passed}건, 실패 {failed}건")
    return exit_status(results)
