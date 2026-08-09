from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from .errors import ContractError, OperationConflict
from .util import atomic_write_json, read_json, value_digest


class CheckpointStore:
    VERSION = "1"

    def __init__(self, path: Path) -> None:
        self.path = path

    def save(self, state: Mapping[str, Any], *, event_head: str) -> None:
        body = {"checkpoint_version": self.VERSION, "event_head": event_head, "state": dict(state)}
        atomic_write_json(self.path, {"body": body, "digest": value_digest(body)})

    def load(self) -> dict[str, Any]:
        envelope = read_json(self.path)
        body = envelope.get("body") if isinstance(envelope, dict) else None
        if not isinstance(body, dict) or envelope.get("digest") != value_digest(body):
            raise ContractError("checkpoint integrity failure")
        if body.get("checkpoint_version") != self.VERSION:
            raise ContractError("incompatible checkpoint version")
        return body


class OperationLedger:
    """A small durable ledger for single-process teaching scenarios."""

    def __init__(self, path: Path) -> None:
        self.path = path
        if not path.exists():
            atomic_write_json(path, {"ledger_version": "1", "operations": {}})

    def _load(self) -> dict[str, Any]:
        value = read_json(self.path)
        if value.get("ledger_version") != "1" or not isinstance(value.get("operations"), dict):
            raise ContractError("invalid operation ledger")
        return value

    def begin(self, operation_id: str, *, fingerprint: str, details: Mapping[str, Any]) -> dict[str, Any]:
        value = self._load()
        existing = value["operations"].get(operation_id)
        if existing:
            if existing["fingerprint"] != fingerprint:
                raise OperationConflict("operation ID reused with different input")
            return existing
        operation = {"status": "STARTED", "fingerprint": fingerprint, "details": dict(details)}
        value["operations"][operation_id] = operation
        atomic_write_json(self.path, value)
        return operation

    def complete(self, operation_id: str, *, receipt: Mapping[str, Any]) -> None:
        value = self._load()
        if operation_id not in value["operations"]:
            raise ContractError("cannot complete an unknown operation")
        value["operations"][operation_id]["status"] = "COMPLETED"
        value["operations"][operation_id]["receipt"] = dict(receipt)
        atomic_write_json(self.path, value)

    def lookup(self, operation_id: str) -> dict[str, Any] | None:
        return self._load()["operations"].get(operation_id)
