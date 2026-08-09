#!/usr/bin/env python3
"""Bounded three-node election model for persist-before-send evidence.

This model explores two terms, two log-freshness levels, both candidate request
orders, durable/non-durable response branches, and one crash/restart boundary.
It is intentionally smaller than the learner Raft implementation, but its
quorums and counterexample are real model state rather than a declared flag.
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass
import itertools
import json
from typing import Any


NODES = ("A", "B", "C")
CANDIDATES = ("B", "C")
MAJORITY = 2


@dataclass(frozen=True)
class VoteState:
    durable_vote: str | None = None
    volatile_vote: str | None = None
    responses: tuple[str, ...] = ()
    crashes: int = 0


def _majorities(state: VoteState) -> dict[str, tuple[str, ...]]:
    # B and C each start with their own durable self-vote. A's response is the
    # second vote that can create a three-node majority.
    result: dict[str, tuple[str, ...]] = {}
    for candidate in CANDIDATES:
        voters = {candidate}
        if candidate in state.responses:
            voters.add("A")
        result[candidate] = tuple(sorted(voters))
    return result


def _is_dual_majority(state: VoteState) -> bool:
    return sum(len(voters) >= MAJORITY for voters in _majorities(state).values()) > 1


def _transitions(
    state: VoteState,
    *,
    term: int,
    voter_log: int,
    candidate_logs: dict[str, int],
    unsafe_send_before_persist: bool,
) -> list[tuple[VoteState, dict[str, Any]]]:
    transitions: list[tuple[VoteState, dict[str, Any]]] = []
    effective_vote = state.volatile_vote or state.durable_vote
    for candidate in CANDIDATES:
        if candidate in state.responses:
            continue
        if candidate_logs[candidate] < voter_log:
            continue
        if effective_vote not in {None, candidate}:
            continue
        persisted = VoteState(
            durable_vote=candidate,
            volatile_vote=candidate,
            responses=state.responses + (candidate,),
            crashes=state.crashes,
        )
        transitions.append((persisted, {
            "kind": "vote_response",
            "term": term,
            "voter": "A",
            "candidate": candidate,
            "candidate_last_log_term": candidate_logs[candidate],
            "voter_last_log_term": voter_log,
            "durable_before_response": True,
        }))
        if unsafe_send_before_persist and state.durable_vote is None:
            non_durable = VoteState(
                durable_vote=None,
                volatile_vote=candidate,
                responses=state.responses + (candidate,),
                crashes=state.crashes,
            )
            transitions.append((non_durable, {
                "kind": "vote_response",
                "term": term,
                "voter": "A",
                "candidate": candidate,
                "candidate_last_log_term": candidate_logs[candidate],
                "voter_last_log_term": voter_log,
                "durable_before_response": False,
            }))
    if state.volatile_vote is not None and state.crashes == 0:
        restarted = VoteState(
            durable_vote=state.durable_vote,
            volatile_vote=state.durable_vote,
            responses=state.responses,
            crashes=1,
        )
        transitions.append((restarted, {
            "kind": "crash_restart",
            "term": term,
            "voter": "A",
            "durable_vote_after_restart": state.durable_vote,
        }))
    if (
        state.volatile_vote is not None
        and state.durable_vote is None
        and unsafe_send_before_persist
    ):
        persisted_late = VoteState(
            durable_vote=state.volatile_vote,
            volatile_vote=state.volatile_vote,
            responses=state.responses,
            crashes=state.crashes,
        )
        transitions.append((persisted_late, {
            "kind": "late_persist",
            "term": term,
            "voter": "A",
            "candidate": state.volatile_vote,
        }))
    return transitions


def explore(*, unsafe_send_before_persist: bool = False) -> dict[str, Any]:
    explored_states = 0
    stale_requests = 0
    shortest: list[dict[str, Any]] | None = None
    shortest_state: VoteState | None = None
    shortest_bounds: dict[str, Any] | None = None

    for term, voter_log, b_log, c_log in itertools.product((1, 2), (0, 1), (0, 1), (0, 1)):
        candidate_logs = {"B": b_log, "C": c_log}
        stale_requests += sum(value < voter_log for value in candidate_logs.values())
        initial = VoteState()
        queue: deque[tuple[VoteState, list[dict[str, Any]]]] = deque([(initial, [])])
        visited = {initial}
        while queue:
            state, path = queue.popleft()
            explored_states += 1
            if _is_dual_majority(state):
                if shortest is None or len(path) < len(shortest):
                    shortest = path
                    shortest_state = state
                    shortest_bounds = {
                        "term": term,
                        "voter_last_log_term": voter_log,
                        "candidate_last_log_terms": candidate_logs,
                    }
                continue
            for next_state, event in _transitions(
                state,
                term=term,
                voter_log=voter_log,
                candidate_logs=candidate_logs,
                unsafe_send_before_persist=unsafe_send_before_persist,
            ):
                if next_state in visited:
                    continue
                visited.add(next_state)
                queue.append((next_state, path + [event]))

    counterexample = shortest or []
    majorities = _majorities(shortest_state) if shortest_state is not None else {}
    return {
        "schema_version": 1,
        "model": "three-node-bounded-election",
        "nodes": list(NODES),
        "bounds": {
            "terms": [1, 2],
            "last_log_terms": [0, 1],
            "crashes_per_path": 1,
        },
        "unsafe_send_before_persist": unsafe_send_before_persist,
        "explored_states": explored_states,
        "stale_requests_considered": stale_requests,
        "double_vote": shortest_state is not None and len(set(shortest_state.responses)) > 1,
        "dual_majority": shortest_state is not None,
        "majorities": {candidate: list(voters) for candidate, voters in majorities.items()},
        "counterexample": counterexample,
        "counterexample_bounds": shortest_bounds,
        "minimal_counterexample_length": len(counterexample) if counterexample else None,
    }


def main() -> int:
    print(json.dumps({
        "safe": explore(),
        "unsafe": explore(unsafe_send_before_persist=True),
    }, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
