from __future__ import annotations

from dataclasses import dataclass


class WALViolation(RuntimeError):
    pass


@dataclass
class Page:
    value: int = 0
    page_lsn: int = 0


class LogManager:
    def __init__(self) -> None:
        # TODO: log records, next LSN, flushed LSN을 초기화한다.
        pass

    def update(self, txid: int, page_id: int, before: int, after: int) -> int:
        raise NotImplementedError("GUIDE_SEMANTIC:wal-update-record")

    def commit(self, txid: int) -> int:
        raise NotImplementedError

    def flush(self, lsn: int) -> None:
        raise NotImplementedError


class Disk:
    def __init__(self) -> None:
        self.pages: dict[int, Page] = {}

    def write(self, page_id: int, page: Page, log: LogManager) -> None:
        raise NotImplementedError


class RecoveryManager:
    def recover(self, disk: Disk, records: list[object]) -> None:
        raise NotImplementedError
