"""성능 방정식, Amdahl의 법칙과 AMAT 계산입니다."""
from __future__ import annotations
from typing import Any

def cpu_time(instructions: float, cpi: float, frequency_ghz: float) -> dict[str, Any]:
    """TODO: 문서의 불변식과 테스트를 기준으로 구현하세요."""
    raise NotImplementedError('TODO: cpu_time')

def amdahl(fraction: float, enhanced_speedup: float) -> dict[str, Any]:
    """TODO: 문서의 불변식과 테스트를 기준으로 구현하세요."""
    raise NotImplementedError('TODO: amdahl')

def amat(hit_time: float, miss_rate: float, miss_penalty: float) -> dict[str, Any]:
    """TODO: 문서의 불변식과 테스트를 기준으로 구현하세요."""
    raise NotImplementedError('TODO: amat')
