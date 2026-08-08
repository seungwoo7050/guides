"""2비트 포화 계수기로 조건 분기의 방향을 예측합니다."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class Branch:
    pc: int
    taken: bool


class TwoBitPredictor:
    def __init__(self, entries: int) -> None:
        if (
            not isinstance(entries, int)
            or isinstance(entries, bool)
            or entries <= 0
            or entries & (entries - 1)
        ):
            raise ValueError("entries는 양의 2의 거듭제곱이어야 합니다.")
        self._counters = [1] * entries
        self.predictions = 0
        self.mispredictions = 0

    def predict(self, pc: int) -> bool:
        raise NotImplementedError("TODO: 2비트 계수기의 예측 방향을 반환하세요.")

    def update(self, pc: int, taken: bool) -> bool:
        raise NotImplementedError("TODO: 실제 분기 결과로 계수기를 갱신하세요.")

    def run(self, branches: Iterable[Branch]) -> dict[str, object]:
        raise NotImplementedError("TODO: trace의 정확도와 최종 계수기를 계산하세요.")
