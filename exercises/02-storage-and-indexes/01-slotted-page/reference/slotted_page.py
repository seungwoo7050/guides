from __future__ import annotations

import struct
from dataclasses import dataclass

# [Implementation 1] Header와 slot binary format을 먼저 고정해 page 안의 두 성장 경계를 계산할 수 있게 한다.
HEADER = struct.Struct("!4sHH")
SLOT = struct.Struct("!HHB3x")
MAGIC = b"SLPG"


class PageFullError(RuntimeError):
    pass


# [Implementation 2] Slot은 안정적인 논리 ID의 상태이고 SlottedPage가 bytes와 free boundary를 소유한다.
@dataclass
class Slot:
    offset: int
    length: int
    alive: bool = True


class SlottedPage:
    def __init__(self, page_size: int = 256) -> None:
        if page_size < HEADER.size + SLOT.size + 1:
            raise ValueError("page_size is too small")
        if page_size > 65535:
            raise ValueError("page_size exceeds on-page offset format")
        self.page_size = page_size
        self._data = bytearray(page_size)
        self._slots: list[Slot] = []
        self._free_end = page_size

    @property
    def free_space(self) -> int:
        return self._free_end - (HEADER.size + len(self._slots) * SLOT.size)

    # [Implementation 3] Payload와 live slot lookup을 mutation 전에 검증해 실패가 page를 바꾸지 않게 한다.
    def _validate_payload(self, payload: bytes) -> bytes:
        if not isinstance(payload, bytes):
            raise TypeError("payload must be bytes")
        if not payload:
            raise ValueError("empty records are not supported")
        if len(payload) > 65535:
            raise ValueError("record is too large")
        return payload

    def _slot(self, slot_id: int) -> Slot:
        try:
            slot = self._slots[slot_id]
        except (IndexError, TypeError) as exc:
            raise KeyError(slot_id) from exc
        if not slot.alive:
            raise KeyError(slot_id)
        return slot

    # [Implementation 4] 수용 가능성을 먼저 계산한 뒤 compact하고 tombstone slot을 안정적으로 재사용한다.
    def insert(self, payload: bytes) -> int:
        payload = self._validate_payload(payload)
        reusable = next((index for index, slot in enumerate(self._slots) if not slot.alive), None)
        directory_cost = 0 if reusable is not None else SLOT.size

        # 실패 전에 전체 live bytes를 기준으로 수용 가능성을 계산한다. 공간이
        # 절대 부족한 경우 compact조차 수행하지 않아 page bytes를 보존한다.
        live_bytes = sum(slot.length for slot in self._slots if slot.alive)
        required = HEADER.size + len(self._slots) * SLOT.size + directory_cost + live_bytes + len(payload)
        if required > self.page_size:
            raise PageFullError("record does not fit in page")
        if len(payload) + directory_cost > self.free_space:
            self.compact()

        self._free_end -= len(payload)
        self._data[self._free_end : self._free_end + len(payload)] = payload
        new_slot = Slot(self._free_end, len(payload), True)
        if reusable is None:
            self._slots.append(new_slot)
            return len(self._slots) - 1
        self._slots[reusable] = new_slot
        return reusable

    # [Implementation 5] Read/delete/update/compact는 slot ID를 유지하며 record bytes의 위치만 다시 소유한다.
    def read(self, slot_id: int) -> bytes:
        slot = self._slot(slot_id)
        return bytes(self._data[slot.offset : slot.offset + slot.length])

    def delete(self, slot_id: int) -> None:
        slot = self._slot(slot_id)
        slot.alive = False
        slot.length = 0
        slot.offset = 0

    def update(self, slot_id: int, payload: bytes) -> None:
        payload = self._validate_payload(payload)
        slot = self._slot(slot_id)
        if len(payload) <= slot.length:
            self._data[slot.offset : slot.offset + len(payload)] = payload
            slot.length = len(payload)
            return

        live_bytes = sum(item.length for item in self._slots if item.alive)
        required = HEADER.size + len(self._slots) * SLOT.size + live_bytes - slot.length + len(payload)
        if required > self.page_size:
            raise PageFullError("update would overflow page")

        records: list[bytes | None] = [self.read(i) if item.alive else None for i, item in enumerate(self._slots)]
        records[slot_id] = payload
        self._rebuild(records)

    def compact(self) -> None:
        records: list[bytes | None] = [self.read(i) if item.alive else None for i, item in enumerate(self._slots)]
        self._rebuild(records)

    def _rebuild(self, records: list[bytes | None]) -> None:
        self._data = bytearray(self.page_size)
        self._free_end = self.page_size
        rebuilt: list[Slot] = []
        for payload in records:
            if payload is None:
                rebuilt.append(Slot(0, 0, False))
                continue
            self._free_end -= len(payload)
            self._data[self._free_end : self._free_end + len(payload)] = payload
            rebuilt.append(Slot(self._free_end, len(payload), True))
        self._slots = rebuilt

    # [Implementation 6] Serialize가 memory state를 고정된 header·directory·record layout으로 내린다.
    def serialize(self) -> bytes:
        raw = bytearray(self._data)
        HEADER.pack_into(raw, 0, MAGIC, len(self._slots), self._free_end)
        for index, slot in enumerate(self._slots):
            SLOT.pack_into(raw, HEADER.size + index * SLOT.size, slot.offset, slot.length, int(slot.alive))
        return bytes(raw)

    # [Implementation 7] 외부 bytes는 boundary와 각 live slot 범위를 모두 검증한 뒤에만 page가 된다.
    @classmethod
    def from_bytes(cls, raw: bytes) -> "SlottedPage":
        if len(raw) < HEADER.size:
            raise ValueError("truncated page")
        magic, slot_count, free_end = HEADER.unpack_from(raw, 0)
        if magic != MAGIC:
            raise ValueError("invalid page magic")
        if HEADER.size + slot_count * SLOT.size > free_end or free_end > len(raw):
            raise ValueError("corrupt page boundaries")

        page = cls(len(raw))
        page._data[:] = raw
        page._free_end = free_end
        for index in range(slot_count):
            offset, length, alive = SLOT.unpack_from(raw, HEADER.size + index * SLOT.size)
            if alive and (offset < free_end or offset + length > len(raw)):
                raise ValueError("corrupt slot")
            page._slots.append(Slot(offset, length, bool(alive)))
        return page
