from __future__ import annotations

import struct
from bisect import bisect_left
from dataclasses import dataclass, field, replace
from typing import Literal

PAGE_HEADER = struct.Struct("!4sQHH")
PAGE_SLOT = struct.Struct("!HH")
RECORD_HEADER = struct.Struct("!qI")
PAGE_MAGIC = b"MSTG"


class WALViolation(RuntimeError):
    pass


class DuplicateKeyError(RuntimeError):
    pass


class PageFull(RuntimeError):
    pass


class SlottedPage:
    def __init__(self, page_id: int, size: int) -> None:
        self.page_id = page_id
        self.size = size
        self.page_lsn = 0
        self._data = bytearray(size)
        self._slots: list[tuple[int, int]] = []
        self._free_end = size

    @property
    def free_space(self) -> int:
        return self._free_end - (PAGE_HEADER.size + len(self._slots) * PAGE_SLOT.size)

    def insert(self, key: int, value: bytes) -> int:
        if not isinstance(key, int):
            raise TypeError("key must be int")
        if not isinstance(value, bytes) or not value:
            raise ValueError("value must be non-empty bytes")
        record = RECORD_HEADER.pack(key, len(value)) + value
        if len(record) + PAGE_SLOT.size > self.free_space:
            raise PageFull("record does not fit")
        self._free_end -= len(record)
        self._data[self._free_end : self._free_end + len(record)] = record
        self._slots.append((self._free_end, len(record)))
        return len(self._slots) - 1

    def read(self, slot_id: int) -> tuple[int, bytes]:
        try:
            offset, length = self._slots[slot_id]
        except (IndexError, TypeError) as exc:
            raise KeyError(slot_id) from exc
        record = memoryview(self._data)[offset : offset + length]
        key, value_length = RECORD_HEADER.unpack_from(record, 0)
        value = bytes(record[RECORD_HEADER.size :])
        if len(value) != value_length:
            raise ValueError("corrupt record")
        return key, value

    def find_key(self, key: int) -> int | None:
        for slot_id in range(len(self._slots)):
            stored_key, _ = self.read(slot_id)
            if stored_key == key:
                return slot_id
        return None

    def records(self) -> list[tuple[int, int, bytes]]:
        return [(slot_id, *self.read(slot_id)) for slot_id in range(len(self._slots))]

    def serialize(self) -> bytes:
        raw = bytearray(self._data)
        PAGE_HEADER.pack_into(raw, 0, PAGE_MAGIC, self.page_lsn, len(self._slots), self._free_end)
        for index, (offset, length) in enumerate(self._slots):
            PAGE_SLOT.pack_into(raw, PAGE_HEADER.size + index * PAGE_SLOT.size, offset, length)
        return bytes(raw)

    @classmethod
    def from_bytes(cls, page_id: int, raw: bytes) -> "SlottedPage":
        magic, page_lsn, slot_count, free_end = PAGE_HEADER.unpack_from(raw, 0)
        if magic != PAGE_MAGIC:
            raise ValueError("invalid page magic")
        if PAGE_HEADER.size + slot_count * PAGE_SLOT.size > free_end or free_end > len(raw):
            raise ValueError("corrupt page boundaries")
        page = cls(page_id, len(raw))
        page._data[:] = raw
        page.page_lsn = page_lsn
        page._free_end = free_end
        for index in range(slot_count):
            offset, length = PAGE_SLOT.unpack_from(raw, PAGE_HEADER.size + index * PAGE_SLOT.size)
            if offset < free_end or offset + length > len(raw):
                raise ValueError("corrupt slot")
            page._slots.append((offset, length))
        return page


class DiskManager:
    def __init__(self, page_size: int = 256) -> None:
        if page_size < 96:
            raise ValueError("page_size must be at least 96")
        self.page_size = page_size
        self.pages: dict[int, bytes] = {}
        self._next_page_id = 0
        self.write_events: list[tuple[int, int]] = []

    def allocate(self) -> int:
        page_id = self._next_page_id
        self._next_page_id += 1
        self.pages[page_id] = SlottedPage(page_id, self.page_size).serialize()
        return page_id

    def read(self, page_id: int) -> SlottedPage:
        try:
            raw = self.pages[page_id]
        except KeyError as exc:
            raise KeyError(page_id) from exc
        return SlottedPage.from_bytes(page_id, raw)

    def write(self, page: SlottedPage) -> None:
        if page.page_id not in self.pages:
            raise KeyError(page.page_id)
        self.pages[page.page_id] = page.serialize()
        self.write_events.append((page.page_id, page.page_lsn))

    @property
    def page_ids(self) -> list[int]:
        return sorted(self.pages)


@dataclass(frozen=True)
class LogRecord:
    lsn: int
    txid: int
    kind: Literal["INSERT", "COMMIT"]
    page_id: int | None = None
    key: int | None = None
    value: bytes | None = None


