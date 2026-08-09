"""Crash-recovery storage boundary used by the protocol core."""
from __future__ import annotations

import copy
from dataclasses import dataclass, field

from .types import LogEntry, Snapshot, snapshot_checksum


class SimulatedCrash(RuntimeError):
    """A deterministic crash immediately before or after one atomic save."""


@dataclass
class PersistentState:
    current_term: int = 0
    voted_for: str | None = None
    log: list[LogEntry] = field(default_factory=list)
    snapshot: Snapshot | None = None


class MemoryStorage:
    """An atomic in-memory durable store with an explicit one-shot crash hook."""

    def __init__(self, initial: PersistentState | None = None) -> None:
        candidate = copy.deepcopy(initial or PersistentState())
        self._validate(candidate)
        self._state = candidate
        self._writes = 0
        self._fault: str | None = None
        self._history: list[PersistentState] = [copy.deepcopy(candidate)]

    def load(self) -> PersistentState:
        return copy.deepcopy(self._state)

    def fail_next_save(self, phase: str) -> None:
        if phase not in {"before", "after"}:
            raise ValueError("save fault phase must be 'before' or 'after'")
        if self._fault is not None:
            raise RuntimeError("a save fault is already armed")
        self._fault = phase

    def save(self, state: PersistentState) -> None:
        self._validate(state)
        self._validate_transition(self._state, state)
        phase, self._fault = self._fault, None
        if phase == "before":
            raise SimulatedCrash("crash before atomic save")
        self._state = copy.deepcopy(state)
        self._writes += 1
        self._history.append(copy.deepcopy(state))
        if phase == "after":
            raise SimulatedCrash("crash after atomic save")

    @property
    def write_count(self) -> int:
        return self._writes

    @property
    def history(self) -> list[PersistentState]:
        return copy.deepcopy(self._history)

    @staticmethod
    def _validate(state: PersistentState) -> None:
        if state.current_term < 0:
            raise ValueError("current_term must be non-negative")
        previous_index = 0
        maximum_term = 0
        previous_term = 0
        if state.snapshot is not None:
            snapshot = state.snapshot
            if snapshot.schema_version != 1:
                raise ValueError("unsupported snapshot schema_version")
            if snapshot.last_included_index < 0 or snapshot.last_included_term < 0:
                raise ValueError("snapshot index and term must be non-negative")
            if snapshot.generation < 0:
                raise ValueError("snapshot generation must be non-negative")
            if not snapshot.configuration or len(set(snapshot.configuration)) != len(snapshot.configuration):
                raise ValueError("snapshot configuration must contain unique voters")
            expected = snapshot_checksum(
                schema_version=snapshot.schema_version,
                last_included_index=snapshot.last_included_index,
                last_included_term=snapshot.last_included_term,
                state_machine=snapshot.state_machine,
                client_sessions=snapshot.client_sessions,
                configuration=snapshot.configuration,
                generation=snapshot.generation,
            )
            if snapshot.checksum != expected:
                raise ValueError("snapshot checksum mismatch")
            previous_index = snapshot.last_included_index
            maximum_term = snapshot.last_included_term
            previous_term = snapshot.last_included_term
        for entry in state.log:
            if entry.index != previous_index + 1:
                raise ValueError("log entries must be contiguous after the snapshot")
            if entry.term < 0:
                raise ValueError("entry term must be non-negative")
            if entry.term < previous_term:
                raise ValueError("log terms must be non-decreasing")
            previous_index = entry.index
            previous_term = entry.term
            maximum_term = max(maximum_term, entry.term)
        if state.current_term < maximum_term:
            raise ValueError("current_term must not be behind durable log or snapshot terms")

    @staticmethod
    def _validate_transition(current: PersistentState, candidate: PersistentState) -> None:
        old = current.snapshot
        new = candidate.snapshot
        if old is None:
            return
        if new is None:
            raise ValueError("durable snapshot must not be removed")
        if new.last_included_index < old.last_included_index:
            raise ValueError("snapshot index must not move backwards")
        if new.generation < old.generation:
            raise ValueError("snapshot generation must not move backwards")
        if new.last_included_index == old.last_included_index:
            if new.checksum != old.checksum:
                raise ValueError("same snapshot boundary must keep identical state")
        elif new.generation <= old.generation:
            raise ValueError("newer snapshot boundary requires a newer generation")
