"""Behavioral evidence checks; this is deliberately not a Raft implementation."""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import re
from typing import Any, Callable, Iterable


@dataclass(frozen=True)
class Diagnostic:
    id: str
    step: int | None
    message: str


@dataclass(frozen=True)
class InvariantResult:
    id: str
    ok: bool
    step: int | None
    evidence: str


@dataclass(frozen=True)
class HistoryResult:
    linearizable: bool
    witness: tuple[str, ...]
    reason: str


EVENT_FIELDS = {
    "schema_version", "run_id", "step", "virtual_time", "event_id", "kind",
    "actor", "target", "message_id", "delivery_id", "state_before_hash",
    "state_after_hash", "invariant_results", "details",
}
HASH_RE = re.compile(r"^[0-9a-f]{64}$")
PENDING_POLICIES = {"drop", "complete", "either"}

REQUIRED_SCENARIO_EVIDENCE: dict[str, tuple[str, ...]] = {
    "normal-write-read": ("leaders_by_term", "commit_index", "last_applied", "applied", "history"),
    "split-vote": ("leaders_by_term", "durable_votes", "progress_evidence"),
    "leader-crash": ("leaders_by_term", "logs", "commit_index", "recovery_evidence"),
    "one-way-partition": ("leaders_by_term", "commit_index", "fault_evidence"),
    "response-loss-retry": ("client_effects", "history", "fault_evidence"),
    "slow-follower-snapshot": ("snapshot", "commit_index", "recovery_evidence"),
    "repeated-crash-restart": ("durable_votes", "commit_index", "recovery_evidence"),
}


def _events(trace: dict[str, Any] | list[dict[str, Any]]) -> list[dict[str, Any]]:
    if isinstance(trace, list):
        return trace
    if not isinstance(trace, dict):
        raise ValueError("trace must be an event list or an object")
    events = trace.get("events")
    if not isinstance(events, list):
        raise ValueError("trace object must contain an events list")
    return events


