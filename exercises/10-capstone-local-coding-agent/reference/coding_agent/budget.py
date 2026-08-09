from __future__ import annotations

import time
from dataclasses import asdict
from typing import Any

from .errors import BudgetExceeded
from .types import RunBudget, UsageReceipt


class BudgetLedger:
    """Reserve work before execution and account for the actual result."""

    def __init__(self, budget: RunBudget | None = None, *, started_at: float | None = None) -> None:
        self.budget = budget or RunBudget()
        self.started_at = time.monotonic() if started_at is None else started_at

    def _wall_guard(self) -> None:
        if time.monotonic() - self.started_at >= self.budget.max_wall_seconds:
            raise BudgetExceeded("wall-time budget exhausted")

    def reserve_step(self) -> None:
        self._wall_guard()
        if self.budget.steps >= self.budget.max_steps:
            raise BudgetExceeded("step budget exhausted")
        self.budget.steps += 1

    def reserve_model_call(self) -> None:
        self._wall_guard()
        if self.budget.model_calls >= self.budget.max_model_calls:
            raise BudgetExceeded("model-call budget exhausted")
        self.budget.model_calls += 1

    def record_usage(self, usage: UsageReceipt) -> None:
        tokens = usage.input_tokens + usage.output_tokens
        if self.budget.tokens + tokens > self.budget.max_tokens:
            raise BudgetExceeded("token budget exhausted")
        if self.budget.cost_microunits + usage.cost_microunits > self.budget.max_cost_microunits:
            raise BudgetExceeded("cost budget exhausted")
        self.budget.tokens += tokens
        self.budget.cost_microunits += usage.cost_microunits

    def reserve_tool_call(self, *, read_bytes: int = 0, writes: int = 0) -> None:
        self._wall_guard()
        if self.budget.tool_calls >= self.budget.max_tool_calls:
            raise BudgetExceeded("tool-call budget exhausted")
        if self.budget.read_bytes + read_bytes > self.budget.max_read_bytes:
            raise BudgetExceeded("read-byte budget exhausted")
        if self.budget.writes + writes > self.budget.max_writes:
            raise BudgetExceeded("write budget exhausted")
        self.budget.tool_calls += 1
        self.budget.read_bytes += read_bytes
        self.budget.writes += writes

    def record_read_bytes(self, amount: int) -> None:
        if amount < 0 or self.budget.read_bytes + amount > self.budget.max_read_bytes:
            raise BudgetExceeded("read-byte budget exhausted")
        self.budget.read_bytes += amount

    def record_command_seconds(self, seconds: float) -> None:
        if self.budget.command_seconds + seconds > self.budget.max_command_seconds:
            raise BudgetExceeded("command-time budget exhausted")
        self.budget.command_seconds += seconds

    def remaining(self) -> dict[str, int | float]:
        return {
            "steps": self.budget.max_steps - self.budget.steps,
            "model_calls": self.budget.max_model_calls - self.budget.model_calls,
            "tool_calls": self.budget.max_tool_calls - self.budget.tool_calls,
            "read_bytes": self.budget.max_read_bytes - self.budget.read_bytes,
            "writes": self.budget.max_writes - self.budget.writes,
            "command_seconds": self.budget.max_command_seconds - self.budget.command_seconds,
            "tokens": self.budget.max_tokens - self.budget.tokens,
            "cost_microunits": self.budget.max_cost_microunits - self.budget.cost_microunits,
            "wall_seconds": max(
                0.0, self.budget.max_wall_seconds - (time.monotonic() - self.started_at)
            ),
        }

    def to_mapping(self) -> dict[str, Any]:
        return asdict(self.budget)

    @classmethod
    def from_mapping(cls, value: dict[str, Any]) -> "BudgetLedger":
        return cls(RunBudget(**value))
