"""주소 공간, COW와 페이지 교체의 학습자 구현 골격입니다."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Iterable, Mapping


class FaultKind(str, Enum):
    NOT_MAPPED = "not-mapped"
    NOT_PRESENT = "not-present"
    PROTECTION = "protection"
    COPY_ON_WRITE = "copy-on-write"


class MemoryFault(RuntimeError):
    def __init__(self, kind: FaultKind, pid: str, vpn: int, message: str) -> None:
        super().__init__(message)
        self.kind = kind
        self.pid = pid
        self.vpn = vpn


class MemoryInvariantError(ValueError):
    pass


@dataclass
class PageTableEntry:
    frame: int | None = None
    present: bool = False
    readable: bool = True
    writable: bool = False
    cow: bool = False
    backing_value: int = 0


@dataclass
class Frame:
    value: int
    refcount: int = 1
    dirty: bool = False
    referenced: bool = False


@dataclass
class AddressSpace:
    pid: str
    pages: dict[int, PageTableEntry] = field(default_factory=dict)


@dataclass
class MemoryManager:
    max_frames: int = 64
    spaces: dict[str, AddressSpace] = field(default_factory=dict)
    frames: dict[int, Frame] = field(default_factory=dict)
    _next_frame: int = 0

    def create_process(self, pid: str) -> None:
        if not pid or pid in self.spaces:
            raise ValueError(f"프로세스 식별자가 유효하지 않습니다: {pid!r}")
        self.spaces[pid] = AddressSpace(pid)

    def map_demand_zero(self, pid: str, vpn: int, *, writable: bool = True) -> None:
        raise NotImplementedError("not-present demand-zero PTE를 만드세요.")

    def map_value(self, pid: str, vpn: int, value: int, *, writable: bool = True) -> None:
        raise NotImplementedError("프레임을 할당하고 present PTE를 만드세요.")

    def read(self, pid: str, vpn: int) -> int:
        raise NotImplementedError("매핑·권한·present 상태를 검사한 뒤 읽으세요.")

    def write(self, pid: str, vpn: int, value: int) -> FaultKind | None:
        raise NotImplementedError("보호 오류와 COW 복사를 구분해 처리하세요.")

    def fork(self, parent_pid: str, child_pid: str) -> None:
        raise NotImplementedError("쓰기 가능한 공유 페이지를 COW로 바꾸세요.")

    def unmap(self, pid: str, vpn: int) -> None:
        raise NotImplementedError("PTE 제거와 frame refcount 감소를 함께 처리하세요.")

    def destroy_process(self, pid: str) -> None:
        raise NotImplementedError("주소 공간의 모든 frame 참조를 해제하세요.")

    def snapshot(self) -> dict[str, Any]:
        raise NotImplementedError("주소 공간과 프레임 상태를 직렬화하세요.")

    def assert_invariants(self) -> None:
        raise NotImplementedError("PTE 참조 수와 frame refcount를 비교하세요.")

    @classmethod
    def validate_snapshot(cls, snapshot: Mapping[str, Any]) -> None:
        raise NotImplementedError("snapshot을 복원하고 COW 불변식을 검사하세요.")


@dataclass(frozen=True)
class ReplacementResult:
    policy: str
    faults: int
    evictions: tuple[int, ...]
    frames: tuple[int, ...]


def simulate_replacement(references: Iterable[int], capacity: int, policy: str) -> ReplacementResult:
    raise NotImplementedError("FIFO, LRU와 Clock 교체 정책을 구현하세요.")
