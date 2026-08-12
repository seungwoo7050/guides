#!/usr/bin/env python3
"""pin·dirty·Clock 교체 계약의 최소 예시다."""

from __future__ import annotations

from dataclasses import dataclass


# [Implementation 1] Frame 하나가 residency, pin, dirty와 second-chance 상태를 함께 소유한다.
@dataclass
class Frame:
    page_id: int | None = None
    pin_count: int = 0
    dirty: bool = False
    referenced: bool = False


# [Implementation 2] Clock이 frame 집합과 순환 hand의 유일한 owner다.
class Clock:
    def __init__(self, capacity: int) -> None:
        self.frames = [Frame() for _ in range(capacity)]
        self.hand = 0

    # [Implementation 3] Pin은 축출을 금지하고 referenced bit는 한 순회 동안 두 번째 기회를 준다.
    def victim(self) -> int:
        for _ in range(len(self.frames) * 2 + 1):
            frame = self.frames[self.hand]
            index = self.hand
            self.hand = (self.hand + 1) % len(self.frames)
            if frame.pin_count > 0:
                continue
            if frame.referenced:
                frame.referenced = False
                continue
            return index
        raise RuntimeError("all frames are pinned")


# [Implementation 4] Pinned frame을 건너뛴 뒤 reference bit가 지워진 frame을 다시 선택하는지 관찰한다.
clock = Clock(2)
clock.frames[0] = Frame(page_id=1, referenced=True)
clock.frames[1] = Frame(page_id=2, pin_count=1)
assert clock.victim() == 0
print("buffer pool example: PASS")
