from __future__ import annotations

from dataclasses import dataclass, field

from .types import CommandResult
from .util import value_digest


def classify_failure(result: CommandResult) -> str:
    if result.exit_kind == "TIMEOUT":
        return "TIMEOUT"
    if result.exit_kind == "CANCELLED":
        return "CANCELLED"
    if result.exit_kind == "SPAWN_ERROR":
        return "ENVIRONMENT"
    text = (result.stdout + "\n" + result.stderr).lower()
    if "no tests" in text or "collected 0" in text:
        return "TEST_DISCOVERY"
    if "syntaxerror" in text or "typeerror" in text or "assert" in text:
        return "CODE_OR_CONTRACT"
    if result.exit_code not in (0, None):
        return "COMMAND_FAILURE"
    return "PASS"


@dataclass
class IterationTracker:
    max_repeated_failures: int = 2
    plan_revision: int = 1
    failures: list[str] = field(default_factory=list)

    def record(self, result: CommandResult) -> str:
        category = classify_failure(result)
        if category == "PASS":
            return category
        signature = value_digest(
            {"category": category, "stdout": result.stdout[-500:], "stderr": result.stderr[-500:]}
        )
        self.failures.append(signature)
        if self.failures.count(signature) > self.max_repeated_failures:
            return "REPEATED_FAILURE"
        self.plan_revision += 1
        return category