class LogManager:
    def __init__(self, records: list[LogRecord] | None = None, flushed_lsn: int = 0) -> None:
        self.records = list(records or [])
        self.next_lsn = max((record.lsn for record in self.records), default=0) + 1
        self.flushed_lsn = flushed_lsn
        self.flush_events: list[int] = []

    def _append(self, record: LogRecord) -> int:
        self.records.append(record)
        self.next_lsn += 1
        return record.lsn

    def insert(self, txid: int, page_id: int, key: int, value: bytes) -> int:
        return self._append(LogRecord(self.next_lsn, txid, "INSERT", page_id, key, value))

    def commit(self, txid: int) -> int:
        return self._append(LogRecord(self.next_lsn, txid, "COMMIT"))

    def flush(self, lsn: int) -> None:
        if lsn >= self.next_lsn:
            raise ValueError("unknown LSN")
        if lsn < self.flushed_lsn:
            raise ValueError("cannot move durable boundary backwards")
        self.flushed_lsn = lsn
        self.flush_events.append(lsn)

    def durable_records(self) -> list[LogRecord]:
        return [record for record in self.records if record.lsn <= self.flushed_lsn]


@dataclass
class Frame:
    page: SlottedPage | None = None
    pin_count: int = 0
    dirty: bool = False
    referenced: bool = False


class BufferPool:
    def __init__(self, disk: DiskManager, log: LogManager, capacity: int = 2) -> None:
        if capacity <= 0:
            raise ValueError("capacity must be positive")
        self.disk = disk
        self.log = log
        self.frames = [Frame() for _ in range(capacity)]
        self.page_table: dict[int, int] = {}
        self.hand = 0

    def fetch(self, page_id: int) -> SlottedPage:
        if page_id in self.page_table:
            frame = self.frames[self.page_table[page_id]]
            frame.pin_count += 1
            frame.referenced = True
            assert frame.page is not None
            return frame.page
        index = self._victim()
        frame = self.frames[index]
        if frame.page is not None:
            self._flush_frame(frame)
            del self.page_table[frame.page.page_id]
        frame.page = self.disk.read(page_id)
        frame.pin_count = 1
        frame.dirty = False
        frame.referenced = True
        self.page_table[page_id] = index
        return frame.page

    def _victim(self) -> int:
        for index, frame in enumerate(self.frames):
            if frame.page is None:
                self.hand = (index + 1) % len(self.frames)
                return index
        for _ in range(len(self.frames) * 2 + 1):
            index = self.hand
            frame = self.frames[index]
            self.hand = (self.hand + 1) % len(self.frames)
            if frame.pin_count:
                continue
            if frame.referenced:
                frame.referenced = False
                continue
            return index
        raise RuntimeError("all buffer frames are pinned")

    def unpin(self, page_id: int, *, dirty: bool = False) -> None:
        frame = self.frames[self.page_table[page_id]]
        if frame.pin_count == 0:
            raise RuntimeError("double unpin")
        frame.pin_count -= 1
        frame.dirty = frame.dirty or dirty

    def _flush_frame(self, frame: Frame) -> None:
        if frame.page is None or not frame.dirty:
            return
        if frame.page.page_lsn > self.log.flushed_lsn:
            raise WALViolation("data page reached disk before its WAL record")
        self.disk.write(frame.page)
        frame.dirty = False

    def flush(self, page_id: int) -> None:
        self._flush_frame(self.frames[self.page_table[page_id]])

    def flush_all(self) -> None:
        for frame in self.frames:
            self._flush_frame(frame)


class BPlusTreeIndex:
    """Capstone용 ordered index. leaf split과 range scan 계약만 유지한다."""

    def __init__(self, leaf_capacity: int = 4) -> None:
        self.leaf_capacity = leaf_capacity
        self.leaves: list[list[tuple[int, tuple[int, int]]]] = [[]]

    def insert(self, key: int, rid: tuple[int, int]) -> None:
        leaf_index = self._leaf_index(key)
        leaf = self.leaves[leaf_index]
        keys = [item[0] for item in leaf]
        position = bisect_left(keys, key)
        if position < len(leaf) and leaf[position][0] == key:
            raise DuplicateKeyError(key)
        leaf.insert(position, (key, rid))
        if len(leaf) > self.leaf_capacity:
            split = len(leaf) // 2
            self.leaves.insert(leaf_index + 1, leaf[split:])
            del leaf[split:]

    def _leaf_index(self, key: int) -> int:
        for index, leaf in enumerate(self.leaves):
            if not leaf or key <= leaf[-1][0]:
                return index
        return len(self.leaves) - 1

    def get(self, key: int) -> tuple[int, int]:
        leaf = self.leaves[self._leaf_index(key)]
        position = bisect_left([item[0] for item in leaf], key)
        if position == len(leaf) or leaf[position][0] != key:
            raise KeyError(key)
        return leaf[position][1]

    def range(self, start: int, end: int) -> list[tuple[int, tuple[int, int]]]:
        return [item for leaf in self.leaves for item in leaf if start <= item[0] <= end]