def canonical_trace_digest(trace: dict[str, Any] | list[dict[str, Any]]) -> str:
    encoded = json.dumps(
        trace, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def validate_trace(trace: dict[str, Any] | list[dict[str, Any]]) -> list[Diagnostic]:
    """Validate identity, the canonical 14-field envelope, and its invariants.

    Malformed untrusted evidence is reported as ``TRACE_SCHEMA`` rather than
    escaping as ``KeyError``/``TypeError`` from an invariant checker.
    """

    diagnostics: list[Diagnostic] = []
    top_run_id: str | None = None
    if isinstance(trace, dict):
        if trace.get("schema_version") != 1:
            diagnostics.append(Diagnostic("TRACE_SCHEMA", None, "unsupported top-level schema_version"))
        raw_run_id = trace.get("run_id")
        if not isinstance(raw_run_id, str) or not raw_run_id:
            diagnostics.append(Diagnostic("TRACE_SCHEMA", None, "top-level run_id must be non-empty"))
        else:
            top_run_id = raw_run_id
        scenario_id = trace.get("scenario_id")
        if scenario_id is not None and (not isinstance(scenario_id, str) or not scenario_id):
            diagnostics.append(Diagnostic("TRACE_SCHEMA", None, "scenario_id must be non-empty when present"))
    elif not isinstance(trace, list):
        return [Diagnostic("TRACE_SCHEMA", None, "trace must be an event list or an object")]

    try:
        events = _events(trace)
    except (AttributeError, TypeError, ValueError) as exc:
        diagnostics.append(Diagnostic("TRACE_SCHEMA", None, str(exc)))
        return diagnostics
    if not events:
        diagnostics.append(Diagnostic("TRACE_SCHEMA", None, "trace must contain at least one event"))
        return diagnostics

    event_ids: set[str] = set()
    inferred_run_id: str | None = top_run_id
    previous_step = 0
    previous_time = 0
    previous_after_hash: str | None = None
    safe_events: list[dict[str, Any]] = []
    for position, raw_event in enumerate(events, 1):
        if not isinstance(raw_event, dict):
            diagnostics.append(Diagnostic("TRACE_SCHEMA", None, f"event {position} must be an object"))
            continue
        event = raw_event
        step = event.get("step")
        diagnostic_step = step if isinstance(step, int) and not isinstance(step, bool) else None
        event_ok = True
        if set(event) != EVENT_FIELDS:
            diagnostics.append(Diagnostic(
                "TRACE_SCHEMA", diagnostic_step,
                f"event {position} fields differ: missing={sorted(EVENT_FIELDS - set(event))} "
                f"extra={sorted(set(event) - EVENT_FIELDS)}",
            ))
            event_ok = False
        if event.get("schema_version") != 1:
            diagnostics.append(Diagnostic("TRACE_SCHEMA", diagnostic_step, "unsupported event schema_version"))
            event_ok = False
        event_run_id = event.get("run_id")
        if not isinstance(event_run_id, str) or not event_run_id:
            diagnostics.append(Diagnostic("TRACE_SCHEMA", diagnostic_step, "event run_id must be non-empty"))
            event_ok = False
        elif inferred_run_id is None:
            inferred_run_id = event_run_id
        elif event_run_id != inferred_run_id:
            diagnostics.append(Diagnostic(
                "TRACE_RUN_ID", diagnostic_step,
                f"event run_id {event_run_id!r} differs from trace run_id {inferred_run_id!r}",
            ))
            event_ok = False
        if not isinstance(step, int) or isinstance(step, bool) or step != previous_step + 1:
            diagnostics.append(Diagnostic("TRACE_STEP", diagnostic_step, "steps must be contiguous from 1"))
            event_ok = False
        else:
            previous_step = step
        virtual_time = event.get("virtual_time")
        if (
            not isinstance(virtual_time, int)
            or isinstance(virtual_time, bool)
            or virtual_time < 0
            or virtual_time < previous_time
        ):
            diagnostics.append(Diagnostic("TRACE_TIME", diagnostic_step, "virtual_time must be a monotonic non-negative integer"))
            event_ok = False
        else:
            previous_time = virtual_time
        event_id = event.get("event_id")
        if not isinstance(event_id, str) or not event_id or event_id in event_ids:
            diagnostics.append(Diagnostic("TRACE_EVENT_ID", diagnostic_step, "event_id must be unique and non-empty"))
            event_ok = False
        else:
            event_ids.add(event_id)
        kind = event.get("kind")
        if not isinstance(kind, str) or not kind:
            diagnostics.append(Diagnostic("TRACE_SCHEMA", diagnostic_step, "kind must be non-empty"))
            event_ok = False
        for field in ("actor", "target", "message_id", "delivery_id"):
            value = event.get(field)
            if value is not None and (not isinstance(value, str) or not value):
                diagnostics.append(Diagnostic("TRACE_SCHEMA", diagnostic_step, f"{field} must be null or non-empty string"))
                event_ok = False
        before_hash = event.get("state_before_hash")
        after_hash = event.get("state_after_hash")
        if not isinstance(before_hash, str) or not HASH_RE.fullmatch(before_hash):
            diagnostics.append(Diagnostic("TRACE_HASH", diagnostic_step, "state_before_hash must be lowercase SHA-256"))
            event_ok = False
        if not isinstance(after_hash, str) or not HASH_RE.fullmatch(after_hash):
            diagnostics.append(Diagnostic("TRACE_HASH", diagnostic_step, "state_after_hash must be lowercase SHA-256"))
            event_ok = False
        if previous_after_hash is not None and before_hash != previous_after_hash:
            diagnostics.append(Diagnostic("TRACE_HASH_CHAIN", diagnostic_step, "state hash chain is discontinuous"))
            event_ok = False
        if isinstance(after_hash, str) and HASH_RE.fullmatch(after_hash):
            previous_after_hash = after_hash
        invariant_results = event.get("invariant_results")
        if not isinstance(invariant_results, list):
            diagnostics.append(Diagnostic("TRACE_SCHEMA", diagnostic_step, "invariant_results must be a list"))
            event_ok = False
        details = event.get("details")
        if not isinstance(details, dict):
            diagnostics.append(Diagnostic("TRACE_SCHEMA", diagnostic_step, "details must be an object"))
            event_ok = False
        if event_ok:
            safe_events.append(event)

    if safe_events:
        try:
            diagnostics.extend(
                Diagnostic(result.id, result.step, result.evidence)
                for result in check_invariants(safe_events)
                if not result.ok
            )
        except (KeyError, TypeError, ValueError, AttributeError) as exc:
            diagnostics.append(Diagnostic("TRACE_SCHEMA", None, f"malformed invariant evidence: {exc}"))
    return diagnostics


def check_scenario_evidence(
    trace: dict[str, Any] | list[dict[str, Any]], scenario_id: str
) -> list[Diagnostic]:
    """Require scenario-specific observable evidence, not just a valid envelope."""

    required = REQUIRED_SCENARIO_EVIDENCE.get(scenario_id)
    if required is None:
        return [Diagnostic("SCENARIO_EVIDENCE", None, f"unknown scenario_id: {scenario_id}")]
    try:
        events = _events(trace)
    except (AttributeError, TypeError, ValueError) as exc:
        return [Diagnostic("SCENARIO_EVIDENCE", None, str(exc))]
    evidence: dict[str, list[Any]] = {field: [] for field in required}
    for event in events:
        if isinstance(event, dict) and isinstance(event.get("details"), dict):
            for field in required:
                if field in event["details"]:
                    evidence[field].append(event["details"][field])

    def meaningful(field: str, value: Any) -> bool:
        if field == "history":
            return (
                isinstance(value, dict)
                and isinstance(value.get("operations"), list)
                and bool(value["operations"])
            )
        if isinstance(value, (dict, list, str)):
            return bool(value)
        return value is not None

    missing = [
        field for field, values in evidence.items()
        if not values or not any(meaningful(field, value) for value in values)
    ]
    diagnostics: list[Diagnostic] = []
    if missing:
        diagnostics.append(Diagnostic(
            "SCENARIO_EVIDENCE", None,
            f"scenario {scenario_id} lacks required evidence: {missing}",
        ))
    if isinstance(trace, dict) and trace.get("scenario_id") != scenario_id:
        diagnostics.append(Diagnostic(
            "SCENARIO_ID", None,
            f"trace scenario_id {trace.get('scenario_id')!r} differs from {scenario_id!r}",
        ))
    return diagnostics


def check_invariants(trace: dict[str, Any] | list[dict[str, Any]]) -> list[InvariantResult]:
    results: list[InvariantResult] = []
    votes: dict[tuple[str, int], str] = {}
    leaders_by_term: dict[str, set[str]] = {}
    commits: dict[str, int] = {}
    applied_by_index: dict[int, str] = {}
    effects: set[tuple[str, int]] = set()
    for event in _events(trace):
        if not isinstance(event, dict):
            continue
        step = event.get("step") if isinstance(event.get("step"), int) else None
        details = event.get("details", {})
        if not isinstance(details, dict):
            continue
        leaders_raw = details.get("leaders_by_term", {})
        if leaders_raw is not None and not isinstance(leaders_raw, dict):
            raise ValueError("leaders_by_term must be an object")
        for term, leaders in leaders_raw.items():
            if not isinstance(leaders, list) or not all(isinstance(item, str) and item for item in leaders):
                raise ValueError("leaders_by_term values must be lists of node ids")
            observed = leaders_by_term.setdefault(str(term), set())
            observed.update(leaders)
            ok = len(set(leaders)) <= 1 and len(observed) <= 1
            results.append(InvariantResult(
                "ELECTION_SAFETY", ok, step,
                f"term {term} leaders_seen={sorted(observed)} event_leaders={leaders}",
            ))
        durable_votes = details.get("durable_votes", [])
        if not isinstance(durable_votes, list):
            raise ValueError("durable_votes must be a list")
        for vote in durable_votes:
            if not isinstance(vote, dict) or not {"node", "term", "candidate"} <= set(vote):
                raise ValueError("durable vote requires node, term, and candidate")
            key = (str(vote["node"]), int(vote["term"]))
            candidate = str(vote["candidate"])
            durable = bool(vote.get("durable", False))
            response_sent = bool(vote.get("response_sent", False))
            prior = votes.get(key)
            ok = (prior is None or prior == candidate) and (not response_sent or durable)
            results.append(InvariantResult(
                "DURABLE_ONE_VOTE", ok, step,
                f"node={key[0]} term={key[1]} prior={prior} candidate={candidate} durable={durable}",
            ))
            if durable and prior is None:
                votes[key] = candidate
        logs = details.get("logs")
        if logs is not None and not isinstance(logs, dict):
            raise ValueError("logs must be an object")
        if isinstance(logs, dict):
            node_logs: dict[str, list[dict[str, Any]]] = {}
            for node, entries in logs.items():
                if not isinstance(entries, list) or not all(isinstance(item, dict) for item in entries):
                    raise ValueError("each node log must be a list of entries")
                node_logs[str(node)] = list(entries)
            nodes = sorted(node_logs)
            for offset, left in enumerate(nodes):
                for right in nodes[offset + 1:]:
                    results.append(InvariantResult(
                        "LOG_MATCHING", _logs_match(node_logs[left], node_logs[right]), step,
                        f"compared {left} and {right}",
                    ))
        commit_values = details.get("commit_index", {})
        if commit_values is not None and not isinstance(commit_values, dict):
            raise ValueError("commit_index must be an object")
        for node, value in commit_values.items():
            value = int(value)
            prior = commits.get(str(node), 0)
            results.append(InvariantResult(
                "COMMIT_MONOTONICITY", value >= prior, step,
                f"node={node} previous={prior} current={value}",
            ))
            commits[str(node)] = max(prior, value)
        applied_values = details.get("last_applied", {})
        if applied_values is not None and not isinstance(applied_values, dict):
            raise ValueError("last_applied must be an object")
        for node, value in applied_values.items():
            commit = int(commit_values.get(node, commits.get(str(node), 0)))
            results.append(InvariantResult(
                "APPLY_BOUND", int(value) <= commit, step,
                f"node={node} last_applied={value} commit_index={commit}",
            ))
        applied_items = details.get("applied", [])
        if not isinstance(applied_items, list):
            raise ValueError("applied must be a list")
        for applied in applied_items:
            if not isinstance(applied, dict) or not {"index", "request_hash"} <= set(applied):
                raise ValueError("applied evidence requires index and request_hash")
            index = int(applied["index"])
            request_hash = str(applied["request_hash"])
            prior = applied_by_index.get(index)
            results.append(InvariantResult(
                "STATE_MACHINE_SAFETY", prior is None or prior == request_hash, step,
                f"index={index} prior={prior} current={request_hash}",
            ))
            if prior is None:
                applied_by_index[index] = request_hash
        client_effects = details.get("client_effects", [])
        if not isinstance(client_effects, list):
            raise ValueError("client_effects must be a list")
        for effect in client_effects:
            if not isinstance(effect, dict) or not {"client_id", "sequence"} <= set(effect):
                raise ValueError("client effect requires client_id and sequence")
            key = (str(effect["client_id"]), int(effect["sequence"]))
            count = int(effect.get("count", 1))
            ok = key not in effects and count == 1
            results.append(InvariantResult(
                "AT_MOST_ONCE_EFFECT", ok, step,
                f"client={key[0]} sequence={key[1]} count={count}",
            ))
            effects.add(key)
        snapshot = details.get("snapshot")
        if snapshot is not None and not isinstance(snapshot, dict):
            raise ValueError("snapshot evidence must be an object")
        if isinstance(snapshot, dict):
            results.append(InvariantResult(
                "SNAPSHOT_EQUIVALENCE",
                snapshot.get("state_hash") == snapshot.get("prefix_state_hash")
                and bool(snapshot.get("sessions_preserved", False))
                and bool(snapshot.get("configuration_preserved", False)),
                step, "snapshot state/session/configuration evidence",
            ))
        shard_authority = details.get("shard_authority", {})
        if shard_authority is not None and not isinstance(shard_authority, dict):
            raise ValueError("shard_authority must be an object")
        for epoch, owners in shard_authority.items():
            results.append(InvariantResult(
                "ONE_SHARD_AUTHORITY", isinstance(owners, list) and len(set(owners)) == 1,
                step, f"epoch={epoch} owners={owners}",
            ))
        flag_diagnostics = {
            "old_term_direct_commit": ("CURRENT_TERM_COMMIT", "old-term entry was directly committed"),
            "stale_candidate_granted": ("STALE_CANDIDATE_REJECTED", "a stale candidate received a vote"),
            "response_before_commit": ("RESPONSE_AFTER_APPLY", "client response preceded commit/apply"),
            "prefix_mutated_on_mismatch": ("PREFIX_MISMATCH_NO_MUTATION", "prevLog mismatch mutated the log"),
            "stale_snapshot_rollback": ("STALE_SNAPSHOT_REJECTED", "stale snapshot rolled state backwards"),
        }
        for flag, (diagnostic_id, evidence) in flag_diagnostics.items():
            if details.get(flag) is True:
                results.append(InvariantResult(diagnostic_id, False, step, evidence))
        history = details.get("history")
        if history is not None and not isinstance(history, dict):
            raise ValueError("history must be an object")
        if isinstance(history, dict):
            history_result = check_history(history)
            results.append(InvariantResult(
                "LINEARIZABLE_HISTORY", history_result.linearizable, step, history_result.reason,
            ))
    return results


def _logs_match(left: list[dict[str, Any]], right: list[dict[str, Any]]) -> bool:
    try:
        by_left = {int(entry["index"]): entry for entry in left}
        by_right = {int(entry["index"]): entry for entry in right}
        for index in sorted(set(by_left) & set(by_right)):
            if int(by_left[index]["term"]) != int(by_right[index]["term"]):
                continue
            for prefix in range(1, index + 1):
                if by_left.get(prefix) != by_right.get(prefix):
                    return False
        return True
    except (KeyError, TypeError, ValueError):
        return False


def check_history(
    history: dict[str, Any], spec: str = "kv", pending_policy: str | None = None
) -> HistoryResult:
    """Check a small KV/CAS history under an explicit pending-operation policy.

    ``drop`` ignores pending invocations, ``complete`` uses all pending operations
    with their supplied proposed status/result, and ``either`` explores every
    subset. The latter two are deliberately bounded to twelve pending operations.
    """

    if spec != "kv":
        raise ValueError("only the kv sequential specification is supported")
    if not isinstance(history, dict):
        return HistoryResult(False, (), "history must be an object")
    policy = pending_policy or history.get("pending_policy", "drop")
    if policy not in PENDING_POLICIES:
        return HistoryResult(False, (), f"unsupported pending policy: {policy}")
    raw_operations = history.get("operations", [])
    if not isinstance(raw_operations, list) or not all(isinstance(op, dict) for op in raw_operations):
        return HistoryResult(False, (), "operations must be a list of objects")
    completed = [op for op in raw_operations if op.get("complete") is not None]
    pending = [op for op in raw_operations if op.get("complete") is None]
    if policy == "drop":
        candidates = [completed]
    elif policy == "complete":
        candidates = [completed + pending]
    else:
        if len(pending) > 12:
            return HistoryResult(False, (), "either pending policy is bounded to twelve pending operations")
        candidates = [
            completed + [pending[index] for index in range(len(pending)) if mask & (1 << index)]
            for mask in range(1 << len(pending))
        ]
    reasons: list[str] = []
    for operations in candidates:
        result = _check_completed_history(history.get("initial", {}), operations)
        if result.linearizable:
            suffix = f" under pending_policy={policy}"
            return HistoryResult(True, result.witness, result.reason + suffix)
        reasons.append(result.reason)
    reason = reasons[0] if reasons else "no pending completion choice was legal"
    return HistoryResult(False, (), f"{reason} under pending_policy={policy}")


def _check_completed_history(initial: Any, operations: list[dict[str, Any]]) -> HistoryResult:
    if not isinstance(initial, dict):
        return HistoryResult(False, (), "initial state must be an object")
    try:
        ids = [str(op["id"]) for op in operations]
    except KeyError:
        return HistoryResult(False, (), "each operation requires an id")
    if len(ids) != len(set(ids)):
        return HistoryResult(False, (), "duplicate operation id")
    for op in operations:
        invoke = op.get("invoke")
        complete = op.get("complete")
        if not isinstance(invoke, int) or isinstance(invoke, bool):
            return HistoryResult(False, (), f"operation {op.get('id')} has invalid invoke")
        if complete is not None and (
            not isinstance(complete, int) or isinstance(complete, bool) or complete < invoke
        ):
            return HistoryResult(False, (), f"operation {op.get('id')} has invalid completion")
    predecessors: dict[str, set[str]] = {str(op["id"]): set() for op in operations}
    for left in operations:
        for right in operations:
            if left is right:
                continue
            left_complete = left.get("complete")
            if left_complete is not None and left_complete < right["invoke"]:
                predecessors[str(right["id"])].add(str(left["id"]))
            if left.get("client") == right.get("client") and left["invoke"] < right["invoke"]:
                predecessors[str(right["id"])].add(str(left["id"]))
    by_id = {str(op["id"]): op for op in operations}

    def search(state: dict[str, Any], remaining: set[str], order: list[str]) -> tuple[str, ...] | None:
        if not remaining:
            return tuple(order)
        for operation_id in sorted(remaining):
            if predecessors[operation_id] & remaining:
                continue
            next_state = dict(state)
            if not _apply_operation(next_state, by_id[operation_id]):
                continue
            found = search(next_state, remaining - {operation_id}, order + [operation_id])
            if found is not None:
                return found
        return None

    witness = search(dict(initial), set(by_id), [])
    if witness is None:
        return HistoryResult(False, (), "no legal sequential order preserves real-time and client order")
    return HistoryResult(True, witness, "legal sequential witness found")


def _apply_operation(state: dict[str, Any], operation: dict[str, Any]) -> bool:
    try:
        kind = operation["kind"]
    except KeyError:
        return False
    key = str(operation.get("key", ""))
    status = operation.get("status")
    if kind == "put":
        if status != "OK":
            return False
        state[key] = operation.get("value")
        return True
    if kind == "get":
        if key not in state:
            return status == "NOT_FOUND"
        return status == "OK" and operation.get("result") == state[key]
    if kind == "compare_and_set":
        if state.get(key) == operation.get("expected"):
            if status != "OK":
                return False
            state[key] = operation.get("value")
            return True
        return status == "MISMATCH"
    return False


def check_expected(
    trace: dict[str, Any] | list[dict[str, Any]], expected: dict[str, Any]
) -> list[Diagnostic]:
    actual = validate_trace(trace)
    actual_ids = sorted({item.id for item in actual})
    wanted = sorted(set(expected.get("diagnostic_ids", [])))
    diagnostics: list[Diagnostic] = []
    if actual_ids != wanted:
        diagnostics.append(Diagnostic(
            "EXPECTED_DIAGNOSTICS", None,
            f"expected diagnostic ids {wanted}, got {actual_ids}",
        ))
    digest = expected.get("digest")
    if digest is not None and canonical_trace_digest(trace) != digest:
        diagnostics.append(Diagnostic("EXPECTED_DIGEST", None, "canonical trace digest differs"))
    return diagnostics


def shrink_failure(
    schedule: Iterable[dict[str, Any]],
    predicate: Callable[[list[dict[str, Any]]], bool],
) -> list[dict[str, Any]]:
    current = list(schedule)
    if not predicate(current):
        raise ValueError("the supplied schedule does not reproduce the failure")
    changed = True
    while changed:
        changed = False
        for index in range(len(current)):
            candidate = current[:index] + current[index + 1:]
            if predicate(candidate):
                current = candidate
                changed = True
                break
    return current
