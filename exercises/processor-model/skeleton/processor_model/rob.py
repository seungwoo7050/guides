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
        raise NotImplementedError("TODO: 명령을 빈 재정렬 버퍼 항목에 배치하세요.")

    def complete(
        self, tag: int, *, value: int | None = None, fault: str | None = None
    ) -> None:
        raise NotImplementedError("TODO: tag에 완료 값 또는 예외를 기록하세요.")

    def retire(
        self, registers: MutableMapping[str, int], limit: int | None = None
    ) -> list[int]:
        raise NotImplementedError("TODO: 준비된 명령을 프로그램 순서대로 반영하세요.")

    def pending_tags(self) -> list[int]:
        return [entry.tag for entry in self._entries]
