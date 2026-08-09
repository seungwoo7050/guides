"""Wire and durable data types shared by the capstone adapters."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
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
    kind: str
    key: str
    value: Any = None
    expected: Any = None
    client_id: str | None = None
    sequence: int | None = None
    fingerprint: str | None = None


@dataclass(frozen=True)
class LogEntry:
    index: int
    term: int
    command: Command | None


@dataclass(frozen=True)
class SessionRecord:
    last_sequence: int
    last_fingerprint: str
    last_result: Any


@dataclass(frozen=True)
class Snapshot:
    last_included_index: int
    last_included_term: int
    state_machine: dict[str, Any]
    client_sessions: dict[str, SessionRecord]
    configuration: tuple[str, ...]
    generation: int = 0


@dataclass(frozen=True)
class Message:
    source: str
    target: str
    term: int
    kind: MessageKind
    payload: dict[str, Any] = field(default_factory=dict)
    message_id: str | None = None


@dataclass(frozen=True)
class ClientRequest:
    client_id: str
    sequence: int
    command: Command


@dataclass(frozen=True)
class ClientResponse:
    client_id: str
    sequence: int
    status: str
    result: Any = None
    leader_hint: str | None = None
    term: int | None = None
