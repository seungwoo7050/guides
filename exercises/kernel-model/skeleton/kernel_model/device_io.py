"""장치 요청과 DMA 수명의 학습자 구현 골격입니다."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Mapping


class RequestState(str, Enum):
    QUEUED = "queued"
    IN_FLIGHT = "in-flight"
    COMPLETED = "completed"
    CANCEL_PENDING = "cancel-pending"
    CANCELLED = "cancelled"
    REAPED = "reaped"


class DeviceStateError(ValueError):
    pass


@dataclass
class IORequest:
    request_id: int
    owner: str
    buffer_pages: tuple[int, ...]
    length: int
    state: RequestState = RequestState.QUEUED
    pinned: bool = False
    bytes_transferred: int = 0
    error: str | None = None


@dataclass
class DeviceQueue:
    queue_depth: int = 8
    requests: dict[int, IORequest] = field(default_factory=dict)
    pending: deque[int] = field(default_factory=deque)
    in_flight: set[int] = field(default_factory=set)
    completions: dict[str, deque[int]] = field(default_factory=dict)
    _next_id: int = 1

    def submit(self, owner: str, buffer_pages: tuple[int, ...], length: int) -> int:
        raise NotImplementedError("queue depth를 확인하고 QUEUED 요청을 만드세요.")

    def start_next(self) -> IORequest | None:
        raise NotImplementedError("요청을 IN_FLIGHT로 바꾸고 buffer를 pin하세요.")

    def cancel(self, owner: str, request_id: int) -> RequestState:
        raise NotImplementedError("queued와 in-flight 취소를 서로 다르게 처리하세요.")

    def interrupt_complete(
        self,
        request_id: int,
        *,
        bytes_transferred: int,
        error: str | None = None,
    ) -> None:
        raise NotImplementedError("완료를 한 번만 기록하고 buffer pin을 해제하세요.")

    def reap(self, owner: str) -> IORequest | None:
        raise NotImplementedError("소유자의 완료 큐에서 결과를 회수하세요.")

    def assert_invariants(self) -> None:
        raise NotImplementedError("요청 상태와 큐·pin 위치를 비교하세요.")

    def snapshot(self) -> dict[str, Any]:
        raise NotImplementedError("장치 큐 상태를 직렬화하세요.")

    @classmethod
    def validate_snapshot(cls, snapshot: Mapping[str, Any]) -> None:
        raise NotImplementedError("snapshot을 복원하고 상태 불변식을 검사하세요.")
