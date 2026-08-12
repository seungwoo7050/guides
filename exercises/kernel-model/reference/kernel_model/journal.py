"""commit 기록을 경계로 재실행 가능한 저널을 모델링합니다."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Iterable, Mapping


class JournalError(ValueError):
    """저널 순서나 트랜잭션 상태가 잘못되었을 때 발생합니다."""


# [Implementation 7] JournalRecord와 Journal은 append-only log의 transaction state와 다음 txid를 소유합니다.
@dataclass(frozen=True, slots=True)
class JournalRecord:
    txid: int
    kind: str
    payload: dict[str, Any] = field(default_factory=dict)


@dataclass
class Journal:
    records: list[JournalRecord] = field(default_factory=list)
    _next_txid: int = 1

    # [Implementation 7-1] begin이 단조 증가 txid를 발급해 이후 operation과 commit의 수명 경계를 엽니다.
    def begin(self) -> int:
        txid = self._next_txid
        self._next_txid += 1
        self.records.append(JournalRecord(txid, "begin"))
        return txid

    # [Implementation 7-2] operation은 열린 transaction에만 append하고 commit 이후 log mutation을 거부합니다.
    def append(self, txid: int, operation: Mapping[str, Any]) -> None:
        state = self._state(txid)
        if state != "open":
            raise JournalError(f"열린 트랜잭션에만 연산을 추가할 수 있습니다: txid={txid}")
        if "op" not in operation:
            raise JournalError("저널 연산에는 op가 필요합니다.")
        self.records.append(JournalRecord(txid, "operation", dict(operation)))

    def commit(self, txid: int) -> None:
        if self._state(txid) != "open":
            raise JournalError(f"열린 트랜잭션만 commit할 수 있습니다: txid={txid}")
        self.records.append(JournalRecord(txid, "commit"))

    # [Implementation 7-3] recovery는 committed transaction만 txid 순서로 replay하고 applied set이 중복 적용 책임을 소유합니다.
    def recover(
        self,
        apply_operation: Callable[[Mapping[str, Any]], None],
        *,
        already_applied: set[int] | None = None,
    ) -> list[int]:
        """commit된 트랜잭션만 txid 순서로 재생합니다."""

        self.validate()
        applied = already_applied if already_applied is not None else set()
        operations: dict[int, list[dict[str, Any]]] = {}
        committed: set[int] = set()
        for record in self.records:
            if record.kind == "operation":
                operations.setdefault(record.txid, []).append(dict(record.payload))
            elif record.kind == "commit":
                committed.add(record.txid)

        recovered: list[int] = []
        for txid in sorted(committed):
            if txid in applied:
                continue
            for operation in operations.get(txid, []):
                apply_operation(operation)
            applied.add(txid)
            recovered.append(txid)
        return recovered

    # [Implementation 7-4] BEGIN → OPERATION* → COMMIT 순서를 검증한 뒤 snapshot reconstruction에도 같은 log 계약을 적용합니다.
    def validate(self) -> None:
        states: dict[int, str] = {}
        for record in self.records:
            if record.txid <= 0:
                raise JournalError("txid는 양수여야 합니다.")
            if record.kind == "begin":
                if record.txid in states:
                    raise JournalError(f"begin이 중복되었습니다: txid={record.txid}")
                states[record.txid] = "open"
            elif record.kind == "operation":
                if states.get(record.txid) != "open":
                    raise JournalError(f"열리지 않은 트랜잭션의 연산입니다: txid={record.txid}")
                if "op" not in record.payload:
                    raise JournalError(f"op가 없는 연산입니다: txid={record.txid}")
            elif record.kind == "commit":
                if states.get(record.txid) != "open":
                    raise JournalError(f"commit 순서가 잘못되었습니다: txid={record.txid}")
                states[record.txid] = "committed"
            else:
                raise JournalError(f"알 수 없는 저널 레코드입니다: {record.kind}")

    def snapshot(self) -> list[dict[str, Any]]:
        return [
            {"txid": record.txid, "kind": record.kind, "payload": dict(record.payload)}
            for record in self.records
        ]

    @classmethod
    def from_snapshot(cls, records: Iterable[Mapping[str, Any]]) -> "Journal":
        journal = cls()
        journal.records = []
        maximum = 0
        for raw in records:
            record = JournalRecord(
                txid=int(raw["txid"]),
                kind=str(raw["kind"]),
                payload=dict(raw.get("payload", {})),
            )
            journal.records.append(record)
            maximum = max(maximum, record.txid)
        journal._next_txid = maximum + 1
        journal.validate()
        return journal

    def _state(self, txid: int) -> str | None:
        state: str | None = None
        for record in self.records:
            if record.txid != txid:
                continue
            if record.kind == "begin":
                state = "open"
            elif record.kind == "commit":
                state = "committed"
        return state
