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
        text = raw.split("#", 1)[0].strip()
        if not text:
            continue
        parts = text.split()
        if len(parts) != 3 or parts[0].upper() not in {"R", "W"}:
            raise ValueError(f"{number}행: 'R core 주소' 또는 'W core 주소' 형식이어야 합니다")
        core = int(parts[1], 0)
        address = int(parts[2], 0)
        if core < 0 or address < 0:
            raise ValueError(f"{number}행: core와 주소는 음수일 수 없습니다")
        result.append(Access(parts[0].upper(), core, address))
    return result


# [Implementation 10] cache block별 안정 MESI state vector를 소유하고 transient network timing은 모델 밖에 둡니다.
class MESISimulator:
    def __init__(self, cores: int, line_size: int) -> None:
        if cores < 2:
            raise ValueError("cores는 2 이상이어야 합니다")
        if line_size <= 0 or line_size & (line_size - 1):
            raise ValueError("line_size는 2의 거듭제곱이어야 합니다")
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
        return self.states.setdefault(block, ["I"] * self.cores)

    # [Implementation 10-1] BusRd·BusRdX·BusUpgr, invalidation과 write-back을 전후 state 증거와 함께 기록합니다.
    def access(self, access: Access) -> None:
        if access.core >= self.cores:
            raise ValueError(f"존재하지 않는 core입니다: {access.core}")
        block = access.address // self.line_size
        states = self._line_states(block)
        before = list(states)
        local = states[access.core]
        bus_event = "none"

        if access.kind == "R":
            if local != "I":
                self.hits += 1
            else:
                self.misses += 1
                self.bus_reads += 1
                bus_event = "BusRd"
                sharers = [index for index, state in enumerate(states) if state != "I"]
                if not sharers:
                    states[access.core] = "E"
                else:
                    for index in sharers:
                        if states[index] == "M":
                            self.writebacks += 1
                        states[index] = "S"
                    states[access.core] = "S"
        else:
            if local == "M":
                self.hits += 1
            elif local == "E":
                self.hits += 1
                states[access.core] = "M"
            elif local == "S":
                self.hits += 1
                self.bus_upgrades += 1
                bus_event = "BusUpgr"
                for index, state in enumerate(states):
                    if index != access.core and state != "I":
                        states[index] = "I"
                        self.invalidations += 1
                states[access.core] = "M"
            else:
                self.misses += 1
                self.bus_read_exclusive += 1
                bus_event = "BusRdX"
                for index, state in enumerate(states):
                    if index == access.core or state == "I":
                        continue
                    if state == "M":
                        self.writebacks += 1
                    states[index] = "I"
                    self.invalidations += 1
                states[access.core] = "M"

        self.events.append(
            {
                "kind": access.kind,
                "core": access.core,
                "address": access.address,
                "block": block,
                "word_offset": access.address % self.line_size,
                "local_hit": local != "I",
                "bus_event": bus_event,
                "before": before,
                "after": list(states),
            }
        )

    def run(self, accesses: list[Access]) -> dict[str, Any]:
        for access in accesses:
            self.access(access)
        total = self.hits + self.misses
        return {
            "configuration": {"cores": self.cores, "line_size": self.line_size},
            "accesses": total,
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": self.hits / total if total else 0.0,
            "bus_reads": self.bus_reads,
            "bus_read_exclusive": self.bus_read_exclusive,
            "bus_upgrades": self.bus_upgrades,
            "invalidations": self.invalidations,
            "writebacks": self.writebacks,
            "final_states": {str(block): states for block, states in sorted(self.states.items())},
            "events": self.events,
        }
