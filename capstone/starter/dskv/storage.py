"""Crash-recovery storage boundary used by the protocol core."""
from __future__ import annotations

import copy
from dataclasses import dataclass, field

from .types import LogEntry, Snapshot


@dataclass
class PersistentState:
    current_term: int = 0
    voted_for: str | None = None
    log: list[LogEntry] = field(default_factory=list)
    snapshot: Snapshot | None = None


class MemoryStorage:
    """An atomic in-memory durable store.

    `Node` instances may disappear, but the storage object survives `Cluster.crash`
    and is reused by `Cluster.restart`. Reads and writes deep-copy state so protocol
    code cannot mutate durable data without an explicit `save` call.
    """

    def __init__(self, initial: PersistentState | None = None) -> None:
        self._state = copy.deepcopy(initial or PersistentState())
        self._writes = 0

    def load(self) -> PersistentState:
        return copy.deepcopy(self._state)

    def save(self, state: PersistentState) -> None:
        self._validate(state)
        self._state = copy.deepcopy(state)
        self._writes += 1

    @property
    def write_count(self) -> int:
        return self._writes

    @staticmethod
    def _validate(state: PersistentState) -> None:
        if state.current_term < 0:
            raise ValueError("current_term must be non-negative")
        previous_index = state.snapshot.last_included_index if state.snapshot else 0
        for entry in state.log:
            if entry.index <= previous_index:
                raise ValueError("log index must follow snapshot index")
            if entry.index != previous_index + 1:
                raise ValueError("log entries must be contiguous")
            if entry.term < 0:
                raise ValueError("entry term must be non-negative")
            previous_index = entry.index
