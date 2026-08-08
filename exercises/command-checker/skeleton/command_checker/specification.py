"""4단계에서 JSON을 검증된 Case로 변환합니다."""

from __future__ import annotations

from pathlib import Path

from .model import Case


def load_cases(path: Path) -> tuple[Case, ...]:
    raise NotImplementedError("stage 04: JSON 명세 검증을 구현하십시오.")
