"""운영체제 상태 모델의 학습자 구현 골격입니다."""

from .deadlock import detect_deadlocked, find_wait_cycle, safe_sequence
from .device_io import DeviceQueue, RequestState
from .filesystem import FileSystemModel
from .journal import Journal
from .lifecycle import KernelState, StateInvariantError, TaskState
from .paging import FaultKind, MemoryManager, simulate_replacement
from .scheduler import JobSpec, Policy, simulate
from .synchronization import ConditionChannel, CountingSemaphore

__all__ = [
    "ConditionChannel",
    "CountingSemaphore",
    "DeviceQueue",
    "FaultKind",
    "FileSystemModel",
    "JobSpec",
    "Journal",
    "KernelState",
    "MemoryManager",
    "Policy",
    "RequestState",
    "StateInvariantError",
    "TaskState",
    "detect_deadlocked",
    "find_wait_cycle",
    "safe_sequence",
    "simulate",
    "simulate_replacement",
]
