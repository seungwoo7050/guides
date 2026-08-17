"""Coordinate case execution, presentation, and final status policy."""

from __future__ import annotations

import os
import shutil
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Sequence, TextIO

from .model import Case, ExecutionError, Result, SpecificationError
from .process import run_case


# [Implementation 5] Executable identity selection.
def validate_executable(command: str) -> str:
    contains_separator = os.sep in command or (os.altsep is not None and os.altsep in command)
    if contains_separator:
        path = Path(command).resolve()
    else:
        selected = shutil.which(command)
        if selected is None:
            raise SpecificationError(f"command not found on PATH: {command}")
        path = Path(selected).resolve()
    if not path.is_file() or not os.access(path, os.X_OK):
        raise SpecificationError(f"command is not executable: {command}")
    return str(path)


# [Implementation 6] Sequential orchestration baseline.
def run_cases(
    cases: Sequence[Case],
    command: Sequence[str],
    jobs: int,
) -> tuple[Result, ...]:
    if jobs < 1:
        raise SpecificationError("jobs must be at least 1")
    if jobs == 1:
        return tuple(run_case(case, command) for case in cases)

    # [Implementation 9] Bounded concurrent execution.
    try:
        with ThreadPoolExecutor(max_workers=jobs) as executor:
            return tuple(executor.map(lambda case: run_case(case, command), cases))
    except OSError as error:
        raise ExecutionError(f"cannot create execution workers: {error}") from error


# [Implementation 6-1] Result presentation policy.
def print_results(
    results: Sequence[Result],
    *,
    stdout: TextIO,
    stderr: TextIO,
) -> None:
    for result in results:
        destination = stdout if result.passed else stderr
        print(("PASS " if result.passed else "FAIL ") + result.name, file=destination)
        for failure in result.failures:
            print(f"  - {failure}", file=destination)


# [Implementation 6-2] Match exit-status policy.
def exit_status(results: Sequence[Result]) -> int:
    return 0 if all(result.passed for result in results) else 1
