"""8단계에서 JSON·JUnit 보고서와 원자적 교체를 구현합니다."""

from __future__ import annotations

from pathlib import Path
from typing import Sequence

from .model import Result


def atomic_write_text(path: Path, data: str) -> None:
    raise NotImplementedError("stage 08: 원자적 파일 교체를 구현하십시오.")


def render_json(results: Sequence[Result]) -> str:
    raise NotImplementedError("stage 08: JSON 보고서를 구현하십시오.")


def write_json_report(path: Path, results: Sequence[Result]) -> None:
    raise NotImplementedError("stage 08: JSON 보고서 저장을 구현하십시오.")


def xml_text(value: str) -> str:
    raise NotImplementedError("stage 08: XML 텍스트 정규화를 구현하십시오.")


def render_junit(results: Sequence[Result]) -> str:
    raise NotImplementedError("stage 08: JUnit 보고서를 구현하십시오.")


def write_junit_report(path: Path, results: Sequence[Result]) -> None:
    raise NotImplementedError("stage 08: JUnit 보고서 저장을 구현하십시오.")
