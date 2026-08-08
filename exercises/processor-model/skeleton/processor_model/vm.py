"""페이지 테이블과 LRU TLB를 이용한 주소 변환 시뮬레이터입니다."""
from __future__ import annotations
from collections import OrderedDict
from dataclasses import dataclass
from typing import Any, Iterable

@dataclass
class Mapping:
    pfn: int
    permissions: set[str]

@dataclass(frozen=True)
class Operation:
    kind: str
    values: tuple[str, ...]

def parse_operations(lines: Iterable[str]) -> list[Operation]:
    operations: list[Operation] = []
    for number, raw in enumerate(lines, 1):
        text = raw.split('#', 1)[0].strip()
        if not text:
            continue
        parts = text.split()
        kind = parts[0].upper()
        expected = {'R': 2, 'W': 2, 'X': 2, 'MAP': 4, 'UNMAP': 2}
        if kind not in expected or len(parts) != expected[kind]:
            raise ValueError(f'{number}행: 잘못된 VM trace 명령입니다: {text}')
        operations.append(Operation(kind, tuple(parts[1:])))
    return operations

class VirtualMemorySimulator:

    def __init__(self, page_size: int, tlb_entries: int, mappings: dict[int, Mapping] | None=None) -> None:
        if page_size <= 0 or page_size & page_size - 1:
            raise ValueError('page_size는 2의 거듭제곱이어야 합니다')
        if tlb_entries < 0:
            raise ValueError('tlb_entries는 음수일 수 없습니다')
        self.page_size = page_size
        self.tlb_entries = tlb_entries
        self.page_table = dict(mappings or {})
        self.tlb: OrderedDict[int, Mapping] = OrderedDict()
        self.tlb_hits = 0
        self.tlb_misses = 0
        self.page_table_walks = 0
        self.page_faults = 0
        self.protection_faults = 0
        self.invalidations = 0
        self.events: list[dict[str, Any]] = []

    def _invalidate(self, vpn: int) -> None:
        if vpn in self.tlb:
            del self.tlb[vpn]
            self.invalidations += 1

    def _insert_tlb(self, vpn: int, mapping: Mapping) -> None:
        if self.tlb_entries == 0:
            return
        self.tlb[vpn] = mapping
        self.tlb.move_to_end(vpn)
        if len(self.tlb) > self.tlb_entries:
            self.tlb.popitem(last=False)

    def _translate(self, kind: str, address: int) -> None:
        """TODO: 문서의 불변식과 테스트를 기준으로 구현하세요."""
        raise NotImplementedError('TODO: _translate')

    def run(self, operations: list[Operation]) -> dict[str, Any]:
        """TODO: 문서의 불변식과 테스트를 기준으로 구현하세요."""
        raise NotImplementedError('TODO: run')
