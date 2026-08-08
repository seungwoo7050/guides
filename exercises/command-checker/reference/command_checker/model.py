"""명령 검사기의 불변 데이터 계약과 경계 예외입니다."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

DEFAULT_OUTPUT_LIMIT = 1024 * 1024


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
        """프로세스 경계에서만 사용할 새 환경 변수 dict를 만듭니다."""

        return dict(self.env)


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


class SpecificationError(ValueError):
    """외부 명세가 검사를 시작하기 위한 계약을 만족하지 않습니다."""


class ExecutionError(RuntimeError):
    """검사 대상 프로세스를 시작하거나 관리할 수 없습니다."""
