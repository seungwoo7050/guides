from __future__ import annotations

from dataclasses import dataclass, field


class BufferPoolFull(RuntimeError):
    pass


# [Implementation 1] DiskManager가 durable page bytes와 물리 I/O 관찰 counter를 소유한다.
class DiskManager:
    def __init__(self, page_size: int = 64) -> None:
        if page_size <= 0:
            raise ValueError("page_size must be positive")
        self.page_size = page_size
        self.pages: dict[int, bytes] = {}
        self.read_count = 0
        self.write_count = 0
        self._next_page_id = 0

    def allocate(self, initial: bytes = b"") -> int:
        if len(initial) > self.page_size:
            raise ValueError("initial page is too large")
        page_id = self._next_page_id
        self._next_page_id += 1
        self.pages[page_id] = initial.ljust(self.page_size, b"\x00")
        return page_id

    def read(self, page_id: int) -> bytes:
        if page_id not in self.pages:
            raise KeyError(page_id)
        self.read_count += 1
        return self.pages[page_id]

    def write(self, page_id: int, data: bytes) -> None:
        if page_id not in self.pages:
            raise KeyError(page_id)
        if len(data) != self.page_size:
            raise ValueError("page write must match page_size")
        self.write_count += 1
        self.pages[page_id] = bytes(data)


# [Implementation 2] Frame 상태와 BufferPool의 page table·Clock hand가 residency의 단일 source of truth다.
@dataclass
class Frame:
    page_id: int | None = None
    data: bytearray = field(default_factory=bytearray)
    pin_count: int = 0
    dirty: bool = False
    referenced: bool = False


class BufferPool:
    def __init__(self, disk: DiskManager, capacity: int) -> None:
        if capacity <= 0:
            raise ValueError("capacity must be positive")
        self.disk = disk
        self.frames = [Frame(data=bytearray(disk.page_size)) for _ in range(capacity)]
        self.page_table: dict[int, int] = {}
        self.hand = 0

    # [Implementation 3] Fetch는 hit의 pin을 늘리거나 dirty victim을 먼저 기록한 뒤 mapping을 교체한다.
    def fetch(self, page_id: int) -> bytearray:
        resident = self.page_table.get(page_id)
        if resident is not None:
            frame = self.frames[resident]
            frame.pin_count += 1
            frame.referenced = True
            return frame.data

        frame_index = self._choose_victim()
        frame = self.frames[frame_index]
        if frame.page_id is not None:
            if frame.dirty:
                self.disk.write(frame.page_id, bytes(frame.data))
            del self.page_table[frame.page_id]

        frame.page_id = page_id
        frame.data[:] = self.disk.read(page_id)
        frame.pin_count = 1
        frame.dirty = False
        frame.referenced = True
        self.page_table[page_id] = frame_index
        return frame.data

    # [Implementation 4] 빈 frame을 우선하고 Clock 순회에서는 pin을 제외한 referenced frame에 한 번 양보한다.
    def _choose_victim(self) -> int:
        for index, frame in enumerate(self.frames):
            if frame.page_id is None:
                self.hand = (index + 1) % len(self.frames)
                return index

        inspected = 0
        limit = len(self.frames) * 2
        while inspected < limit:
            index = self.hand
            frame = self.frames[index]
            self.hand = (self.hand + 1) % len(self.frames)
            inspected += 1
            if frame.pin_count > 0:
                continue
            if frame.referenced:
                frame.referenced = False
                continue
            return index
        raise BufferPoolFull("all frames are pinned or recently referenced")

    # [Implementation 5] Unpin만 pin ownership을 반환하며 dirty 상태는 한번 켜지면 flush까지 유지된다.
    def unpin(self, page_id: int, *, dirty: bool = False) -> None:
        try:
            frame = self.frames[self.page_table[page_id]]
        except KeyError as exc:
            raise KeyError(page_id) from exc
        if frame.pin_count == 0:
            raise RuntimeError("page is already unpinned")
        frame.pin_count -= 1
        frame.dirty = frame.dirty or dirty

    # [Implementation 6] Flush가 dirty bytes를 disk boundary로 내리고 성공 뒤에만 flag를 지운다.
    def flush(self, page_id: int) -> None:
        try:
            frame = self.frames[self.page_table[page_id]]
        except KeyError as exc:
            raise KeyError(page_id) from exc
        if frame.dirty:
            self.disk.write(page_id, bytes(frame.data))
            frame.dirty = False

    def flush_all(self) -> None:
        for page_id in list(self.page_table):
            self.flush(page_id)
