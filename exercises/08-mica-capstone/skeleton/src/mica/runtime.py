from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class RuntimeValue:
    type: str
    value: object


class RuntimeFailure(RuntimeError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
