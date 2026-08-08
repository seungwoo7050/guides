"""조건 대기와 세마포어의 학습자 구현 골격입니다."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field


class SynchronizationError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class WaitToken:
    channel: str
    generation: int


@dataclass
class ConditionChannel:
    name: str
    generation: int = 0
    waiters: dict[str, int] = field(default_factory=dict)

    def prepare_wait(self) -> WaitToken:
        return WaitToken(self.name, self.generation)

    def commit_wait(self, tid: str, token: WaitToken) -> bool:
        raise NotImplementedError("사건 세대가 바뀌었다면 잠들지 않도록 구현하세요.")

    def cancel_wait(self, tid: str) -> bool:
        return self.waiters.pop(tid, None) is not None

    def notify_one(self) -> str | None:
        raise NotImplementedError("세대를 올리고 한 대기자를 깨우세요.")

    def notify_all(self) -> list[str]:
        raise NotImplementedError("세대를 올리고 모든 대기자를 깨우세요.")


@dataclass
class CountingSemaphore:
    permits: int
    waiters: deque[str] = field(default_factory=deque)
    granted: set[str] = field(default_factory=set)

    def acquire(self, tid: str) -> bool:
        raise NotImplementedError("허가가 없으면 FIFO 큐에 등록하세요.")

    def release(self, tid: str) -> str | None:
        raise NotImplementedError("대기자에게 허가를 직접 넘기거나 permits를 늘리세요.")

    def assert_invariants(self) -> None:
        raise NotImplementedError("대기자와 허가 소유자가 겹치지 않는지 검사하세요.")
