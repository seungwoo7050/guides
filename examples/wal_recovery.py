#!/usr/bin/env python3
"""page LSN보다 새로운 로그만 redo하는 최소 복구 예시다."""

from dataclasses import dataclass


@dataclass
class Page:
    value: int
    page_lsn: int


@dataclass(frozen=True)
class LogRecord:
    lsn: int
    value: int


def redo(page: Page, records: list[LogRecord]) -> Page:
    for record in records:
        if record.lsn > page.page_lsn:
            page.value = record.value
            page.page_lsn = record.lsn
    return page


recovered = redo(Page(value=10, page_lsn=1), [LogRecord(1, 10), LogRecord(2, 15)])
assert recovered == Page(value=15, page_lsn=2)
print("wal recovery example: PASS")
