"""성능 방정식, Amdahl의 법칙과 AMAT 계산입니다."""

from __future__ import annotations

from typing import Any


# [Implementation 3] CPU time, Amdahl과 AMAT를 단위와 입력 범위가 드러나는 순수 계산 경계로 구성합니다.
def cpu_time(instructions: float, cpi: float, frequency_ghz: float) -> dict[str, Any]:
    if instructions < 0:
        raise ValueError("instructions는 음수일 수 없습니다")
    if cpi <= 0:
        raise ValueError("cpi는 0보다 커야 합니다")
    if frequency_ghz <= 0:
        raise ValueError("frequency_ghz는 0보다 커야 합니다")
    cycles = instructions * cpi
    seconds = cycles / (frequency_ghz * 1_000_000_000.0)
    return {
        "instructions": instructions,
        "cpi": cpi,
        "frequency_ghz": frequency_ghz,
        "cycles": cycles,
        "seconds": seconds,
    }


def amdahl(fraction: float, enhanced_speedup: float) -> dict[str, Any]:
    if not 0.0 <= fraction <= 1.0:
        raise ValueError("fraction은 0과 1 사이여야 합니다")
    if enhanced_speedup <= 0:
        raise ValueError("enhanced_speedup은 0보다 커야 합니다")
    total = (1.0 - fraction) + fraction / enhanced_speedup
    speedup = 1.0 / total
    limit = None if fraction == 1.0 else 1.0 / (1.0 - fraction)
    return {
        "enhanced_fraction": fraction,
        "enhanced_part_speedup": enhanced_speedup,
        "normalized_time": total,
        "overall_speedup": speedup,
        "infinite_enhancement_limit": limit,
    }


def amat(hit_time: float, miss_rate: float, miss_penalty: float) -> dict[str, Any]:
    if hit_time < 0 or miss_penalty < 0:
        raise ValueError("시간은 음수일 수 없습니다")
    if not 0.0 <= miss_rate <= 1.0:
        raise ValueError("miss_rate는 0과 1 사이여야 합니다")
    value = hit_time + miss_rate * miss_penalty
    return {
        "hit_time": hit_time,
        "miss_rate": miss_rate,
        "miss_penalty": miss_penalty,
        "amat": value,
    }