class MiniStorageEngine:
    def __init__(
        self,
        disk: DiskManager | None = None,
        log: LogManager | None = None,
        *,
        buffer_capacity: int = 2,
    ) -> None:
        self.disk = disk or DiskManager()
        self.log = log or LogManager()
        self.buffer = BufferPool(self.disk, self.log, buffer_capacity)
        self.index = BPlusTreeIndex()
        self._next_txid = 1
        if not self.disk.page_ids:
            self.disk.allocate()
        self._rebuild_index()

    def _rebuild_index(self) -> None:
        self.index = BPlusTreeIndex()
        for page_id in self.disk.page_ids:
            page = self.disk.read(page_id)
            for slot_id, key, _ in page.records():
                self.index.insert(key, (page_id, slot_id))

    def _choose_page(self, value: bytes) -> int:
        needed = RECORD_HEADER.size + len(value) + PAGE_SLOT.size
        for page_id in self.disk.page_ids:
            page = self.buffer.fetch(page_id)
            fits = page.free_space >= needed
            self.buffer.unpin(page_id)
            if fits:
                return page_id
        return self.disk.allocate()

    def insert(self, key: int, value: bytes) -> None:
        try:
            self.index.get(key)
        except KeyError:
            pass
        else:
            raise DuplicateKeyError(key)

        page_id = self._choose_page(value)
        txid = self._next_txid
        self._next_txid += 1
        insert_lsn = self.log.insert(txid, page_id, key, value)
        page = self.buffer.fetch(page_id)
        try:
            slot_id = page.insert(key, value)
            page.page_lsn = insert_lsn
        finally:
            self.buffer.unpin(page_id, dirty=True)
        commit_lsn = self.log.commit(txid)
        self.log.flush(commit_lsn)
        self.index.insert(key, (page_id, slot_id))

    def get(self, key: int) -> bytes:
        page_id, slot_id = self.index.get(key)
        page = self.buffer.fetch(page_id)
        try:
            stored_key, value = page.read(slot_id)
            if stored_key != key:
                raise RuntimeError("index points to a different key")
            return value
        finally:
            self.buffer.unpin(page_id)

    def range(self, start: int, end: int) -> list[tuple[int, bytes]]:
        return [(key, self.get(key)) for key, _ in self.index.range(start, end)]

    def checkpoint(self) -> None:
        self.buffer.flush_all()

    @classmethod
    def recover(
        cls,
        disk: DiskManager,
        durable_records: list[LogRecord],
        *,
        buffer_capacity: int = 2,
    ) -> "MiniStorageEngine":
        durable_lsn = max((record.lsn for record in durable_records), default=0)
        log = LogManager(durable_records, durable_lsn)
        committed = {record.txid for record in durable_records if record.kind == "COMMIT"}

        # 이 축소 엔진은 WAL을 heap의 source of truth로 유지하며 truncate하지 않는다.
        # 따라서 recovery는 durable committed INSERT만으로 page들을 다시 만들어
        # disk까지 도달한 미완료 transaction의 effect도 제거한다.
        page_ids = set(disk.page_ids)
        page_ids.update(
            record.page_id
            for record in durable_records
            if record.kind == "INSERT" and record.page_id is not None
        )
        if not page_ids:
            page_ids.add(0)
        disk.pages = {
            page_id: SlottedPage(page_id, disk.page_size).serialize()
            for page_id in sorted(page_ids)
        }
        disk._next_page_id = max(page_ids) + 1

        engine = cls(disk, log, buffer_capacity=buffer_capacity)
        # Recovery 뒤 txid를 1부터 다시 쓰면 과거 COMMIT이 새 미완료 INSERT를
        # committed로 오인하게 만든다. Durable WAL의 namespace 다음부터 재개한다.
        engine._next_txid = max((record.txid for record in durable_records), default=0) + 1

        for record in durable_records:
            if record.kind != "INSERT" or record.txid not in committed:
                continue
            assert record.page_id is not None and record.key is not None and record.value is not None
            page = engine.buffer.fetch(record.page_id)
            try:
                if page.find_key(record.key) is None:
                    page.insert(record.key, record.value)
                    page.page_lsn = max(page.page_lsn, record.lsn)
                    dirty = True
                else:
                    dirty = False
            finally:
                engine.buffer.unpin(record.page_id, dirty=dirty)

        engine.buffer.flush_all()
        engine._rebuild_index()
        return engine
