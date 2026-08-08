"""실행 주체의 상태 전이와 대기 큐를 결정론적으로 모델링합니다."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Deque, Mapping


class TaskState(str, Enum):
    """모델에서 사용하는 최소 실행 상태입니다."""

    NEW = "new"
    READY = "ready"
    RUNNING = "running"
    BLOCKED = "blocked"
    TERMINATED = "terminated"


@dataclass(slots=True)
class Task:
    """한 실행 주체가 소유하는 상태입니다."""

    tid: str
    state: TaskState = TaskState.NEW
    wait_channel: str | None = None
    block_reason: str | None = None
    transitions: list[str] = field(default_factory=list)

    def record(self, transition: str) -> None:
        self.transitions.append(transition)


class StateInvariantError(ValueError):
    """실행 상태와 큐의 관계가 모순일 때 발생합니다."""


@dataclass
class KernelState:
    """CPU 하나, 실행 가능 큐와 대기 큐를 함께 관리합니다."""

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
        self.assert_invariants()
        return task

    def admit(self, tid: str) -> None:
        task = self._require(tid)
        if task.state is not TaskState.NEW:
            raise StateInvariantError(f"NEW 작업만 admit할 수 있습니다: {tid}")
        task.state = TaskState.READY
        task.record("new->ready")
        self.ready.append(tid)
        self.assert_invariants()

    def dispatch(self) -> str | None:
        if self.running is not None:
            raise StateInvariantError("CPU에 이미 실행 중인 작업이 있습니다.")
        if not self.ready:
            self.assert_invariants()
            return None
        tid = self.ready.popleft()
        task = self._require(tid)
        if task.state is not TaskState.READY:
            raise StateInvariantError(f"실행 가능 큐의 작업 상태가 READY가 아닙니다: {tid}")
        task.state = TaskState.RUNNING
        task.record("ready->running")
        self.running = tid
        self.assert_invariants()
        return tid

    def preempt(self) -> str:
        task = self._running_task()
        self.running = None
        task.state = TaskState.READY
        task.record("running->ready:preempt")
        self.ready.append(task.tid)
        self.assert_invariants()
        return task.tid

    def yield_cpu(self) -> str:
        task = self._running_task()
        self.running = None
        task.state = TaskState.READY
        task.record("running->ready:yield")
        self.ready.append(task.tid)
        self.assert_invariants()
        return task.tid

    def block(self, channel: str, reason: str) -> str:
        if not channel:
            raise ValueError("대기 채널은 비어 있을 수 없습니다.")
        task = self._running_task()
        self.running = None
        task.state = TaskState.BLOCKED
        task.wait_channel = channel
        task.block_reason = reason
        task.record(f"running->blocked:{channel}")
        self.wait_queues.setdefault(channel, deque()).append(task.tid)
        self.assert_invariants()
        return task.tid

    def wake_one(self, channel: str) -> str | None:
        queue = self.wait_queues.get(channel)
        if not queue:
            self.assert_invariants()
            return None
        tid = queue.popleft()
        if not queue:
            self.wait_queues.pop(channel, None)
        task = self._require(tid)
        if task.state is not TaskState.BLOCKED or task.wait_channel != channel:
            raise StateInvariantError(f"대기 큐와 작업 상태가 일치하지 않습니다: {tid}")
        task.state = TaskState.READY
        task.wait_channel = None
        task.block_reason = None
        task.record(f"blocked->ready:{channel}")
        self.ready.append(tid)
        self.assert_invariants()
        return tid

    def wake_all(self, channel: str) -> list[str]:
        awakened: list[str] = []
        while True:
            tid = self.wake_one(channel)
            if tid is None:
                break
            awakened.append(tid)
        return awakened

    def exit_running(self) -> str:
        task = self._running_task()
        self.running = None
        task.state = TaskState.TERMINATED
        task.wait_channel = None
        task.block_reason = None
        task.record("running->terminated")
        self.completed.append(task.tid)
        self.assert_invariants()
        return task.tid

    def snapshot(self) -> dict[str, Any]:
        return {
            "running": self.running,
            "ready": list(self.ready),
            "wait_queues": {name: list(queue) for name, queue in sorted(self.wait_queues.items())},
            "completed": list(self.completed),
            "tasks": {
                tid: {
                    "state": task.state.value,
                    "wait_channel": task.wait_channel,
                    "block_reason": task.block_reason,
                    "transitions": list(task.transitions),
                }
                for tid, task in sorted(self.tasks.items())
            },
        }

    def assert_invariants(self) -> None:
        ready_items = list(self.ready)
        if len(set(ready_items)) != len(ready_items):
            raise StateInvariantError("실행 가능 큐에 같은 작업이 중복되었습니다.")
        if self.running is not None and self.running in ready_items:
            raise StateInvariantError("실행 중인 작업이 실행 가능 큐에도 있습니다.")

        blocked_locations: dict[str, str] = {}
        for channel, queue in self.wait_queues.items():
            if not channel:
                raise StateInvariantError("이름이 없는 대기 큐가 있습니다.")
            for tid in queue:
                if tid in blocked_locations:
                    raise StateInvariantError(f"작업이 둘 이상의 대기 큐에 있습니다: {tid}")
                blocked_locations[tid] = channel

        completed_set = set(self.completed)
        if len(completed_set) != len(self.completed):
            raise StateInvariantError("완료 목록에 같은 작업이 중복되었습니다.")

        for tid, task in self.tasks.items():
            if task.tid != tid:
                raise StateInvariantError(f"작업 key와 내부 식별자가 다릅니다: key={tid} task={task.tid}")
            in_ready = tid in ready_items
            is_running = tid == self.running
            wait_channel = blocked_locations.get(tid)
            in_completed = tid in completed_set

            if task.state is not TaskState.BLOCKED and (task.wait_channel is not None or task.block_reason is not None):
                raise StateInvariantError(f"대기하지 않는 작업에 wait metadata가 남아 있습니다: {tid}")

            if task.state is TaskState.NEW:
                if in_ready or is_running or wait_channel is not None or in_completed:
                    raise StateInvariantError(f"NEW 작업이 실행 자료구조에 노출되었습니다: {tid}")
            elif task.state is TaskState.READY:
                if not in_ready or is_running or wait_channel is not None or in_completed:
                    raise StateInvariantError(f"READY 작업의 위치가 잘못되었습니다: {tid}")
            elif task.state is TaskState.RUNNING:
                if not is_running or in_ready or wait_channel is not None or in_completed:
                    raise StateInvariantError(f"RUNNING 작업의 위치가 잘못되었습니다: {tid}")
            elif task.state is TaskState.BLOCKED:
                if wait_channel is None or task.wait_channel != wait_channel:
                    raise StateInvariantError(f"BLOCKED 작업이 정확한 대기 큐에 없습니다: {tid}")
                if not task.block_reason:
                    raise StateInvariantError(f"BLOCKED 작업에 대기 이유가 없습니다: {tid}")
                if in_ready or is_running or in_completed:
                    raise StateInvariantError(f"BLOCKED 작업이 다른 실행 위치에도 있습니다: {tid}")
            elif task.state is TaskState.TERMINATED:
                if not in_completed or in_ready or is_running or wait_channel is not None:
                    raise StateInvariantError(f"TERMINATED 작업의 위치가 잘못되었습니다: {tid}")

        if self.running is not None and self.running not in self.tasks:
            raise StateInvariantError("존재하지 않는 작업이 CPU를 사용하고 있습니다.")
        for tid in ready_items + list(blocked_locations) + self.completed:
            if tid not in self.tasks:
                raise StateInvariantError(f"자료구조가 존재하지 않는 작업을 참조합니다: {tid}")

    @classmethod
    def validate_snapshot(cls, snapshot: Mapping[str, Any]) -> None:
        model = cls()
        task_data = snapshot.get("tasks")
        if not isinstance(task_data, Mapping):
            raise StateInvariantError("snapshot.tasks가 객체가 아닙니다.")
        for tid, raw in task_data.items():
            if not isinstance(tid, str) or not isinstance(raw, Mapping):
                raise StateInvariantError("작업 항목 형식이 잘못되었습니다.")
            state = TaskState(str(raw.get("state")))
            model.tasks[tid] = Task(
                tid=tid,
                state=state,
                wait_channel=raw.get("wait_channel"),
                block_reason=raw.get("block_reason"),
            )
        ready = snapshot.get("ready", [])
        completed = snapshot.get("completed", [])
        wait_queues = snapshot.get("wait_queues", {})
        if not isinstance(ready, list) or not isinstance(completed, list) or not isinstance(wait_queues, Mapping):
            raise StateInvariantError("snapshot의 큐 형식이 잘못되었습니다.")
        model.ready = deque(str(item) for item in ready)
        model.running = snapshot.get("running")
        model.completed = [str(item) for item in completed]
        model.wait_queues = {
            str(channel): deque(str(item) for item in items)
            for channel, items in wait_queues.items()
            if isinstance(items, list)
        }
        if len(model.wait_queues) != len(wait_queues):
            raise StateInvariantError("대기 큐 항목이 배열이 아닙니다.")
        model.assert_invariants()

    def _require(self, tid: str) -> Task:
        try:
            return self.tasks[tid]
        except KeyError as exc:
            raise KeyError(f"작업을 찾을 수 없습니다: {tid}") from exc

    def _running_task(self) -> Task:
        if self.running is None:
            raise StateInvariantError("실행 중인 작업이 없습니다.")
        task = self._require(self.running)
        if task.state is not TaskState.RUNNING:
            raise StateInvariantError("running 포인터와 작업 상태가 일치하지 않습니다.")
        return task
