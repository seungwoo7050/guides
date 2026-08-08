"""5단계와 7단계에서 외부 프로세스 수명을 구현합니다."""

from __future__ import annotations

import subprocess
from typing import Any, Sequence

from .model import Case, Result


def _collect_process(
    process: subprocess.Popen[bytes],
    input_bytes: bytes,
    *,
    timeout: float,
    output_limit: int,
) -> tuple[bytes, bytes, bool, str | None]:
    raise NotImplementedError("stage 07: 제한된 프로세스 수집을 구현하십시오.")


def run_case(case: Case, command: Sequence[str]) -> Result:
    raise NotImplementedError("stage 05: 외부 프로세스 실행을 구현하십시오.")
