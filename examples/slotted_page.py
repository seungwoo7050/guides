#!/usr/bin/env python3
"""가변 길이 record, compaction과 안정적인 slot ID를 관찰한다."""

from __future__ import annotations

from dataclasses import dataclass

# [Implementation 1] Slot directory의 고정 비용과 record 위치를 page 상태의 공통 어휘로 먼저 둔다.
SLOT_BYTES = 4


@dataclass
class Slot:
    offset: int
    length: int
    alive: bool = True


# [Implementation 2] Page가 byte area, free boundary와 slot 수명을 함께 소유한다.
class SlottedPage:
    def __init__(self, size: int = 96) -> None:
        self.data = bytearray(size)
        self.free_end = size
        self.slots: list[Slot] = []

    @property
    def contiguous_free_space(self) -> int:
        return self.free_end - len(self.slots) * SLOT_BYTES

    @property
    def total_free_space(self) -> int:
        live_bytes = sum(slot.length for slot in self.slots if slot.alive)
        return len(self.data) - live_bytes - len(self.slots) * SLOT_BYTES

    # [Implementation 3] 전체 공간과 연속 공간을 구분하고 필요할 때만 compact한 뒤 bytes를 쓴다.
    def insert(self, payload: bytes) -> int:
        if not payload:
            raise ValueError("empty record")
        required = len(payload) + SLOT_BYTES
        if required > self.total_free_space:
            raise OverflowError("page full")
        if required > self.contiguous_free_space:
            self.compact()

        self.free_end -= len(payload)
        self.data[self.free_end : self.free_end + len(payload)] = payload
        self.slots.append(Slot(self.free_end, len(payload)))
        return len(self.slots) - 1

    # [Implementation 4] Read/delete/compact는 record 위치가 바뀌어도 외부 slot ID를 유지한다.
    def read(self, slot_id: int) -> bytes:
        slot = self.slots[slot_id]
        if not slot.alive:
            raise KeyError(slot_id)
        return bytes(self.data[slot.offset : slot.offset + slot.length])

    def delete(self, slot_id: int) -> None:
        slot = self.slots[slot_id]
        if not slot.alive:
            raise KeyError(slot_id)
        slot.alive = False

    def compact(self) -> None:
        records = [self.read(index) if slot.alive else None for index, slot in enumerate(self.slots)]
        self.data = bytearray(len(self.data))
        self.free_end = len(self.data)
        for slot, payload in zip(self.slots, records, strict=True):
            if payload is None:
                continue
            self.free_end -= len(payload)
            self.data[self.free_end : self.free_end + len(payload)] = payload
            slot.offset = self.free_end


# [Implementation 5] 삭제로 생긴 조각을 회수한 뒤에도 기존 live slot이 같은 payload를 가리키는지 본다.
page = SlottedPage()
first = page.insert(b"alpha" * 4)
second = page.insert(b"a variable record" * 2)
page.delete(first)
before = page.read(second)
third = page.insert(b"after compaction" * 2)
assert second == 1 and third == 2
assert page.read(second) == before
print("slotted page example: PASS")
