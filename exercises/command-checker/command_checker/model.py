"""Immutable data contracts and boundary exceptions for command-checker."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

DEFAULT_OUTPUT_LIMIT = 1024 * 1024


# [Implementation 2] Immutable case model.
@dataclass(frozen=True, slots=True)
class Case:
    name: str
    args: tuple[str, ...] = ()
    stdin: str = ""
    stdout: str = ""
    stderr: str = ""
    returncode: int = 0
    timeout: float = 2.0
    cwd: Path | None = None
    env: tuple[tuple[str, str], ...] = ()
    output_limit: int = DEFAULT_OUTPUT_LIMIT

    def environment_overrides(self) -> dict[str, str]:
        """Return a fresh environment mapping for the process boundary."""
        return dict(self.env)


# [Implementation 2-1] Immutable result model.
@dataclass(frozen=True, slots=True)
class Result:
    name: str
    passed: bool
    duration_ms: int
    failures: tuple[str, ...]
    returncode: int | None
    stdout: str
    stderr: str
    timed_out: bool = False
    exceeded_stream: str | None = None


# [Implementation 2-2] Boundary error taxonomy.
class SpecificationError(ValueError):
    """The external case specification cannot be accepted safely."""


class ExecutionError(RuntimeError):
    """The target process cannot be started or managed correctly."""
