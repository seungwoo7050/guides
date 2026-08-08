"""계층별 관찰 trace의 입력 계약을 구현하는 학습자 파일입니다."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

STAGE_ORDER = ("dns", "route", "neighbor", "path", "transport", "tls", "http")
VALID_STATUSES = frozenset({"ok", "failed", "not-run"})
VALID_TRANSPORTS = frozenset({"tcp", "udp", "quic"})


class TraceFormatError(ValueError):
    """입력 trace가 공개 계약을 만족하지 않을 때 발생합니다."""


@dataclass(frozen=True)
class RequestContext:
    name: str
    port: int
    transport: str
    application: str

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "RequestContext":
        raise NotImplementedError("request 필드 검증을 구현하세요")

    def to_mapping(self) -> dict[str, object]:
        raise NotImplementedError("request 직렬화를 구현하세요")


@dataclass(frozen=True)
class StageEvidence:
    stage: str
    status: str
    observation: str
    facts: Mapping[str, Any]

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any], expected_stage: str) -> "StageEvidence":
        raise NotImplementedError("단계별 증거 검증을 구현하세요")

    def to_mapping(self) -> dict[str, object]:
        raise NotImplementedError("단계별 증거 직렬화를 구현하세요")


@dataclass(frozen=True)
class Trace:
    request: RequestContext
    stages: tuple[StageEvidence, ...]

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "Trace":
        raise NotImplementedError("계층 순서와 상태 진행 검증을 구현하세요")

    def to_mapping(self) -> dict[str, object]:
        raise NotImplementedError("trace 직렬화를 구현하세요")

    @property
    def first_failure(self) -> StageEvidence | None:
        raise NotImplementedError("첫 실패 단계를 구현하세요")

    @property
    def last_success(self) -> StageEvidence | None:
        raise NotImplementedError("마지막 성공 단계를 구현하세요")


def load_trace(path: str | Path) -> Trace:
    raise NotImplementedError("JSON 파일 읽기와 오류 변환을 구현하세요")
