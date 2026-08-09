"""Public wire, client, log, and snapshot contracts for the capstone."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
import hashlib
import json
from typing import Any


class Role(str, Enum):
    FOLLOWER = "FOLLOWER"
    CANDIDATE = "CANDIDATE"
    LEADER = "LEADER"


class MessageKind(str, Enum):
    REQUEST_VOTE = "REQUEST_VOTE"
    REQUEST_VOTE_RESPONSE = "REQUEST_VOTE_RESPONSE"
    APPEND_ENTRIES = "APPEND_ENTRIES"
    APPEND_ENTRIES_RESPONSE = "APPEND_ENTRIES_RESPONSE"
    INSTALL_SNAPSHOT = "INSTALL_SNAPSHOT"
    INSTALL_SNAPSHOT_RESPONSE = "INSTALL_SNAPSHOT_RESPONSE"


@dataclass(frozen=True)
class Command:
    """A state-machine operation; transport retry identity lives on ClientRequest."""

    kind: str
    key: str
    value: Any = None
    expected: Any = None


def canonical_fingerprint(command: Command) -> str:
    encoded = json.dumps(
        asdict(command), ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


@dataclass(frozen=True)
class ClientRequest:
    client_id: str
    sequence: int
    fingerprint: str
    command: Command

    def __post_init__(self) -> None:
        if not self.client_id:
            raise ValueError("client_id must be non-empty")
        if self.sequence < 1:
            raise ValueError("sequence must start at 1")
        if self.fingerprint != canonical_fingerprint(self.command):
            raise ValueError("fingerprint must be the canonical command fingerprint")


@dataclass(frozen=True)
class LogEntry:
    index: int
    term: int
    request: ClientRequest | None


@dataclass(frozen=True)
class SessionRecord:
    last_sequence: int
    last_fingerprint: str
    last_result: Any


@dataclass(frozen=True)
class Snapshot:
    schema_version: int
    checksum: str
    last_included_index: int
    last_included_term: int
    state_machine: dict[str, Any]
    client_sessions: dict[str, SessionRecord]
    configuration: tuple[str, ...]
    generation: int = 0


def snapshot_checksum(
    *,
    schema_version: int,
    last_included_index: int,
    last_included_term: int,
    state_machine: dict[str, Any],
    client_sessions: dict[str, SessionRecord],
    configuration: tuple[str, ...],
    generation: int,
) -> str:
    payload = {
        "schema_version": schema_version,
        "last_included_index": last_included_index,
        "last_included_term": last_included_term,
        "state_machine": state_machine,
        "client_sessions": {
            key: asdict(value) for key, value in sorted(client_sessions.items())
        },
        "configuration": list(configuration),
        "generation": generation,
    }
    encoded = json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def build_snapshot(
    *,
    last_included_index: int,
    last_included_term: int,
    state_machine: dict[str, Any],
    client_sessions: dict[str, SessionRecord],
    configuration: tuple[str, ...],
    generation: int,
) -> Snapshot:
    checksum = snapshot_checksum(
        schema_version=1,
        last_included_index=last_included_index,
        last_included_term=last_included_term,
        state_machine=state_machine,
        client_sessions=client_sessions,
        configuration=configuration,
        generation=generation,
    )
    return Snapshot(
        schema_version=1,
        checksum=checksum,
        last_included_index=last_included_index,
        last_included_term=last_included_term,
        state_machine=state_machine,
        client_sessions=client_sessions,
        configuration=configuration,
        generation=generation,
    )


@dataclass(frozen=True)
class Message:
    source: str
    target: str
    term: int
    kind: MessageKind
    payload: dict[str, Any] = field(default_factory=dict)
    message_id: str | None = None


@dataclass(frozen=True)
class ClientResponse:
    client_id: str
    sequence: int
    status: str
    result: Any = None
    leader_hint: str | None = None
    term: int | None = None
