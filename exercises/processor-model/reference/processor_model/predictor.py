"""2비트 포화 계수기로 조건 분기의 방향을 예측합니다."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class Branch:
    pc: int
    taken: bool


class TwoBitPredictor:
    """PC 하위 인덱스로 2비트 계수기 표를 조회합니다.

    각 계수기는 약한 비실행 상태인 1에서 시작합니다. 0과 1은 분기가
    실행되지 않는다고 예측하고, 2와 3은 실행된다고 예측합니다.
    """

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

    def _index(self, pc: int) -> int:
        if (
            not isinstance(pc, int)
            or isinstance(pc, bool)
            or pc < 0
            or pc % 4
        ):
            raise ValueError("pc는 0 이상의 4바이트 정렬 주소여야 합니다.")
        return (pc // 4) & (len(self._counters) - 1)

    def predict(self, pc: int) -> bool:
        return self._counters[self._index(pc)] >= 2

    def update(self, pc: int, taken: bool) -> bool:
        if not isinstance(taken, bool):
            raise ValueError("taken은 bool 값이어야 합니다.")
        index = self._index(pc)
        predicted = self._counters[index] >= 2
        self.predictions += 1
        if predicted != taken:
            self.mispredictions += 1
        if taken:
            self._counters[index] = min(3, self._counters[index] + 1)
        else:
            self._counters[index] = max(0, self._counters[index] - 1)
        return predicted

    def run(self, branches: Iterable[Branch]) -> dict[str, object]:
        for branch in branches:
            if not isinstance(branch, Branch):
                raise ValueError("trace에는 Branch 값만 사용할 수 있습니다.")
            self.update(branch.pc, branch.taken)
        return {
            "predictions": self.predictions,
            "mispredictions": self.mispredictions,
            "accuracy": (
                (self.predictions - self.mispredictions) / self.predictions
                if self.predictions
                else 0.0
            ),
            "counters": list(self._counters),
        }
