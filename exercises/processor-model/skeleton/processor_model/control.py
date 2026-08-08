"""Tiny-RISC 명령을 단순 단일 사이클 데이터패스 제어 신호로 변환합니다."""
from __future__ import annotations
from typing import Any
CONTROL: dict[str, dict[str, Any]] = {}

def signals(opcode: str) -> dict[str, Any]:
    """TODO: 문서의 불변식과 테스트를 기준으로 구현하세요."""
    raise NotImplementedError('TODO: signals')
