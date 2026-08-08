"""조건 대기, 세마포어와 깨우기 손실을 상태 모델로 설명합니다."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field


class SynchronizationError(ValueError):
    """동기화 상태가 계약을 위반할 때 발생합니다."""


@dataclass(frozen=True, slots=True)
class WaitToken:
    """조건을 확인한 순간의 사건 세대를 기록합니다."""

    channel: str
    generation: int


@dataclass
class ConditionChannel:
    """조건 검사와 대기 등록 사이의 사건 유실을 방지하는 모델입니다."""

    name: str
    generation: int = 0
    waiters: dict[str, int] = field(default_factory=dict)

    def prepare_wait(self) -> WaitToken:
        return WaitToken(channel=self.name, generation=self.generation)

    def commit_wait(self, tid: str, token: WaitToken) -> bool:
        if token.channel != self.name:
            raise SynchronizationError("다른 조건 채널의 토큰입니다.")
        if tid in self.waiters:
            raise SynchronizationError(f"이미 대기 중인 작업입니다: {tid}")
        if token.generation != self.generation:
            return False
        self.waiters[tid] = token.generation
        return True

    def cancel_wait(self, tid: str) -> bool:
        return self.waiters.pop(tid, None) is not None

    def notify_one(self) -> str | None:
        self.generation += 1
        if not self.waiters:
            return None
        tid = next(iter(self.waiters))
        self.waiters.pop(tid)
        return tid

    def notify_all(self) -> list[str]:
        self.generation += 1
        awakened = list(self.waiters)
        self.waiters.clear()
        return awakened


@dataclass
class CountingSemaphore:
    """허가 수와 FIFO 대기자를 함께 관리하는 세마포어 모델입니다."""

    permits: int
    waiters: deque[str] = field(default_factory=deque)
    granted: set[str] = field(default_factory=set)

    def __post_init__(self) -> None:
        if self.permits < 0:
            raise ValueError("세마포어 허가 수는 음수일 수 없습니다.")

    def acquire(self, tid: str) -> bool:
        if tid in self.granted or tid in self.waiters:
            raise SynchronizationError(f"같은 작업이 허가를 중복 요청했습니다: {tid}")
        if self.permits > 0:
            self.permits -= 1
            self.granted.add(tid)
            return True
        self.waiters.append(tid)
        return False

    def release(self, tid: str) -> str | None:
        if tid not in self.granted:
            raise SynchronizationError(f"허가를 소유하지 않은 작업입니다: {tid}")
        self.granted.remove(tid)
        if self.waiters:
            awakened = self.waiters.popleft()
            self.granted.add(awakened)
            return awakened
        self.permits += 1
        return None

    def assert_invariants(self) -> None:
        if self.permits < 0:
            raise SynchronizationError("허가 수가 음수입니다.")
        if len(set(self.waiters)) != len(self.waiters):
            raise SynchronizationError("세마포어 대기 큐에 중복 작업이 있습니다.")
        if self.granted.intersection(self.waiters):
            raise SynchronizationError("한 작업이 허가 소유자이면서 대기자입니다.")
