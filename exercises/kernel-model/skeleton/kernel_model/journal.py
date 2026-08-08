"""저널 복구의 학습자 구현 골격입니다."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Iterable, Mapping


class JournalError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class JournalRecord:
    txid: int
    kind: str
    payload: dict[str, Any] = field(default_factory=dict)


@dataclass
class Journal:
    records: list[JournalRecord] = field(default_factory=list)
    _next_txid: int = 1

    def begin(self) -> int:
        raise NotImplementedError("새 txid와 begin 레코드를 만드세요.")

    def append(self, txid: int, operation: Mapping[str, Any]) -> None:
        raise NotImplementedError("열린 트랜잭션에만 연산을 추가하세요.")

    def commit(self, txid: int) -> None:
        raise NotImplementedError("열린 트랜잭션에 commit 레코드를 추가하세요.")

    def recover(
        self,
        apply_operation: Callable[[Mapping[str, Any]], None],
        *,
        already_applied: set[int] | None = None,
    ) -> list[int]:
        raise NotImplementedError("commit된 트랜잭션만 한 번씩 재생하세요.")

    def validate(self) -> None:
        raise NotImplementedError("begin-operation-commit 순서를 검사하세요.")

    def snapshot(self) -> list[dict[str, Any]]:
        return [
            {"txid": record.txid, "kind": record.kind, "payload": dict(record.payload)}
            for record in self.records
        ]

    @classmethod
    def from_snapshot(cls, records: Iterable[Mapping[str, Any]]) -> "Journal":
        raise NotImplementedError("snapshot을 JournalRecord 목록으로 복원하세요.")
