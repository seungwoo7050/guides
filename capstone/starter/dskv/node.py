"""Raft node skeleton. Protocol transitions are intentionally incomplete."""
from __future__ import annotations

from typing import Any

from .storage import MemoryStorage, PersistentState
from .types import ClientRequest, ClientResponse, Message, Role


class Node:
    def __init__(
        self,
        node_id: str,
        peers: list[str],
        storage: MemoryStorage,
        election_timeout: int,
    ) -> None:
        if node_id in peers:
            raise ValueError("peers must not include node_id")
        if election_timeout <= 0:
            raise ValueError("election_timeout must be positive")
        self.node_id = node_id
        self.peers = tuple(peers)
        self.storage = storage
        self.election_timeout = election_timeout
        self.role = Role.FOLLOWER
        self.leader_id: str | None = None
        self.commit_index = storage.load().snapshot.last_included_index if storage.load().snapshot else 0
        self.last_applied = self.commit_index
        self.state_machine: dict[str, Any] = {}
        self.client_sessions: dict[str, Any] = {}
        self.next_index: dict[str, int] = {}
        self.match_index: dict[str, int] = {}
        self._responses: list[ClientResponse] = []
        self._last_contact = 0

    @property
    def persistent(self) -> PersistentState:
        return self.storage.load()

    @property
    def current_term(self) -> int:
        return self.persistent.current_term

    @property
    def last_log_index(self) -> int:
        state = self.persistent
        if state.log:
            return state.log[-1].index
        return state.snapshot.last_included_index if state.snapshot else 0

    @property
    def last_log_term(self) -> int:
        state = self.persistent
        if state.log:
            return state.log[-1].term
        return state.snapshot.last_included_term if state.snapshot else 0

    def tick(self, now: int) -> list[Message]:
        """Apply one timer event and return outgoing messages.

        TODO milestone 1: election timeout, candidate transition, durable term/vote,
        RequestVote messages, heartbeat scheduling and leader step-down.
        """
        raise NotImplementedError("implement election and heartbeat transitions")

    def receive(self, message: Message, now: int) -> list[Message]:
        """Apply one delivered protocol message and return outgoing messages.

        TODO milestones 1, 2 and 6: RequestVote, AppendEntries and
        InstallSnapshot request/response transitions.
        """
        raise NotImplementedError("implement protocol message transitions")

    def submit(
        self,
        request: ClientRequest,
        now: int,
    ) -> tuple[list[Message], ClientResponse | None]:
        """Accept a client operation at the current node.

        TODO milestones 3 and 5: redirect on non-leader, append on leader,
        commit/apply before response and session deduplication.
        """
        raise NotImplementedError("implement client command transitions")

    def drain_responses(self) -> list[ClientResponse]:
        responses = list(self._responses)
        self._responses.clear()
        return responses

    def state_summary(self) -> dict[str, Any]:
        state = self.persistent
        return {
            "node_id": self.node_id,
            "role": self.role.value,
            "leader_id": self.leader_id,
            "current_term": state.current_term,
            "voted_for": state.voted_for,
            "last_log_index": self.last_log_index,
            "last_log_term": self.last_log_term,
            "commit_index": self.commit_index,
            "last_applied": self.last_applied,
            "state_machine": dict(self.state_machine),
        }
