"""set-associative write-back cache와 3C miss 분류를 시뮬레이션합니다."""
from __future__ import annotations
from collections import OrderedDict
from dataclasses import dataclass
from typing import Any, Iterable

@dataclass
class Line:
    block: int
    dirty: bool = False

@dataclass(frozen=True)
class Access:
    kind: str
    address: int

def parse_trace(lines: Iterable[str]) -> list[Access]:
    result: list[Access] = []
    for number, raw in enumerate(lines, 1):
        text = raw.split('#', 1)[0].strip()
        if not text:
            continue
        parts = text.split()
        if len(parts) != 2 or parts[0].upper() not in {'R', 'W'}:
            raise ValueError(f"{number}행: 'R 주소' 또는 'W 주소' 형식이어야 합니다")
        address = int(parts[1], 0)
        if address < 0:
            raise ValueError(f'{number}행: 주소는 음수일 수 없습니다')
        result.append(Access(parts[0].upper(), address))
    return result

class CacheSimulator:

    def __init__(self, size_bytes: int, block_size: int, associativity: int, write_allocate: bool=True) -> None:
        if size_bytes <= 0 or block_size <= 0 or associativity <= 0:
            raise ValueError('cache 크기, block 크기와 associativity는 양수여야 합니다')
        if block_size & block_size - 1:
            raise ValueError('block_size는 2의 거듭제곱이어야 합니다')
        if size_bytes % (block_size * associativity):
            raise ValueError('size_bytes는 block_size * associativity의 배수여야 합니다')
        self.size_bytes = size_bytes
        self.block_size = block_size
        self.associativity = associativity
        self.set_count = size_bytes // (block_size * associativity)
        self.line_count = size_bytes // block_size
        self.write_allocate = write_allocate
        self.sets: list[OrderedDict[int, Line]] = [OrderedDict() for _ in range(self.set_count)]
        self.shadow: OrderedDict[int, None] = OrderedDict()
        self.seen: set[int] = set()
        self.hits = 0
        self.misses = 0
        self.reads = 0
        self.writes = 0
        self.compulsory = 0
        self.conflict = 0
        self.capacity = 0
        self.writebacks = 0
        self.memory_writes = 0
        self.events: list[dict[str, Any]] = []

    def _touch_shadow(self, block: int) -> bool:
        hit = block in self.shadow
        if hit:
            self.shadow.move_to_end(block)
        else:
            self.shadow[block] = None
            if len(self.shadow) > self.line_count:
                self.shadow.popitem(last=False)
        return hit

    def access(self, access: Access) -> None:
        """TODO: 문서의 불변식과 테스트를 기준으로 구현하세요."""
        raise NotImplementedError('TODO: access')

    def run(self, accesses: list[Access]) -> dict[str, Any]:
        """TODO: 문서의 불변식과 테스트를 기준으로 구현하세요."""
        raise NotImplementedError('TODO: run')
