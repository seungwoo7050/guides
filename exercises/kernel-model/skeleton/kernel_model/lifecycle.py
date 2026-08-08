"""실행 주체 상태 모델의 학습자 구현 골격입니다."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Deque, Mapping


class TaskState(str, Enum):
    NEW = "new"
    READY = "ready"
    RUNNING = "running"
    BLOCKED = "blocked"
    TERMINATED = "terminated"


@dataclass(slots=True)
class Task:
    tid: str
    state: TaskState = TaskState.NEW
    wait_channel: str | None = None
    block_reason: str | None = None
    transitions: list[str] = field(default_factory=list)

    def record(self, transition: str) -> None:
        self.transitions.append(transition)


class StateInvariantError(ValueError):
    pass


@dataclass
class KernelState:
    tasks: dict[str, Task] = field(default_factory=dict)
    ready: Deque[str] = field(default_factory=deque)
    running: str | None = None
    wait_queues: dict[str, Deque[str]] = field(default_factory=dict)
    completed: list[str] = field(default_factory=list)

    def add(self, tid: str) -> Task:
        if not tid or tid in self.tasks:
            raise ValueError(f"새 작업 식별자가 유효하지 않습니다: {tid!r}")
        task = Task(tid=tid)
        self.tasks[tid] = task
        task.record("created")
        return task

    def admit(self, tid: str) -> None:
        raise NotImplementedError("NEW 작업을 READY 큐에 넣으세요.")

    def dispatch(self) -> str | None:
        raise NotImplementedError("READY 큐에서 한 작업을 RUNNING으로 전환하세요.")

    def preempt(self) -> str:
        raise NotImplementedError("RUNNING 작업을 READY로 되돌리세요.")

    def yield_cpu(self) -> str:
        raise NotImplementedError("자발적 양보를 상태 전이로 기록하세요.")

    def block(self, channel: str, reason: str) -> str:
        raise NotImplementedError("RUNNING 작업을 정확히 한 대기 큐로 옮기세요.")

    def wake_one(self, channel: str) -> str | None:
        raise NotImplementedError("대기 큐의 한 작업을 READY로 깨우세요.")

    def wake_all(self, channel: str) -> list[str]:
        awakened: list[str] = []
        while True:
            tid = self.wake_one(channel)
            if tid is None:
                return awakened
            awakened.append(tid)

    def exit_running(self) -> str:
        raise NotImplementedError("RUNNING 작업을 TERMINATED로 전환하세요.")

    def snapshot(self) -> dict[str, Any]:
        raise NotImplementedError("상태를 JSON 직렬화 가능한 객체로 반환하세요.")

    def assert_invariants(self) -> None:
        raise NotImplementedError("상태와 큐의 일대일 관계를 검사하세요.")

    @classmethod
    def validate_snapshot(cls, snapshot: Mapping[str, Any]) -> None:
        raise NotImplementedError("snapshot을 모델로 복원한 뒤 불변식을 검사하세요.")
