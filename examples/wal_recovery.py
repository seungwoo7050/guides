#!/usr/bin/env python3
"""page LSN보다 새로운 로그만 redo하는 최소 복구 예시다."""

from dataclasses import dataclass


# [Implementation 1] Page LSN과 immutable log record가 replay 여부를 결정하는 최소 상태다.
@dataclass
class Page:
    value: int
    page_lsn: int


@dataclass(frozen=True)
class LogRecord:
    lsn: int
    value: int


# [Implementation 2] Page보다 새로운 LSN만 적용해 같은 record를 반복해도 상태가 더 진행되지 않게 한다.
def redo(page: Page, records: list[LogRecord]) -> Page:
    for record in records:
        if record.lsn > page.page_lsn:
            page.value = record.value
            page.page_lsn = record.lsn
    return page


# [Implementation 3] 이미 반영된 record와 새 record를 섞어 최소 redo 결과를 관찰한다.
recovered = redo(Page(value=10, page_lsn=1), [LogRecord(1, 10), LogRecord(2, 15)])
assert recovered == Page(value=15, page_lsn=2)
print("wal recovery example: PASS")
