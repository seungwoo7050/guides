#!/usr/bin/env python3
"""pin·dirty·Clock 교체 계약의 최소 예시다."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Frame:
    page_id: int | None = None
    pin_count: int = 0
    dirty: bool = False
    referenced: bool = False


class Clock:
    def __init__(self, capacity: int) -> None:
        self.frames = [Frame() for _ in range(capacity)]
        self.hand = 0

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


clock = Clock(2)
clock.frames[0] = Frame(page_id=1, referenced=True)
clock.frames[1] = Frame(page_id=2, pin_count=1)
assert clock.victim() == 0
print("buffer pool example: PASS")
