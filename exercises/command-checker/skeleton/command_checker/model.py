"""2단계에서 불변 데이터 계약을 완성합니다."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

DEFAULT_OUTPUT_LIMIT = 1024 * 1024


@dataclass(frozen=True)
class Case:
    name: str
    args: tuple[str, ...] = ()
    stdin: str = ""
    stdout: str = ""
    stderr: str = ""
    returncode: int = 0
    timeout: float = 2.0
    cwd: Path | None = None
    # TODO(stage 02): 공유 가능한 불변 표현으로 바꾸십시오.
    env: dict[str, str] = field(default_factory=dict)
    output_limit: int = DEFAULT_OUTPUT_LIMIT

    def environment_overrides(self) -> dict[str, str]:
        return dict(self.env)


@dataclass(frozen=True)
class Result:
    name: str
    passed: bool
    duration_ms: int
    failures: tuple[str, ...]
    returncode: int | None
    stdout: str
    stderr: str
    # TODO(stage 02): 수명 제한 상태를 모델에 추가하십시오.


class SpecificationError(ValueError):
    """외부 명세가 시작 계약을 만족하지 않습니다."""


class ExecutionError(RuntimeError):
    """검사 대상 프로세스를 시작하거나 관리할 수 없습니다."""
