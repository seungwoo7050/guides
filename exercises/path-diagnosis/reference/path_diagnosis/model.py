"""계층별 관찰 trace의 입력 계약과 불변식을 정의합니다."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any, Mapping

STAGE_ORDER = ("dns", "route", "neighbor", "path", "transport", "tls", "http")
VALID_STATUSES = frozenset({"ok", "failed", "not-run"})
VALID_TRANSPORTS = frozenset({"tcp", "udp", "quic"})


class TraceFormatError(ValueError):
    """입력 trace가 공개 계약을 만족하지 않을 때 발생합니다."""


# [Implementation 1] 진단할 요청의 이름·port·transport·application 경계를 먼저 검증합니다.
@dataclass(frozen=True)
class RequestContext:
    """진단하려는 요청의 최소 식별 정보입니다."""

    name: str
    port: int
    transport: str
    application: str

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "RequestContext":
        if not isinstance(value, Mapping):
            raise TraceFormatError("request는 객체여야 합니다")
        name = _required_text(value, "name", "request")
        application = _required_text(value, "application", "request")
        transport = _required_text(value, "transport", "request").lower()
        if transport not in VALID_TRANSPORTS:
            supported = ", ".join(sorted(VALID_TRANSPORTS))
            raise TraceFormatError(f"지원하지 않는 transport입니다: {transport}; 지원: {supported}")
        port = value.get("port")
        if isinstance(port, bool) or not isinstance(port, int) or not 1 <= port <= 65535:
            raise TraceFormatError("request.port는 1부터 65535 사이의 정수여야 합니다")
        return cls(name=name, port=port, transport=transport, application=application)

    def to_mapping(self) -> dict[str, object]:
        return {
            "name": self.name,
            "port": self.port,
            "transport": self.transport,
            "application": self.application,
        }


# [Implementation 1-1] 한 계층의 status와 관찰 facts를 불변 evidence로 정규화합니다.
@dataclass(frozen=True)
class StageEvidence:
    """한 계층에서 수집한 상태, 관찰 문장과 구조화된 사실입니다."""

    stage: str
    status: str
    observation: str
    facts: Mapping[str, Any]

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any], expected_stage: str) -> "StageEvidence":
        if not isinstance(value, Mapping):
            raise TraceFormatError(f"{expected_stage} 단계는 객체여야 합니다")
        stage = _required_text(value, "stage", expected_stage)
        if stage != expected_stage:
            raise TraceFormatError(
                f"단계 순서가 잘못되었습니다: {expected_stage} 위치에 {stage}가 있습니다"
            )
        status = _required_text(value, "status", stage)
        if status not in VALID_STATUSES:
            raise TraceFormatError(f"{stage}.status가 잘못되었습니다: {status}")
        observation = _required_text(value, "observation", stage)
        facts = value.get("facts")
        if not isinstance(facts, Mapping):
            raise TraceFormatError(f"{stage}.facts는 객체여야 합니다")
        return cls(stage=stage, status=status, observation=observation, facts=dict(facts))

    def to_mapping(self) -> dict[str, object]:
        return {
            "stage": self.stage,
            "status": self.status,
            "observation": self.observation,
            "facts": dict(self.facts),
        }


# [Implementation 1-2] 일곱 계층의 순서와 첫 실패 전후 progression을 Trace가 소유합니다.
@dataclass(frozen=True)
class Trace:
    """정해진 계층 순서와 상태 진행을 만족하는 전체 관찰 기록입니다."""

    request: RequestContext
    stages: tuple[StageEvidence, ...]

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "Trace":
        if not isinstance(value, Mapping):
            raise TraceFormatError("trace 최상위 값은 객체여야 합니다")
        request = RequestContext.from_mapping(value.get("request"))
        raw_stages = value.get("stages")
        if not isinstance(raw_stages, list):
            raise TraceFormatError("stages는 배열이어야 합니다")
        if len(raw_stages) != len(STAGE_ORDER):
            raise TraceFormatError(
                f"stages는 {len(STAGE_ORDER)}개여야 합니다: 실제 {len(raw_stages)}개"
            )
        stages = tuple(
            StageEvidence.from_mapping(raw_stage, expected_stage)
            for raw_stage, expected_stage in zip(raw_stages, STAGE_ORDER, strict=True)
        )
        _validate_progression(stages)
        return cls(request=request, stages=stages)

    def to_mapping(self) -> dict[str, object]:
        return {
            "request": self.request.to_mapping(),
            "stages": [stage.to_mapping() for stage in self.stages],
        }

    @property
    def first_failure(self) -> StageEvidence | None:
        return next((stage for stage in self.stages if stage.status == "failed"), None)

    @property
    def last_success(self) -> StageEvidence | None:
        failure = self.first_failure
        if failure is None:
            return self.stages[-1]
        failure_index = STAGE_ORDER.index(failure.stage)
        if failure_index == 0:
            return None
        return self.stages[failure_index - 1]


# [Implementation 1-3] 파일·JSON·구조 오류를 하나의 공개 TraceFormatError 경계로 바꿉니다.
def load_trace(path: str | Path) -> Trace:
    """JSON 파일을 읽고 모든 입력 오류를 TraceFormatError로 통일합니다."""

    source = Path(path)
    try:
        text = source.read_text(encoding="utf-8")
    except OSError as error:
        raise TraceFormatError(f"trace 파일을 읽을 수 없습니다: {source}: {error}") from error
    try:
        value = json.loads(text)
    except json.JSONDecodeError as error:
        raise TraceFormatError(
            f"JSON 구문이 잘못되었습니다: {source}:{error.lineno}:{error.colno}"
        ) from error
    try:
        return Trace.from_mapping(value)
    except TraceFormatError:
        raise
    except (KeyError, TypeError, ValueError) as error:
        raise TraceFormatError(f"trace 구조가 잘못되었습니다: {error}") from error


def _required_text(value: Mapping[str, Any], key: str, context: str) -> str:
    item = value.get(key)
    if not isinstance(item, str) or not item.strip():
        raise TraceFormatError(f"{context}.{key}는 비어 있지 않은 문자열이어야 합니다")
    return item.strip()


def _validate_progression(stages: tuple[StageEvidence, ...]) -> None:
    failure_seen = False
    for stage in stages:
        if not failure_seen:
            if stage.status == "ok":
                continue
            if stage.status == "failed":
                failure_seen = True
                continue
            raise TraceFormatError(
                f"앞선 실패 없이 {stage.stage} 단계가 not-run일 수 없습니다"
            )
        if stage.status != "not-run":
            raise TraceFormatError(
                f"첫 실패 뒤 {stage.stage} 단계는 not-run이어야 합니다"
            )
