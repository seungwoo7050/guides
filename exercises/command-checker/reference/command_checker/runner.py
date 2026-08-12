"""사례 실행 순서, 결과 표시와 최종 상태 정책입니다."""

from __future__ import annotations

import os
import shutil
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Sequence, TextIO

from .model import Case, ExecutionError, Result, SpecificationError
from .process import run_case


# [Implementation 5] 호출 context에서 실행 파일 identity를 한 번 선택해 사례별 재선택을 막습니다.
def validate_executable(command: str) -> str:
    contains_separator = os.sep in command or (os.altsep is not None and os.altsep in command)
    if contains_separator:
        path = Path(command).resolve()
    else:
        selected = shutil.which(command)
        if selected is None:
            raise SpecificationError(f"PATH에서 명령을 찾을 수 없습니다: {command}")
        path = Path(selected).resolve()
    if not path.is_file() or not os.access(path, os.X_OK):
        raise SpecificationError(f"실행할 수 없는 명령입니다: {command}")
    return str(path)


# [Implementation 6] 먼저 순차 실행과 입력 순서라는 baseline orchestration을 완성합니다.
def run_cases(
    cases: Sequence[Case],
    command: Sequence[str],
    jobs: int,
) -> tuple[Result, ...]:
    if jobs < 1:
        raise SpecificationError("jobs는 1 이상이어야 합니다.")
    if jobs == 1:
        return tuple(run_case(case, command) for case in cases)

    # [Implementation 9] bounded worker를 추가하되 executor.map으로 입력 순서를 보존합니다.
    try:
        with ThreadPoolExecutor(max_workers=jobs) as executor:
            return tuple(executor.map(lambda case: run_case(case, command), cases))
    except OSError as error:
        raise ExecutionError(f"실행 worker를 만들 수 없습니다: {error}") from error


# [Implementation 6-1] 불변 Result만 보고 통과와 실패를 사용자 출력 채널에 배치합니다.
def print_results(
    results: Sequence[Result],
    *,
    stdout: TextIO,
    stderr: TextIO,
) -> None:
    for result in results:
        destination = stdout if result.passed else stderr
        print(("통과 " if result.passed else "실패 ") + result.name, file=destination)
        for failure in result.failures:
            print(f"  - {failure}", file=destination)


# [Implementation 6-2] 전체 관찰이 끝난 뒤 한 곳에서 성공·불일치 상태를 축약합니다.
def exit_status(results: Sequence[Result]) -> int:
    return 0 if all(result.passed for result in results) else 1
