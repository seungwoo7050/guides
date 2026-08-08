"""CPU 스케줄링 정책의 학습자 구현 골격입니다."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Iterable


class Policy(str, Enum):
    FCFS = "fcfs"
    SJF = "sjf"
    PRIORITY = "priority"
    RR = "rr"
    MLFQ = "mlfq"


@dataclass(frozen=True, slots=True)
class JobSpec:
    tid: str
    arrival: int
    cpu_bursts: tuple[int, ...]
    io_waits: tuple[int, ...] = ()
    priority: int = 0

    def validate(self) -> None:
        if not self.tid or self.arrival < 0 or not self.cpu_bursts:
            raise ValueError("작업 명세가 유효하지 않습니다.")
        if any(value <= 0 for value in self.cpu_bursts + self.io_waits):
            raise ValueError("버스트와 대기 시간은 양수여야 합니다.")
        if len(self.io_waits) != len(self.cpu_bursts) - 1:
            raise ValueError("CPU 버스트 사이마다 I/O 대기가 필요합니다.")


@dataclass(frozen=True)
class Tick:
    time: int
    running: str | None
    ready: tuple[str, ...]
    blocked: tuple[tuple[str, int], ...]


@dataclass(frozen=True)
class JobMetrics:
    response: int
    waiting: int
    turnaround: int


@dataclass(frozen=True)
class ScheduleResult:
    policy: Policy
    timeline: tuple[Tick, ...]
    completion_order: tuple[str, ...]
    metrics: dict[str, JobMetrics]

    @property
    def makespan(self) -> int:
        return len(self.timeline)

    @property
    def cpu_busy_ticks(self) -> int:
        return sum(1 for tick in self.timeline if tick.running is not None)


def simulate(
    jobs: Iterable[JobSpec],
    policy: Policy | str,
    *,
    quantum: int = 2,
    max_time: int = 100_000,
) -> ScheduleResult:
    raise NotImplementedError("도착, I/O wakeup, 선택, 실행과 완료를 tick 순서로 구현하세요.")
