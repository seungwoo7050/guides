"""계층별 증거 진단을 구현하는 학습자 파일입니다."""

from __future__ import annotations

from dataclasses import dataclass

from .model import Trace


@dataclass(frozen=True)
class Diagnosis:
    code: str
    layer: str | None
    last_success: str | None
    first_failure: str | None
    summary: str
    evidence: tuple[str, ...]
    next_checks: tuple[str, ...]

    @property
    def healthy(self) -> bool:
        return self.code == "HEALTHY"

    def to_mapping(self) -> dict[str, object]:
        raise NotImplementedError("진단 직렬화를 구현하세요")


def diagnose(trace: Trace) -> Diagnosis:
    raise NotImplementedError("첫 실패와 단계별 세부 진단을 구현하세요")


def render_text(diagnosis: Diagnosis) -> str:
    raise NotImplementedError("사람이 읽는 출력 형식을 구현하세요")
