"""작은 재정렬 버퍼로 순차 완료와 정확한 예외를 재현합니다."""

from __future__ import annotations

from dataclasses import dataclass
from typing import MutableMapping


@dataclass
class Entry:
    tag: int
    destination: str | None
    ready: bool = False
    value: int | None = None
    fault: str | None = None


class PreciseException(RuntimeError):
    def __init__(self, tag: int, reason: str) -> None:
        super().__init__(f"{tag}번 명령에서 예외가 발생했습니다: {reason}")
        self.tag = tag
        self.reason = reason


class ReorderBuffer:
    """명령은 순서와 무관하게 완료하되 맨 앞에서만 상태를 반영합니다."""

    def __init__(self, capacity: int) -> None:
        if (
            not isinstance(capacity, int)
            or isinstance(capacity, bool)
            or capacity <= 0
        ):
            raise ValueError("capacity는 양의 정수여야 합니다.")
        self.capacity = capacity
        self._next_tag = 0
        self._entries: list[Entry] = []

    def issue(self, destination: str | None) -> int:
        if destination is not None and (
            not isinstance(destination, str) or not destination
        ):
            raise ValueError("destination은 비어 있지 않은 문자열 또는 None이어야 합니다.")
        if len(self._entries) >= self.capacity:
            raise BufferError("재정렬 버퍼가 가득 찼습니다.")
        tag = self._next_tag
        self._next_tag += 1
        self._entries.append(Entry(tag, destination))
        return tag

    def complete(
        self, tag: int, *, value: int | None = None, fault: str | None = None
    ) -> None:
        if fault is not None and (not isinstance(fault, str) or not fault):
            raise ValueError("fault는 비어 있지 않은 문자열이어야 합니다.")
        if fault is not None and value is not None:
            raise ValueError("완료 값과 예외는 함께 기록할 수 없습니다.")
        entry = next((item for item in self._entries if item.tag == tag), None)
        if entry is None:
            raise KeyError(f"대기 중인 tag가 아닙니다: {tag}")
        if entry.ready:
            raise ValueError(f"이미 완료한 tag입니다: {tag}")
        if entry.destination is not None and value is None and fault is None:
            raise ValueError("레지스터 쓰기 명령에는 완료 값이 필요합니다.")
        entry.ready = True
        entry.value = value
        entry.fault = fault

    def retire(
        self, registers: MutableMapping[str, int], limit: int | None = None
    ) -> list[int]:
        if limit is not None and (
            not isinstance(limit, int) or isinstance(limit, bool) or limit < 0
        ):
            raise ValueError("limit은 0 이상의 정수여야 합니다.")
        retired: list[int] = []
        while self._entries and self._entries[0].ready:
            if limit is not None and len(retired) >= limit:
                break
            entry = self._entries.pop(0)
            if entry.fault is not None:
                self._entries.clear()
                raise PreciseException(entry.tag, entry.fault)
            if entry.destination is not None:
                assert entry.value is not None
                registers[entry.destination] = entry.value
            retired.append(entry.tag)
        return retired

    def pending_tags(self) -> list[int]:
        return [entry.tag for entry in self._entries]
