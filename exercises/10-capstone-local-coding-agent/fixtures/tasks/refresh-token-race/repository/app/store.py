from __future__ import annotations

from collections.abc import Callable


class RefreshTokenStore:
    def __init__(self) -> None:
        self._used: set[str] = set()

    def consume(self, token: str, *, before_commit: Callable[[], None] | None = None) -> bool:
        if token in self._used:
            return False
        if before_commit is not None:
            before_commit()
        self._used.add(token)
        return True
