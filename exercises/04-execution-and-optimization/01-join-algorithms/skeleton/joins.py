from __future__ import annotations

from typing import Any

Row = dict[str, Any]
Joined = tuple[Row, Row]


def nested_loop_join(left: list[Row], right: list[Row], left_key: str, right_key: str) -> list[Joined]:
    raise NotImplementedError


def hash_join(left: list[Row], right: list[Row], left_key: str, right_key: str) -> list[Joined]:
    raise NotImplementedError


def merge_join(left: list[Row], right: list[Row], left_key: str, right_key: str) -> list[Joined]:
    raise NotImplementedError
