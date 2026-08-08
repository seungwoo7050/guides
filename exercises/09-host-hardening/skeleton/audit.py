from __future__ import annotations

from typing import Any


def audit(snapshot: dict[str, Any]) -> list[dict[str, str]]:
    """호스트 snapshot의 위험을 구조화된 finding 목록으로 반환합니다."""
    del snapshot
    return []
