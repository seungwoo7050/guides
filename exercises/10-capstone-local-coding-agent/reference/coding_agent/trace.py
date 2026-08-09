from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from .errors import ContractError
from .util import atomic_write_text, canonical_json, sha256_text


SENSITIVE_KEYS = {"secret", "password", "credential", "authorization", "token", "content", "api_key"}
SECRET_PATTERN = re.compile(r"(?i)(api[_-]?key|secret|password|token)\s*[:=]\s*[^\s,;]+")


def redact(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {
            str(key): "[REDACTED]" if _sensitive_key(str(key)) else redact(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [redact(item) for item in value]
    if isinstance(value, tuple):
        return [redact(item) for item in value]
    if isinstance(value, str):
        return SECRET_PATTERN.sub(lambda match: f"{match.group(1)}=[REDACTED]", value)
    return value


def _sensitive_key(key: str) -> bool:
    """Match credential fields without erasing counters such as input_tokens."""
    normalized = key.lower()
    return normalized in SENSITIVE_KEYS or normalized.endswith(
        ("_secret", "_password", "_credential", "_authorization", "_token", "_api_key")
    )


class EventLog:
    def __init__(self, path: Path, *, session_id: str) -> None:
        self.path = path
        self.session_id = session_id
        self._events = self.load() if path.exists() else []

    def append(self, event_type: str, payload: Mapping[str, Any] | None = None) -> dict[str, Any]:
        previous = self._events[-1]["digest"] if self._events else "GENESIS"
        event = {
            "event_version": "1",
            "session_id": self.session_id,
            "sequence": len(self._events) + 1,
            "time": datetime.now(timezone.utc).isoformat(),
            "type": event_type,
            "payload": redact(dict(payload or {})),
            "previous_digest": previous,
        }
        event["digest"] = sha256_text(canonical_json(event))
        self._events.append(event)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        existing = self.path.read_text(encoding="utf-8") if self.path.exists() else ""
        atomic_write_text(self.path, existing + json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n")
        return event

    def load(self) -> list[dict[str, Any]]:
        events: list[dict[str, Any]] = []
        previous = "GENESIS"
        for number, line in enumerate(self.path.read_text(encoding="utf-8").splitlines(), 1):
            try:
                event = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ContractError(f"invalid event JSON at line {number}") from exc
            digest = event.pop("digest", None)
            if event.get("previous_digest") != previous or digest != sha256_text(canonical_json(event)):
                raise ContractError(f"event integrity failure at line {number}")
            event["digest"] = digest
            previous = digest
            events.append(event)
        return events

    @property
    def events(self) -> tuple[dict[str, Any], ...]:
        return tuple(self._events)

    @property
    def head(self) -> str:
        return self._events[-1]["digest"] if self._events else "GENESIS"
