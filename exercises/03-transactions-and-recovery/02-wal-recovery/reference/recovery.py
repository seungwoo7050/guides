from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Literal


class WALViolation(RuntimeError):
    pass


# [Implementation 1] Page LSN과 immutable LogRecord가 data state와 history position을 분리한다.
@dataclass
class Page:
    value: int = 0
    page_lsn: int = 0


@dataclass(frozen=True)
class LogRecord:
    lsn: int
    txid: int
    kind: Literal["UPDATE", "COMMIT"]
    page_id: int | None = None
    before: int | None = None
    after: int | None = None


# [Implementation 2] LogManager가 증가하는 LSN namespace와 뒤로 갈 수 없는 durable boundary를 소유한다.
class LogManager:
    def __init__(self) -> None:
        self.records: list[LogRecord] = []
        self.next_lsn = 1
        self.flushed_lsn = 0

    def _append(self, record: LogRecord) -> int:
        self.records.append(record)
        self.next_lsn += 1
        return record.lsn

    def update(self, txid: int, page_id: int, before: int, after: int) -> int:
        return self._append(LogRecord(self.next_lsn, txid, "UPDATE", page_id, before, after))

    def commit(self, txid: int) -> int:
        return self._append(LogRecord(self.next_lsn, txid, "COMMIT"))

    def flush(self, lsn: int) -> None:
        if lsn < self.flushed_lsn or lsn >= self.next_lsn:
            raise ValueError("cannot flush unknown or older LSN")
        self.flushed_lsn = lsn


# [Implementation 3] Disk write는 page LSN까지 WAL이 durable한지 확인한 뒤 복사본만 영속화한다.
class Disk:
    def __init__(self) -> None:
        self.pages: dict[int, Page] = {}
        self.write_events: list[tuple[int, int]] = []

    def read(self, page_id: int) -> Page:
        return replace(self.pages.get(page_id, Page()))

    def write(self, page_id: int, page: Page, log: LogManager) -> None:
        if page.page_lsn > log.flushed_lsn:
            raise WALViolation("log must be flushed before the data page")
        self.pages[page_id] = replace(page)
        self.write_events.append((page_id, page.page_lsn))


# [Implementation 4] Recovery는 commit 집합과 update history를 분류하고 page LSN보다 새로운 record만 redo한다.
class RecoveryManager:
    def recover(self, disk: Disk, records: list[LogRecord]) -> None:
        committed = {record.txid for record in records if record.kind == "COMMIT"}
        updates = [record for record in records if record.kind == "UPDATE"]

        # REDO: repeat history. page_lsn으로 이미 반영된 update를 건너뛴다.
        for record in updates:
            assert record.page_id is not None and record.after is not None
            page = disk.pages.setdefault(record.page_id, Page())
            if page.page_lsn < record.lsn:
                page.value = record.after
                page.page_lsn = record.lsn

        # [Implementation 5] Commit되지 않은 transaction은 역순 undo해 같은 page의 before image 순서를 복원한다.
        # UNDO: crash 시점에 commit되지 않은 transaction을 역순으로 되돌린다.
        losers = {record.txid for record in updates} - committed
        for record in reversed(updates):
            if record.txid not in losers:
                continue
            assert record.page_id is not None and record.before is not None
            page = disk.pages.setdefault(record.page_id, Page())
            page.value = record.before
            # 교육용 모델에서는 CLR 대신 원 update LSN을 유지한다. 재실행해도 결과는 같다.
            page.page_lsn = max(page.page_lsn, record.lsn)
