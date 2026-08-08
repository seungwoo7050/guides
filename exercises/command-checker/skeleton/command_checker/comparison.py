"""3단계에서 세 결과 채널의 순수 비교를 구현합니다."""

from __future__ import annotations

from .model import Case


def compare_observation(
    case: Case,
    *,
    returncode: int | None,
    stdout: str,
    stderr: str,
    timed_out: bool = False,
    exceeded_stream: str | None = None,
) -> tuple[str, ...]:
    raise NotImplementedError("stage 03: 결과 비교를 구현하십시오.")
