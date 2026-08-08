"""주소 공간, 페이지 폴트, COW와 페이지 교체 정책을 모델링합니다."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Iterable, Mapping


class FaultKind(str, Enum):
    NOT_MAPPED = "not-mapped"
    NOT_PRESENT = "not-present"
    PROTECTION = "protection"
    COPY_ON_WRITE = "copy-on-write"


class MemoryFault(RuntimeError):
    """모델이 커널 개입이 필요한 접근을 발견했을 때 발생합니다."""

    def __init__(self, kind: FaultKind, pid: str, vpn: int, message: str) -> None:
        super().__init__(message)
        self.kind = kind
        self.pid = pid
        self.vpn = vpn


class MemoryInvariantError(ValueError):
    """매핑과 물리 프레임 참조 관계가 모순일 때 발생합니다."""


@dataclass
class PageTableEntry:
    frame: int | None = None
    present: bool = False
    readable: bool = True
    writable: bool = False
    cow: bool = False
    backing_value: int = 0

    def clone(self) -> "PageTableEntry":
        return PageTableEntry(
            frame=self.frame,
            present=self.present,
            readable=self.readable,
            writable=self.writable,
            cow=self.cow,
            backing_value=self.backing_value,
        )


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
    """페이지 단위 값 하나를 저장하는 간결한 물리 메모리 모델입니다."""

    max_frames: int = 64
    spaces: dict[str, AddressSpace] = field(default_factory=dict)
    frames: dict[int, Frame] = field(default_factory=dict)
    _next_frame: int = 0

    def __post_init__(self) -> None:
        if self.max_frames <= 0:
            raise ValueError("물리 프레임 수는 양수여야 합니다.")

    def create_process(self, pid: str) -> None:
        if not pid or pid in self.spaces:
            raise ValueError(f"프로세스 식별자가 유효하지 않습니다: {pid!r}")
        self.spaces[pid] = AddressSpace(pid)

    def map_demand_zero(self, pid: str, vpn: int, *, writable: bool = True) -> None:
        space = self._space(pid)
        self._validate_vpn(vpn)
        if vpn in space.pages:
            raise MemoryInvariantError(f"이미 매핑된 페이지입니다: {pid}:{vpn}")
        space.pages[vpn] = PageTableEntry(
            present=False,
            readable=True,
            writable=writable,
            cow=False,
            backing_value=0,
        )
        self.assert_invariants()

    def map_value(self, pid: str, vpn: int, value: int, *, writable: bool = True) -> None:
        space = self._space(pid)
        self._validate_vpn(vpn)
        if vpn in space.pages:
            raise MemoryInvariantError(f"이미 매핑된 페이지입니다: {pid}:{vpn}")
        frame_id = self._allocate_frame(value)
        space.pages[vpn] = PageTableEntry(
            frame=frame_id,
            present=True,
            readable=True,
            writable=writable,
            cow=False,
            backing_value=value,
        )
        self.assert_invariants()

    def read(self, pid: str, vpn: int) -> int:
        entry = self._entry(pid, vpn)
        if not entry.readable:
            raise MemoryFault(FaultKind.PROTECTION, pid, vpn, "읽기 권한이 없습니다.")
        self._ensure_present(pid, vpn, entry)
        assert entry.frame is not None
        frame = self.frames[entry.frame]
        frame.referenced = True
        return frame.value

    def write(self, pid: str, vpn: int, value: int) -> FaultKind | None:
        entry = self._entry(pid, vpn)
        if not entry.writable and not entry.cow:
            raise MemoryFault(FaultKind.PROTECTION, pid, vpn, "쓰기 권한이 없습니다.")
        self._ensure_present(pid, vpn, entry)
        fault: FaultKind | None = None
        if entry.cow:
            self._resolve_cow(entry)
            fault = FaultKind.COPY_ON_WRITE
        assert entry.frame is not None
        frame = self.frames[entry.frame]
        frame.value = value
        frame.dirty = True
        frame.referenced = True
        entry.backing_value = value
        self.assert_invariants()
        return fault

    def fork(self, parent_pid: str, child_pid: str) -> None:
        if child_pid in self.spaces:
            raise ValueError(f"이미 존재하는 프로세스입니다: {child_pid}")
        parent = self._space(parent_pid)
        child = AddressSpace(child_pid)
        for vpn, parent_entry in parent.pages.items():
            child_entry = parent_entry.clone()
            if parent_entry.present:
                if parent_entry.frame is None:
                    raise MemoryInvariantError("present 페이지에 frame이 없습니다.")
                self.frames[parent_entry.frame].refcount += 1
                if parent_entry.writable or parent_entry.cow:
                    parent_entry.writable = False
                    parent_entry.cow = True
                    child_entry.writable = False
                    child_entry.cow = True
            child.pages[vpn] = child_entry
        self.spaces[child_pid] = child
        self.assert_invariants()

    def unmap(self, pid: str, vpn: int) -> None:
        space = self._space(pid)
        try:
            entry = space.pages.pop(vpn)
        except KeyError as exc:
            raise MemoryFault(FaultKind.NOT_MAPPED, pid, vpn, "매핑이 없습니다.") from exc
        if entry.present:
            assert entry.frame is not None
            self._decref(entry.frame)
        self.assert_invariants()

    def destroy_process(self, pid: str) -> None:
        space = self._space(pid)
        for entry in space.pages.values():
            if entry.present:
                assert entry.frame is not None
                self._decref(entry.frame)
        self.spaces.pop(pid)
        self.assert_invariants()

    def snapshot(self) -> dict[str, Any]:
        return {
            "frames": {
                str(frame_id): {
                    "value": frame.value,
                    "refcount": frame.refcount,
                    "dirty": frame.dirty,
                    "referenced": frame.referenced,
                }
                for frame_id, frame in sorted(self.frames.items())
            },
            "spaces": {
                pid: {
                    str(vpn): {
                        "frame": entry.frame,
                        "present": entry.present,
                        "readable": entry.readable,
                        "writable": entry.writable,
                        "cow": entry.cow,
                        "backing_value": entry.backing_value,
                    }
                    for vpn, entry in sorted(space.pages.items())
                }
                for pid, space in sorted(self.spaces.items())
            },
        }

    def assert_invariants(self) -> None:
        references: dict[int, list[PageTableEntry]] = {frame_id: [] for frame_id in self.frames}
        for pid, space in self.spaces.items():
            for vpn, entry in space.pages.items():
                self._validate_vpn(vpn)
                if entry.present:
                    if entry.frame is None or entry.frame not in self.frames:
                        raise MemoryInvariantError(f"매핑이 존재하지 않는 프레임을 가리킵니다: {pid}:{vpn}")
                    references[entry.frame].append(entry)
                elif entry.frame is not None:
                    raise MemoryInvariantError(f"not-present 페이지가 프레임을 가리킵니다: {pid}:{vpn}")
                if entry.cow and entry.writable:
                    raise MemoryInvariantError(f"COW 페이지가 동시에 쓰기 가능입니다: {pid}:{vpn}")
        for frame_id, frame in self.frames.items():
            actual = len(references[frame_id])
            if actual != frame.refcount:
                raise MemoryInvariantError(
                    f"프레임 참조 수가 일치하지 않습니다: frame={frame_id} stored={frame.refcount} actual={actual}"
                )
            if actual == 0:
                raise MemoryInvariantError(f"참조되지 않는 프레임이 남아 있습니다: {frame_id}")
            if actual > 1 and any(entry.writable for entry in references[frame_id]):
                raise MemoryInvariantError(f"공유 프레임이 쓰기 가능으로 노출되었습니다: {frame_id}")

    @classmethod
    def validate_snapshot(cls, snapshot: Mapping[str, Any]) -> None:
        manager = cls(max_frames=max(1, len(snapshot.get("frames", {})) + 1))
        raw_frames = snapshot.get("frames")
        raw_spaces = snapshot.get("spaces")
        if not isinstance(raw_frames, Mapping) or not isinstance(raw_spaces, Mapping):
            raise MemoryInvariantError("memory snapshot 형식이 잘못되었습니다.")
        manager.frames = {}
        for raw_id, raw in raw_frames.items():
            if not isinstance(raw, Mapping):
                raise MemoryInvariantError("frame 항목 형식이 잘못되었습니다.")
            frame_id = int(raw_id)
            manager.frames[frame_id] = Frame(
                value=int(raw.get("value", 0)),
                refcount=int(raw.get("refcount", 0)),
                dirty=bool(raw.get("dirty", False)),
                referenced=bool(raw.get("referenced", False)),
            )
        manager.spaces = {}
        for pid, raw_pages in raw_spaces.items():
            if not isinstance(raw_pages, Mapping):
                raise MemoryInvariantError("address space 항목 형식이 잘못되었습니다.")
            space = AddressSpace(str(pid))
            for raw_vpn, raw in raw_pages.items():
                if not isinstance(raw, Mapping):
                    raise MemoryInvariantError("PTE 항목 형식이 잘못되었습니다.")
                frame = raw.get("frame")
                space.pages[int(raw_vpn)] = PageTableEntry(
                    frame=None if frame is None else int(frame),
                    present=bool(raw.get("present", False)),
                    readable=bool(raw.get("readable", True)),
                    writable=bool(raw.get("writable", False)),
                    cow=bool(raw.get("cow", False)),
                    backing_value=int(raw.get("backing_value", 0)),
                )
            manager.spaces[space.pid] = space
        manager.assert_invariants()

    def _space(self, pid: str) -> AddressSpace:
        try:
            return self.spaces[pid]
        except KeyError as exc:
            raise KeyError(f"주소 공간이 없습니다: {pid}") from exc

    def _entry(self, pid: str, vpn: int) -> PageTableEntry:
        self._validate_vpn(vpn)
        space = self._space(pid)
        try:
            return space.pages[vpn]
        except KeyError as exc:
            raise MemoryFault(FaultKind.NOT_MAPPED, pid, vpn, "가상 페이지가 매핑되지 않았습니다.") from exc

    def _ensure_present(self, pid: str, vpn: int, entry: PageTableEntry) -> None:
        if entry.present:
            return
        try:
            frame_id = self._allocate_frame(entry.backing_value)
        except MemoryError as exc:
            raise MemoryFault(FaultKind.NOT_PRESENT, pid, vpn, "빈 물리 프레임이 없습니다.") from exc
        entry.frame = frame_id
        entry.present = True
        self.assert_invariants()

    def _resolve_cow(self, entry: PageTableEntry) -> None:
        if not entry.present or entry.frame is None or not entry.cow:
            raise MemoryInvariantError("COW 해제 대상이 아닙니다.")
        old_id = entry.frame
        old_frame = self.frames[old_id]
        if old_frame.refcount == 1:
            entry.cow = False
            entry.writable = True
            return
        new_id = self._allocate_frame(old_frame.value)
        self._decref(old_id)
        entry.frame = new_id
        entry.cow = False
        entry.writable = True

    def _allocate_frame(self, value: int) -> int:
        if len(self.frames) >= self.max_frames:
            raise MemoryError("빈 물리 프레임이 없습니다.")
        frame_id = self._next_frame
        self._next_frame += 1
        self.frames[frame_id] = Frame(value=value)
        return frame_id

    def _decref(self, frame_id: int) -> None:
        frame = self.frames[frame_id]
        frame.refcount -= 1
        if frame.refcount < 0:
            raise MemoryInvariantError(f"프레임 참조 수가 음수가 되었습니다: {frame_id}")
        if frame.refcount == 0:
            self.frames.pop(frame_id)

    @staticmethod
    def _validate_vpn(vpn: int) -> None:
        if not isinstance(vpn, int) or vpn < 0:
            raise ValueError(f"VPN은 0 이상의 정수여야 합니다: {vpn!r}")


@dataclass(frozen=True)
class ReplacementResult:
    policy: str
    faults: int
    evictions: tuple[int, ...]
    frames: tuple[int, ...]


def simulate_replacement(references: Iterable[int], capacity: int, policy: str) -> ReplacementResult:
    """FIFO, LRU와 Clock의 페이지 폴트 수를 비교합니다."""

    pages = list(references)
    if capacity <= 0:
        raise ValueError("프레임 수는 양수여야 합니다.")
    if any(not isinstance(page, int) or page < 0 for page in pages):
        raise ValueError("페이지 참조는 0 이상의 정수여야 합니다.")
    normalized = policy.lower()
    if normalized not in {"fifo", "lru", "clock"}:
        raise ValueError(f"지원하지 않는 교체 정책입니다: {policy}")

    if normalized == "fifo":
        frames: list[int] = []
        queue: deque[int] = deque()
        faults = 0
        evictions: list[int] = []
        for page in pages:
            if page in frames:
                continue
            faults += 1
            if len(frames) == capacity:
                victim = queue.popleft()
                frames.remove(victim)
                evictions.append(victim)
            frames.append(page)
            queue.append(page)
        return ReplacementResult(normalized, faults, tuple(evictions), tuple(frames))

    if normalized == "lru":
        frames = []
        last_used: dict[int, int] = {}
        faults = 0
        evictions = []
        for tick, page in enumerate(pages):
            if page not in frames:
                faults += 1
                if len(frames) == capacity:
                    victim = min(frames, key=lambda item: (last_used[item], item))
                    frames.remove(victim)
                    last_used.pop(victim)
                    evictions.append(victim)
                frames.append(page)
            last_used[page] = tick
        return ReplacementResult(normalized, faults, tuple(evictions), tuple(frames))

    frames = []
    referenced: dict[int, bool] = {}
    hand = 0
    faults = 0
    evictions = []
    for page in pages:
        if page in frames:
            referenced[page] = True
            continue
        faults += 1
        if len(frames) < capacity:
            frames.append(page)
            referenced[page] = True
            continue
        while referenced[frames[hand]]:
            referenced[frames[hand]] = False
            hand = (hand + 1) % capacity
        victim = frames[hand]
        evictions.append(victim)
        referenced.pop(victim)
        frames[hand] = page
        referenced[page] = True
        hand = (hand + 1) % capacity
    return ReplacementResult(normalized, faults, tuple(evictions), tuple(frames))
