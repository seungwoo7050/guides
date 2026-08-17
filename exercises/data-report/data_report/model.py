"""Immutable domain values used after the external-input boundary."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


class DataReportError(ValueError):
    """Raised when external data does not satisfy the report contract."""


# [Implementation 2]
# Validated input becomes immutable before aggregation.
@dataclass(frozen=True, slots=True)
class Record:
    category: str
    amount: Decimal


@dataclass(frozen=True, slots=True)
class CategoryTotal:
    category: str
    count: int
    total: Decimal


@dataclass(frozen=True, slots=True)
class Report:
    rows: tuple[CategoryTotal, ...]
    count: int
    total: Decimal
