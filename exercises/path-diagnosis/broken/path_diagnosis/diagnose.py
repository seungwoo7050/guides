"""검사가 알려진 오답을 거부하는지 확인하는 의도적 잘못된 구현입니다."""

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
        return {
            "code": self.code,
            "healthy": self.healthy,
            "layer": self.layer,
            "last_success": self.last_success,
            "first_failure": self.first_failure,
            "summary": self.summary,
            "evidence": list(self.evidence),
            "next_checks": list(self.next_checks),
        }


def diagnose(trace: Trace) -> Diagnosis:
    return Diagnosis(
        code="HEALTHY",
        layer=None,
        last_success="http",
        first_failure=None,
        summary="모든 요청을 정상으로 잘못 분류합니다.",
        evidence=(),
        next_checks=(),
    )


def render_text(diagnosis: Diagnosis) -> str:
    return f"code: {diagnosis.code}"
