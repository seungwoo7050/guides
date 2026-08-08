"""6단계와 8단계에서 사례 집계와 병렬 실행을 구현합니다."""

from __future__ import annotations

from typing import Sequence, TextIO

from .model import Case, Result


def validate_executable(command: str) -> None:
    raise NotImplementedError("stage 06: 실행 파일 검증을 구현하십시오.")


def run_cases(cases: Sequence[Case], command: Sequence[str], jobs: int) -> tuple[Result, ...]:
    raise NotImplementedError("stage 06: 전체 사례 실행을 구현하십시오.")


def print_results(results: Sequence[Result], *, stdout: TextIO, stderr: TextIO) -> None:
    raise NotImplementedError("stage 06: 결과 표시를 구현하십시오.")


def exit_status(results: Sequence[Result]) -> int:
    raise NotImplementedError("stage 06: 최종 종료 상태를 구현하십시오.")
