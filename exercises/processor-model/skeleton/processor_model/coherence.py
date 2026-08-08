"""단순 snooping MESI cache coherence trace 시뮬레이터입니다."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Iterable

@dataclass(frozen=True)
class Access:
    kind: str
    core: int
    address: int

def parse_trace(lines: Iterable[str]) -> list[Access]:
    result: list[Access] = []
    for number, raw in enumerate(lines, 1):
        text = raw.split('#', 1)[0].strip()
        if not text:
            continue
        parts = text.split()
        if len(parts) != 3 or parts[0].upper() not in {'R', 'W'}:
            raise ValueError(f"{number}행: 'R core 주소' 또는 'W core 주소' 형식이어야 합니다")
        core = int(parts[1], 0)
        address = int(parts[2], 0)
        if core < 0 or address < 0:
            raise ValueError(f'{number}행: core와 주소는 음수일 수 없습니다')
        result.append(Access(parts[0].upper(), core, address))
    return result

class MESISimulator:

    def __init__(self, cores: int, line_size: int) -> None:
        if cores < 2:
            raise ValueError('cores는 2 이상이어야 합니다')
        if line_size <= 0 or line_size & line_size - 1:
            raise ValueError('line_size는 2의 거듭제곱이어야 합니다')
        self.cores = cores
        self.line_size = line_size
        self.states: dict[int, list[str]] = {}
        self.bus_reads = 0
        self.bus_read_exclusive = 0
        self.bus_upgrades = 0
        self.invalidations = 0
        self.writebacks = 0
        self.hits = 0
        self.misses = 0
        self.events: list[dict[str, Any]] = []

    def _line_states(self, block: int) -> list[str]:
        return self.states.setdefault(block, ['I'] * self.cores)

    def access(self, access: Access) -> None:
        """TODO: 문서의 불변식과 테스트를 기준으로 구현하세요."""
        raise NotImplementedError('TODO: access')

    def run(self, accesses: list[Access]) -> dict[str, Any]:
        """TODO: 문서의 불변식과 테스트를 기준으로 구현하세요."""
        raise NotImplementedError('TODO: run')
