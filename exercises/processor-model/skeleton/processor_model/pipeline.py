"""5단계 in-order 파이프라인의 데이터·제어 hazard를 추적합니다."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any
from .isa import Instruction, sources_and_destination
STAGE_NAMES = ('IF', 'ID', 'EX', 'MEM', 'WB')

@dataclass
class Slot:
    index: int
    instruction: Instruction

@dataclass
class PipelineResult:
    cycles: int
    retired: int
    data_stalls: int
    control_stalls: int
    flushes: int
    timeline: list[dict[str, str]]

    def as_dict(self) -> dict[str, Any]:
        return {'cycles': self.cycles, 'retired': self.retired, 'data_stalls': self.data_stalls, 'control_stalls': self.control_stalls, 'flushes': self.flushes, 'cpi': self.cycles / self.retired if self.retired else 0.0, 'timeline': self.timeline}

def _display(slot: Slot | None) -> str:
    if slot is None:
        return '.'
    return f'I{slot.index}:{slot.instruction.op}'

def _has_data_hazard(id_slot: Slot | None, ex_slot: Slot | None, mem_slot: Slot | None, forwarding: str) -> bool:
    """TODO: 문서의 불변식과 테스트를 기준으로 구현하세요."""
    raise NotImplementedError('TODO: _has_data_hazard')

def simulate(instructions: list[Instruction], forwarding: str='full', branch_penalty: int=2, max_cycles: int=100000) -> PipelineResult:
    """TODO: 문서의 불변식과 테스트를 기준으로 구현하세요."""
    raise NotImplementedError('TODO: simulate')
