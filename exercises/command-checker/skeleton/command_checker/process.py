"""5단계와 7단계에서 외부 프로세스 수명을 구현합니다."""

from __future__ import annotations

from typing import Sequence

from .model import Case, Result


def run_case(case: Case, command: Sequence[str]) -> Result:
    raise NotImplementedError("stage 05: 외부 프로세스 실행을 구현하십시오.")
