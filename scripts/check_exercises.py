#!/usr/bin/env python3
"""Validate exercise references, expected outcomes, and selected semantics."""
from __future__ import annotations

import argparse
import copy
import itertools
import json
import re
import sys
from pathlib import Path
from typing import Any, Callable


ROOT = Path(__file__).resolve().parents[1]
EXERCISES = ROOT / "exercises"
EXPECTED_SCHEMA = "exercise-expected-v1"
CASE_KINDS = {"normal", "boundary", "failure"}


class CheckError(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise CheckError(message)


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise CheckError(f"cannot parse JSON {path.relative_to(ROOT)}: {exc}") from exc


def resolve_pointer(document: Any, pointer: str) -> Any:
    require(pointer == "" or pointer.startswith("/"), f"invalid JSON pointer: {pointer}")
    current = document
    if not pointer:
        return current
    for raw in pointer[1:].split("/"):
        token = raw.replace("~1", "/").replace("~0", "~")
        if isinstance(current, list):
            require(token.isdigit(), f"list pointer token is not an index: {pointer}")
            index = int(token)
            require(0 <= index < len(current), f"list pointer is out of range: {pointer}")
            current = current[index]
        elif isinstance(current, dict):
            require(token in current, f"object pointer key is missing: {pointer}")
            current = current[token]
        else:
            raise CheckError(f"pointer traverses a scalar value: {pointer}")
    return current


def heading_anchor(raw: str) -> str:
    text = re.sub(r"[^\w\- ]", "", raw.strip().lower(), flags=re.UNICODE)
    return re.sub(r"[\s\-]+", "-", text).strip("-")


def markdown_anchors(path: Path) -> set[str]:
    anchors: set[str] = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        match = re.match(r"^#{1,6}\s+(.+?)\s*#*\s*$", line)
        if match:
            anchors.add(heading_anchor(match.group(1)))
    return anchors


def nonempty_strings(value: Any) -> bool:
    return (
        isinstance(value, list)
        and bool(value)
        and all(isinstance(item, str) and bool(item.strip()) for item in value)
    )


def discover_expected(arguments: list[str]) -> list[Path]:
    if not arguments:
        return sorted(EXERCISES.rglob("expected.json"))

    discovered: set[Path] = set()
    for raw in arguments:
        candidate = Path(raw)
        if not candidate.is_absolute():
            candidate = ROOT / candidate
        candidate = candidate.resolve()
        try:
            candidate.relative_to(EXERCISES.resolve())
        except ValueError as exc:
            raise CheckError(f"path is outside exercises: {raw}") from exc
        if candidate.is_dir():
            discovered.update(candidate.rglob("expected.json"))
        elif candidate.is_file() and candidate.name == "expected.json":
            discovered.add(candidate)
        else:
            raise CheckError(f"path has no expected.json: {raw}")
    return sorted(discovered)


def find_object_with_id(value: Any, target: str) -> dict[str, Any] | None:
    if isinstance(value, dict):
        if value.get("id") == target:
            return value
        for child in value.values():
            found = find_object_with_id(child, target)
            if found is not None:
                return found
    elif isinstance(value, list):
        for child in value:
            found = find_object_with_id(child, target)
            if found is not None:
                return found
    return None


def validate_compact_contract(
    path: Path,
    data: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    relative_dir = path.parent.relative_to(EXERCISES).as_posix()
    require(data.get("schema_version") == 1, f"unsupported schema_version: {path}")
    require(data.get("exercise_id") == relative_dir, f"exercise_id mismatch: {path}")

    readme = path.parent / "README.md"
    reference = path.parent / "reference.md"
    require(readme.is_file(), f"exercise README missing: {relative_dir}")
    require(reference.is_file(), f"exercise reference missing: {relative_dir}")
    readme_text = readme.read_text(encoding="utf-8")
    require("reference.md" in readme_text, f"README does not link reference.md: {relative_dir}")
    require("expected.json" in readme_text, f"README does not link expected.json: {relative_dir}")
    require(markdown_anchors(reference), f"reference has no headings: {relative_dir}")

    checks = data.get("automated_checks")
    require(isinstance(checks, list) and checks, f"automated_checks must be non-empty: {relative_dir}")
    check_ids: set[str] = set()
    fixtures: dict[str, Any] = {}
    derived_prefix = "learner plan derived from "
    for check in checks:
        require(isinstance(check, dict), f"automated check must be an object: {relative_dir}")
        check_id = check.get("id")
        require(isinstance(check_id, str) and check_id, f"automated check id missing: {relative_dir}")
        require(check_id not in check_ids, f"duplicate automated check id {check_id}: {relative_dir}")
        check_ids.add(check_id)
        require(
            isinstance(check.get("observation"), str) and check["observation"].strip(),
            f"observation missing for {check_id}",
        )
        require("expected" in check and check["expected"] is not None, f"expected value missing for {check_id}")

        fixture_spec = check.get("fixture")
        require(isinstance(fixture_spec, str) and fixture_spec, f"fixture missing for {check_id}")
        selector = ""
        if fixture_spec.startswith(derived_prefix):
            fixture_name = fixture_spec[len(derived_prefix):]
        else:
            fixture_name, separator, selector = fixture_spec.partition("#")
            if not separator:
                selector = ""
        fixture_path = (path.parent / fixture_name).resolve()
        try:
            fixture_path.relative_to(path.parent.resolve())
        except ValueError as exc:
            raise CheckError(f"fixture escapes exercise directory: {fixture_spec}") from exc
        require(fixture_path.is_file(), f"fixture does not exist for {check_id}: {fixture_name}")
        if fixture_name not in fixtures:
            fixture = load_json(fixture_path)
            require(
                not isinstance(fixture, dict) or fixture.get("schema_version") == 1,
                f"fixture schema_version must be 1: {fixture_name}",
            )
            fixtures[fixture_name] = fixture

        if selector:
            selector_parts = selector.split("/")
            selected = find_object_with_id(fixtures[fixture_name], selector_parts[0])
            require(selected is not None, f"fixture selector is missing for {check_id}: {selector_parts[0]}")
            for detail in selector_parts[1:]:
                range_match = re.fullmatch(r"([A-Za-z]+\d+)-([A-Za-z]+\d+)", detail)
                targets = range_match.groups() if range_match else (detail,)
                for target in targets:
                    require(
                        find_object_with_id(selected, target) is not None,
                        f"fixture detail selector is missing for {check_id}: {target}",
                    )

    reviews = data.get("manual_review")
    require(isinstance(reviews, list) and reviews, f"manual_review must be non-empty: {relative_dir}")
    review_ids: set[str] = set()
    for review in reviews:
        require(isinstance(review, dict), f"manual review must be an object: {relative_dir}")
        review_id = review.get("id")
        require(isinstance(review_id, str) and review_id, f"manual review id missing: {relative_dir}")
        require(review_id not in review_ids, f"duplicate manual review id {review_id}: {relative_dir}")
        review_ids.add(review_id)
        require(
            isinstance(review.get("question"), str) and review["question"].strip(),
            f"manual review question missing for {review_id}",
        )
        require(
            nonempty_strings(review.get("required_evidence")),
            f"manual review evidence missing for {review_id}",
        )
    require(nonempty_strings(data.get("limits")), f"limits must be non-empty: {relative_dir}")
    return data, fixtures


def validate_generic(path: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    data = load_json(path)
    require(isinstance(data, dict), f"expected root must be an object: {path}")
    if data.get("guide_schema") is None and "automated_checks" in data:
        return validate_compact_contract(path, data)
    require(data.get("guide_schema") == EXPECTED_SCHEMA, f"unsupported guide_schema: {path}")
    require(data.get("schema_version") == 1, f"unsupported schema_version: {path}")

    relative_dir = path.parent.relative_to(EXERCISES).as_posix()
    require(data.get("exercise_id") == relative_dir, f"exercise_id mismatch: {path}")

    readme = path.parent / "README.md"
    reference = path.parent / "reference.md"
    require(readme.is_file(), f"exercise README missing: {relative_dir}")
    require(reference.is_file(), f"exercise reference missing: {relative_dir}")
    readme_text = readme.read_text(encoding="utf-8")
    require("reference.md" in readme_text, f"README does not link reference.md: {relative_dir}")
    require("expected.json" in readme_text, f"README does not link expected.json: {relative_dir}")
    anchors = markdown_anchors(reference)

    cases = data.get("cases")
    require(isinstance(cases, list) and cases, f"expected cases must be non-empty: {relative_dir}")
    case_ids: set[str] = set()
    kinds: set[str] = set()
    fixtures: dict[str, Any] = {}

    for case in cases:
        require(isinstance(case, dict), f"case must be an object: {relative_dir}")
        case_id = case.get("id")
        require(isinstance(case_id, str) and case_id, f"case id missing: {relative_dir}")
        require(case_id not in case_ids, f"duplicate case id {case_id}: {relative_dir}")
        case_ids.add(case_id)

        kind = case.get("kind")
        require(kind in CASE_KINDS, f"invalid kind for {case_id}: {kind}")
        kinds.add(kind)

        fixture_name = case.get("fixture")
        require(isinstance(fixture_name, str) and fixture_name, f"fixture missing for {case_id}")
        fixture_path = (path.parent / fixture_name).resolve()
        try:
            fixture_path.relative_to(path.parent.resolve())
        except ValueError as exc:
            raise CheckError(f"fixture escapes exercise directory: {fixture_name}") from exc
        require(fixture_path.is_file(), f"fixture does not exist for {case_id}: {fixture_name}")
        if fixture_name not in fixtures:
            fixture = load_json(fixture_path)
            require(
                not isinstance(fixture, dict) or fixture.get("schema_version") == 1,
                f"fixture schema_version must be 1: {fixture_name}",
            )
            fixtures[fixture_name] = fixture
        source = resolve_pointer(fixtures[fixture_name], case.get("source_path", ""))
        if isinstance(source, dict) and "id" in source:
            require(source["id"] == case_id, f"source id mismatch for {case_id}")

        anchor = case.get("reference_anchor")
        require(isinstance(anchor, str) and anchor, f"reference_anchor missing for {case_id}")
        require(anchor in anchors, f"reference heading is missing for {case_id}: #{anchor}")
        require(isinstance(case.get("outcome"), dict) and case["outcome"], f"outcome missing for {case_id}")
        require(nonempty_strings(case.get("human_evidence")), f"human_evidence missing for {case_id}")
        require(nonempty_strings(case.get("limits")), f"limits missing for {case_id}")

    required_kinds = data.get("required_case_kinds")
    require(
        isinstance(required_kinds, list)
        and all(kind in CASE_KINDS for kind in required_kinds),
        f"invalid required_case_kinds: {relative_dir}",
    )
    missing_kinds = set(required_kinds) - kinds
    require(not missing_kinds, f"missing required case kinds {sorted(missing_kinds)}: {relative_dir}")
    return data, fixtures


def case_map(expected: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {case["id"]: case for case in expected["cases"]}


def vector_relation(left: dict[str, int], right: dict[str, int]) -> str:
    keys = set(left) | set(right)
    left_le = all(int(left.get(key, 0)) <= int(right.get(key, 0)) for key in keys)
    right_le = all(int(right.get(key, 0)) <= int(left.get(key, 0)) for key in keys)
    if left_le and right_le:
        return "equal"
    if right_le:
        return "left-dominates"
    if left_le:
        return "right-dominates"
    return "concurrent"


def validate_causality(expected: dict[str, Any], fixtures: dict[str, Any]) -> None:
    trace = fixtures["trace.json"]
    processes = list(trace["processes"])
    lamport = {process: 0 for process in processes}
    vectors = {process: {item: 0 for item in processes} for process in processes}
    messages: dict[str, tuple[int, dict[str, int], str]] = {}
    clocks: dict[str, dict[str, Any]] = {}
    last_event: dict[str, str] = {}
    direct_edges: set[tuple[str, str]] = set()

    for event in trace["events"]:
        event_id = event["id"]
        process = event["process"]
        require(process in lamport, f"unknown process in causality fixture: {process}")
        if process in last_event:
            direct_edges.add((last_event[process], event_id))
        last_event[process] = event_id

        if event["kind"] == "receive":
            message_id = event["message"]
            require(message_id in messages, f"receive before send: {message_id}")
            sent_lamport, sent_vector, send_id = messages[message_id]
            lamport[process] = max(lamport[process], sent_lamport) + 1
            for item in processes:
                vectors[process][item] = max(vectors[process][item], sent_vector[item])
            vectors[process][process] += 1
            direct_edges.add((send_id, event_id))
        else:
            lamport[process] += 1
            vectors[process][process] += 1

        clocks[event_id] = {
            "lamport": lamport[process],
            "vector": dict(vectors[process]),
        }
        if event["kind"] == "send":
            messages[event["message"]] = (
                lamport[process],
                dict(vectors[process]),
                event_id,
            )

    cases = case_map(expected)
    clock_outcome = cases["clock-and-order"]["outcome"]
    require(clock_outcome["event_clocks"] == clocks, "causality event clocks differ from expected")
    expected_edges = {tuple(edge) for edge in clock_outcome["direct_edges"]}
    require(expected_edges == direct_edges, "causality direct edges differ from expected")

    adjacency: dict[str, set[str]] = {event["id"]: set() for event in trace["events"]}
    for source, target in direct_edges:
        adjacency[source].add(target)

    def reaches(source: str, target: str) -> bool:
        pending = list(adjacency[source])
        seen: set[str] = set()
        while pending:
            current = pending.pop()
            if current == target:
                return True
            if current not in seen:
                seen.add(current)
                pending.extend(adjacency[current])
        return False

    pairs = clock_outcome["concurrent_pairs"]
    require(len(pairs) >= 5, "causality expected data must expose at least five concurrent pairs")
    for left, right in pairs:
        require(not reaches(left, right) and not reaches(right, left), f"pair is not concurrent: {left},{right}")
        left_vector = clocks[left]["vector"]
        right_vector = clocks[right]["vector"]
        require(vector_relation(left_vector, right_vector) == "concurrent", f"vectors are comparable: {left},{right}")

    def missing_edges(included: set[str]) -> set[tuple[str, str]]:
        return {
            (source, target)
            for source, target in direct_edges
            if target in included and source not in included
        }

    for cut_id in ("cut-1", "cut-2"):
        included = set(trace["candidate_cuts"][cut_id])
        missing = missing_edges(included)
        outcome = cases[cut_id]["outcome"]
        require(outcome["consistent"] is (not missing), f"cut classification mismatch: {cut_id}")
        expected_missing = {tuple(edge) for edge in outcome["missing_predecessors"]}
        require(expected_missing == missing, f"cut predecessor mismatch: {cut_id}")
        for repair in outcome["minimal_repairs"]:
            modified = set(included)
            if repair["action"] == "add":
                modified.update(repair["events"])
            elif repair["action"] == "remove":
                modified.difference_update(repair["events"])
            else:
                raise CheckError(f"unknown cut repair action: {repair['action']}")
            require(not missing_edges(modified), f"cut repair is not consistent: {cut_id}")


def validate_failure_model(expected: dict[str, Any], fixtures: dict[str, Any]) -> None:
    fixture_cases = {item["id"]: item for item in fixtures["scenarios.json"]["scenarios"]}
    expected_classes = {
        "slow-or-crashed": "suspicion-only",
        "vote-before-persist": "unsafe-durable-promise",
        "partitioned-register": "availability-consistency-conflict",
        "crash-recovery-log": "durability-contract-violation",
    }
    require(set(fixture_cases) == set(expected_classes), "failure-model scenario set changed")
    for case_id, classification in expected_classes.items():
        outcome = case_map(expected)[case_id]["outcome"]
        require(outcome["classification"] == classification, f"failure-model classification mismatch: {case_id}")
        events = fixture_cases[case_id]["events"]
        require(isinstance(events, list) and len(events) >= 3, f"failure-model trace is too small: {case_id}")


def operation_key(operation: dict[str, Any]) -> str | None:
    return operation.get("key")


def apply_operation(state: Any, operation: dict[str, Any]) -> tuple[bool, Any]:
    next_state = copy.deepcopy(state)
    key = operation_key(operation)
    if isinstance(next_state, dict):
        require(key is not None, f"multi-register operation has no key: {operation['id']}")
        current = next_state[key]
    else:
        current = next_state

    if operation["op"] == "read":
        return operation.get("result") == current, next_state
    if operation["op"] == "write":
        if operation.get("result") not in ("OK", None):
            return False, next_state
        if isinstance(next_state, dict):
            next_state[key] = operation["value"]
        else:
            next_state = operation["value"]
        return True, next_state
    raise CheckError(f"unsupported consistency operation: {operation['op']}")


def search_history(
    history: dict[str, Any],
    initial: Any,
    *,
    real_time: bool,
) -> tuple[list[str] | None, list[str]]:
    completed = [copy.deepcopy(item) for item in history["operations"] if item.get("complete") is not None]
    pending = [copy.deepcopy(item) for item in history["operations"] if item.get("complete") is None and item["op"] == "write"]

    for count in range(len(pending) + 1):
        for selected in itertools.combinations(pending, count):
            selected_ids = [item["id"] for item in selected]
            selected_ops = []
            for item in selected:
                operation = copy.deepcopy(item)
                operation["result"] = "OK"
                selected_ops.append(operation)
            operations = completed + selected_ops
            predecessors = {item["id"]: set() for item in operations}

            by_process: dict[str, list[dict[str, Any]]] = {}
            for item in operations:
                by_process.setdefault(item["process"], []).append(item)
            for process_ops in by_process.values():
                ordered = sorted(process_ops, key=lambda item: (item["invoke"], item["id"]))
                for left, right in zip(ordered, ordered[1:]):
                    predecessors[right["id"]].add(left["id"])

            if real_time:
                for left in operations:
                    for right in operations:
                        if left["id"] == right["id"]:
                            continue
                        if left.get("complete") is not None and left["complete"] < right["invoke"]:
                            predecessors[right["id"]].add(left["id"])

            memo: set[tuple[frozenset[str], str]] = set()

            def walk(done: frozenset[str], state: Any, order: list[str]) -> list[str] | None:
                memo_key = (done, json.dumps(state, ensure_ascii=False, sort_keys=True))
                if memo_key in memo:
                    return None
                memo.add(memo_key)
                if len(done) == len(operations):
                    return list(order)
                ready = [
                    item
                    for item in operations
                    if item["id"] not in done and predecessors[item["id"]].issubset(done)
                ]
                ready.sort(key=lambda item: (item["invoke"], item["id"]))
                for item in ready:
                    valid, next_state = apply_operation(state, item)
                    if valid:
                        witness = walk(done | {item["id"]}, next_state, order + [item["id"]])
                        if witness is not None:
                            return witness
                return None

            witness = walk(frozenset(), copy.deepcopy(initial), [])
            if witness is not None:
                return witness, selected_ids
    return None, []


def validate_consistency_history(expected: dict[str, Any], fixtures: dict[str, Any]) -> None:
    fixture = fixtures["histories.json"]
    histories = {item["id"]: item for item in fixture["histories"]}
    expected_cases = case_map(expected)
    require(set(histories) == set(expected_cases), "consistency history set differs from expected")
    expected_causal = {"h1": True, "h2": True, "h3": True, "h4": True, "h5": False, "h6": True}

    for history_id, history in histories.items():
        initial = history.get("object", fixture["object"])["initial"]
        linear_witness, linear_pending = search_history(history, initial, real_time=True)
        sequential_witness, sequential_pending = search_history(history, initial, real_time=False)
        outcome = expected_cases[history_id]["outcome"]
        require(outcome["linearizable"] is (linear_witness is not None), f"linearizability mismatch: {history_id}")
        require(
            outcome["sequentially_consistent"] is (sequential_witness is not None),
            f"sequential consistency mismatch: {history_id}",
        )
        require(outcome["causal_consistent"] is expected_causal[history_id], f"causal classification mismatch: {history_id}")
        chosen_witness = linear_witness if linear_witness is not None else sequential_witness
        chosen_pending = linear_pending if linear_witness is not None else sequential_pending
        require(outcome["witness"] == chosen_witness, f"history witness mismatch: {history_id}")
        require(outcome["included_pending"] == chosen_pending, f"pending policy mismatch: {history_id}")


def validate_quorum_register(expected: dict[str, Any], fixtures: dict[str, Any]) -> None:
    scenarios = {item["id"]: item for item in fixtures["topology.json"]["scenarios"]}
    cases = case_map(expected)
    require(set(scenarios) == set(cases), "quorum scenario set differs from expected")

    q1 = scenarios["q1"]
    write_set = set(q1["writes"][0]["acks"])
    read_set = set(q1["read_responses"])
    q1_outcome = cases["q1"]["outcome"]
    require(sorted(write_set & read_set) == q1_outcome["write_read_intersection"], "q1 intersection mismatch")
    versions = list(q1["read_responses"].values())
    selected = max(versions, key=lambda item: sum(int(value) for value in item["version"].values()))
    for candidate in versions:
        require(
            vector_relation(selected["version"], candidate["version"]) in {"left-dominates", "equal"},
            "q1 selected version does not dominate a response",
        )
    require(selected["value"] == q1_outcome["selected_value"], "q1 selected value mismatch")
    repair_targets = sorted(
        replica
        for replica, value in q1["read_responses"].items()
        if value["version"] != selected["version"]
    )
    require(repair_targets == q1_outcome["repair_targets"], "q1 repair targets mismatch")

    q2 = scenarios["q2"]
    left, right = q2["writes"]
    relation = vector_relation(left["version"], right["version"])
    require(relation == cases["q2"]["outcome"]["version_relation"], "q2 vector relation mismatch")
    require(sorted([left["value"], right["value"]]) == cases["q2"]["outcome"]["required_values"], "q2 siblings mismatch")

    q3 = scenarios["q3-sloppy"]
    actual_intersection = sorted(set(q3["write_1_actual"]) & set(q3["write_2_actual"]))
    require(actual_intersection == cases["q3-sloppy"]["outcome"]["actual_write_intersection"], "q3 intersection mismatch")

    q4 = scenarios["q4-membership"]
    old_new = sorted(set(q4["old"]["replicas"]) & set(q4["new"]["replicas"]))
    require(old_new == cases["q4-membership"]["outcome"]["old_new_replica_intersection"], "q4 membership mismatch")


def validate_failure_detector(expected: dict[str, Any], fixtures: dict[str, Any]) -> None:
    fixture = fixtures["observations.json"]
    timeout = int(fixture["detector"]["timeout_ticks"])
    cases = case_map(expected)
    fixture_cases = {item["id"]: item for item in fixture["cases"]}
    require(set(cases) == set(fixture_cases), "failure-detector case set differs from expected")

    for case_id, scenario in fixture_cases.items():
        state = copy.deepcopy(scenario["initial"])
        suspicions: list[str] = []
        first_violation: str | None = None
        for event in scenario["events"]:
            if event["kind"] == "tick":
                if event["step"] - state["last_heartbeat_step"] >= timeout:
                    state["status"] = "SUSPECT"
                    suspicions.append(event["id"])
            elif event["kind"] == "mark_suspect":
                state["status"] = "SUSPECT"
                suspicions.append(event["id"])
            elif event["kind"] == "heartbeat":
                if event["incarnation"] == state["incarnation"]:
                    state["last_heartbeat_step"] = event["step"]
                    state["status"] = "ALIVE"
            elif event["kind"] == "irreversible_remove":
                if event.get("evidence") == ["heartbeat-timeout"] and first_violation is None:
                    first_violation = event["id"]

        outcome = cases[case_id]["outcome"]
        require(state["status"] == outcome["final_status"], f"detector final status mismatch: {case_id}")
        require(
            state["last_heartbeat_step"] == outcome["last_heartbeat_step"],
            f"detector heartbeat frontier mismatch: {case_id}",
        )
        require(suspicions == outcome["suspicion_events"], f"detector suspicion trace mismatch: {case_id}")
        if "first_contract_violation" in outcome:
            require(first_violation == outcome["first_contract_violation"], f"detector violation mismatch: {case_id}")
        else:
            require(first_violation is None, f"unexpected detector violation: {case_id}")


def validate_anti_entropy(expected: dict[str, Any], fixtures: dict[str, Any]) -> None:
    fixture_cases = {item["id"]: item for item in fixtures["repairs.json"]["cases"]}
    cases = case_map(expected)
    require(set(cases) == set(fixture_cases), "anti-entropy case set differs from expected")

    normal = fixture_cases["dominant-repair"]
    source = normal["initial"]["A"][0]
    target = normal["initial"]["C"][0]
    relation = vector_relation(source["version"], target["version"])
    require(relation == "left-dominates", "dominant repair source does not dominate target")
    normal_outcome = cases["dominant-repair"]["outcome"]
    require(normal_outcome["version_relation"] == "source-dominates-target", "dominant repair relation mismatch")
    final_normal = {replica: [source["value"]] for replica in fixtures["repairs.json"]["replicas"]}
    require(final_normal == normal_outcome["final_values"], "dominant repair final state mismatch")

    boundary = fixture_cases["concurrent-siblings"]
    left = boundary["initial"]["A"][0]
    right = boundary["initial"]["B"][0]
    relation = vector_relation(left["version"], right["version"])
    boundary_outcome = cases["concurrent-siblings"]["outcome"]
    require(relation == boundary_outcome["version_relation"], "anti-entropy sibling relation mismatch")
    siblings = sorted([left["value"], right["value"]])
    require(siblings == boundary_outcome["required_siblings"], "anti-entropy sibling values mismatch")
    expected_final = {replica: siblings for replica in fixtures["repairs.json"]["replicas"]}
    require(expected_final == boundary_outcome["final_values"], "anti-entropy sibling convergence mismatch")

    failure = fixture_cases["tombstone-resurrection"]
    tombstone = failure["initial"]["A"][0]
    stale = failure["initial"]["C"][0]
    require(vector_relation(tombstone["version"], stale["version"]) == "left-dominates", "tombstone does not dominate stale value")
    gc_event = next(event for event in failure["events"] if event["kind"] == "gc_tombstone")
    repair_event = next(event for event in failure["events"] if event["kind"] == "repair_from")
    failure_outcome = cases["tombstone-resurrection"]["outcome"]
    require(gc_event["id"] == failure_outcome["first_contract_violation"], "unsafe tombstone GC point mismatch")
    require(gc_event["evidence"] == failure_outcome["unsafe_gc_evidence"], "unsafe GC evidence mismatch")
    require(repair_event["id"] == failure_outcome["resurrection_event"], "resurrection event mismatch")


def compact_expected_map(expected: dict[str, Any]) -> dict[str, Any]:
    return {
        check["id"]: check["expected"]
        for check in expected["automated_checks"]
    }


def compare_compact_observations(
    expected: dict[str, Any],
    actual: dict[str, Any],
) -> None:
    declared = compact_expected_map(expected)
    require(
        set(actual) == set(declared),
        f"semantic checker coverage differs for {expected['exercise_id']}: "
        f"missing={sorted(set(declared) - set(actual))} "
        f"extra={sorted(set(actual) - set(declared))}",
    )
    for check_id, expected_value in declared.items():
        require(
            actual[check_id] == expected_value,
            f"semantic observation mismatch for {expected['exercise_id']}#{check_id}: "
            f"expected={expected_value!r} actual={actual[check_id]!r}",
        )


def last_log_position(node: dict[str, Any]) -> tuple[int, int]:
    terms = node["log_terms"]
    return (int(terms[-1]) if terms else 0, len(terms))


def validate_election_trace(expected: dict[str, Any], fixtures: dict[str, Any]) -> None:
    fixture = fixtures["election.json"]
    quorum = len(fixture["cluster"]) // 2 + 1
    scenarios = {item["id"]: item for item in fixture["scenarios"]}

    stale = scenarios["stale-candidate"]
    candidate = next(event["node"] for event in stale["events"] if event["kind"] == "timeout")
    timeout = next(event for event in stale["events"] if event["kind"] == "timeout")
    candidate_position = last_log_position(stale["initial"][candidate])
    granted = [candidate]
    rejected: list[str] = []
    for event in stale["events"]:
        if event["kind"] != "deliver_request_vote":
            continue
        voter = event["to"]
        advertised = (int(event["last_log_term"]), int(event["last_log_index"]))
        if advertised >= last_log_position(stale["initial"][voter]):
            granted.append(voter)
        else:
            rejected.append(voter)

    split = scenarios["split-vote-and-retry"]
    node_state = {
        node_id: {
            "current_term": int(state["current_term"]),
            "voted_for": state["voted_for"],
            "position": last_log_position(state),
        }
        for node_id, state in split["initial"].items()
    }
    votes: dict[tuple[str, int], set[str]] = {}
    term_nine_snapshot: dict[str, Any] | None = None
    minimum_quorum_event: str | None = None
    elected: str | None = None
    elected_term: int | None = None
    for event in split["events"]:
        if event["id"] == "e7":
            term_nine_leaders = sorted(
                candidate_id
                for (candidate_id, term), candidate_votes in votes.items()
                if term == 9 and len(candidate_votes) >= quorum
            )
            term_nine_uncommitted = sorted(
                node_id
                for node_id, state in node_state.items()
                if state["current_term"] <= 9 and state["voted_for"] is None
            )
            term_nine_snapshot = {
                "A": sorted(votes.get(("A", 9), set())),
                "D": sorted(votes.get(("D", 9), set())),
                "uncommitted_voter": term_nine_uncommitted[0] if len(term_nine_uncommitted) == 1 else None,
                "leader": term_nine_leaders[0] if len(term_nine_leaders) == 1 else None,
            }
        kind = event["kind"]
        if kind == "timeout":
            node_id = event["node"]
            term = int(event["next_term"])
            node_state[node_id]["current_term"] = term
            node_state[node_id]["voted_for"] = node_id
            votes.setdefault((node_id, term), set()).add(node_id)
        elif kind == "deliver_request_vote":
            voter = event["to"]
            candidate_id = event["from"]
            term = int(event["term"])
            state = node_state[voter]
            if term > state["current_term"]:
                state["current_term"] = term
                state["voted_for"] = None
            advertised = (int(event["last_log_term"]), int(event["last_log_index"]))
            if (
                term == state["current_term"]
                and state["voted_for"] in (None, candidate_id)
                and advertised >= state["position"]
            ):
                state["voted_for"] = candidate_id
                candidate_votes = votes.setdefault((candidate_id, term), set())
                candidate_votes.add(voter)
                if len(candidate_votes) >= quorum and minimum_quorum_event is None:
                    minimum_quorum_event = event["id"]
                    elected = candidate_id
                    elected_term = term
        elif kind == "drop_request_vote":
            continue
        else:
            raise CheckError(f"unknown split-vote event: {kind}")
    require(term_nine_snapshot is not None, "split-vote fixture has no retry boundary")

    unsafe = scenarios["vote-before-persist"]
    promised_votes: dict[tuple[str, int], set[str]] = {}
    unsafe_voter_history: dict[tuple[str, int], str] = {}
    first_violation: str | None = None
    for event in unsafe["events"]:
        kind = event["kind"]
        if kind == "timeout":
            candidate_id = event["node"]
            term = int(event["next_term"])
            promised_votes.setdefault((candidate_id, term), set()).add(candidate_id)
        elif kind == "send_vote_response_before_persist" and event.get("granted"):
            voter = event["from"]
            candidate_id = event["to"]
            term = 7
            unsafe_voter_history[(voter, term)] = candidate_id
            promised_votes.setdefault((candidate_id, term), set()).add(voter)
        elif kind == "deliver_request_vote":
            candidate_id = event["from"]
            voter = event["to"]
            term = int(event["term"])
            prior = unsafe_voter_history.get((voter, term))
            if prior is not None and prior != candidate_id and first_violation is None:
                first_violation = event["id"]
            unsafe_voter_history[(voter, term)] = candidate_id
            promised_votes.setdefault((candidate_id, term), set()).add(voter)
    possible_leaders = sorted(
        candidate_id
        for (candidate_id, term), voters in promised_votes.items()
        if term == 7 and len(voters) >= quorum
    )

    actual = {
        "cluster-quorum": quorum,
        "stale-candidate": {
            "candidate": candidate,
            "term": int(timeout["next_term"]),
            "granted_by": sorted(granted),
            "rejected_by": sorted(rejected),
            "leader": candidate if len(granted) >= quorum else None,
        },
        "split-vote-term-9": term_nine_snapshot,
        "retry-term-10": {
            "leader": elected,
            "term": elected_term,
            "minimum_quorum_reached_at": minimum_quorum_event,
        },
        "unsafe-double-vote": {
            "node": "A",
            "term": 7,
            "first_violation_event": first_violation,
            "possible_leaders": possible_leaders,
        },
    }
    compare_compact_observations(expected, actual)


def append_matches(log: list[dict[str, Any]], index: int, term: int) -> bool:
    if index == 0:
        return True
    return any(int(entry["index"]) == index and int(entry["term"]) == term for entry in log)


def validate_log_reconciliation(expected: dict[str, Any], fixtures: dict[str, Any]) -> None:
    fixture = fixtures["logs.json"]
    scenarios = {item["id"]: item for item in fixture["scenarios"]}
    conflict = scenarios["conflicting-suffix"]
    follower_log = copy.deepcopy(conflict["follower"]["log"])
    results: dict[str, bool] = {}
    for attempt in conflict["attempts"]:
        success = append_matches(
            follower_log,
            int(attempt["prev_log_index"]),
            int(attempt["prev_log_term"]),
        )
        results[attempt["id"]] = success
        if not success:
            continue
        for incoming in attempt["entries"]:
            index = int(incoming["index"])
            existing = next(
                (entry for entry in follower_log if int(entry["index"]) == index),
                None,
            )
            if existing is not None and int(existing["term"]) != int(incoming["term"]):
                follower_log = [entry for entry in follower_log if int(entry["index"]) < index]
                existing = None
            if existing is None:
                follower_log.append(copy.deepcopy(incoming))
    final_index = int(follower_log[-1]["index"])

    current_term = scenarios["old-term-majority"]
    cluster_size = len(current_term["cluster"])
    majority = cluster_size // 2 + 1
    terms = {int(entry["index"]): int(entry["term"]) for entry in current_term["log"]}
    commits: dict[str, int] = {}
    for state in current_term["states"]:
        commit = int(state["leader_commit_before"])
        for index in sorted(terms):
            replicated = sum(int(value) >= index for value in state["match_index"].values())
            if replicated >= majority and terms[index] == int(current_term["current_term"]):
                commit = max(commit, index)
        commits[state["id"]] = commit

    actual = {
        "append-attempt-results": results,
        "reconciled-log": {
            "terms": [int(entry["term"]) for entry in follower_log],
            "match_index": final_index,
            "next_index": final_index + 1,
        },
        "old-term-not-directly-committed": commits["s1"],
        "current-term-entry-commits-prefix": commits["s2"],
    }
    compare_compact_observations(expected, actual)


def run_session_scenario(
    initial: dict[str, Any],
    scenario: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    counter = int(initial["counter"])
    sessions = copy.deepcopy(initial.get("client_sessions", {}))
    snapshot: dict[str, Any] | None = None
    observations: dict[str, dict[str, Any]] = {}

    for event in scenario["events"]:
        event_id = event["id"]
        kind = event["kind"]
        status: str | None = None
        result: Any = None
        effects = 0
        if kind == "commit_and_apply":
            counter += int(event["amount"])
            effects = 1
            result = counter
            sessions[event["client_id"]] = {
                "last_sequence": int(event["sequence"]),
                "last_fingerprint": event["fingerprint"],
                "last_result": result,
            }
            status = "OK"
        elif kind in {"retry", "conflicting_retry", "gap_request"}:
            client_id = event["client_id"]
            sequence = int(event["sequence"])
            session = sessions.get(client_id)
            if session is None:
                # The unsafe fixture models the implementation that lost its
                # deduplication record and therefore treats the retry as new.
                counter += int(event["amount"])
                effects = 1
                result = counter
                sessions[client_id] = {
                    "last_sequence": sequence,
                    "last_fingerprint": event["fingerprint"],
                    "last_result": result,
                }
                status = "OK"
            elif sequence == int(session["last_sequence"]):
                if event["fingerprint"] == session["last_fingerprint"]:
                    result = session["last_result"]
                    status = "OK"
                else:
                    status = "SEQUENCE_CONFLICT"
            elif sequence > int(session["last_sequence"]) + 1:
                status = "SEQUENCE_GAP"
            elif sequence < int(session["last_sequence"]):
                status = "STALE_SEQUENCE"
            else:
                counter += int(event["amount"])
                effects = 1
                result = counter
                sessions[client_id] = {
                    "last_sequence": sequence,
                    "last_fingerprint": event["fingerprint"],
                    "last_result": result,
                }
                status = "OK"
        elif kind == "create_snapshot":
            snapshot = {"counter": counter, "client_sessions": {}}
            if "client_sessions" in scenario["snapshot_includes"]:
                snapshot["client_sessions"] = copy.deepcopy(sessions)
        elif kind == "restart_from_snapshot":
            require(snapshot is not None, f"restart has no snapshot: {scenario['id']}")
            counter = int(snapshot["counter"])
            sessions = copy.deepcopy(snapshot["client_sessions"])
        elif kind in {"lose_response", "crash"}:
            pass
        else:
            raise CheckError(f"unknown session event: {kind}")
        observations[event_id] = {
            "counter": counter,
            "sessions": copy.deepcopy(sessions),
            "status": status,
            "result": result,
            "additional_effects": effects,
        }
    return observations


def validate_client_session(expected: dict[str, Any], fixtures: dict[str, Any]) -> None:
    fixture = fixtures["sessions.json"]
    initial = fixture["sequential_spec"]["initial"]
    scenarios = {item["id"]: item for item in fixture["scenarios"]}
    safe = run_session_scenario(initial, scenarios["safe-snapshot"])
    unsafe = run_session_scenario(initial, scenarios["unsafe-snapshot"])
    first_safe_event = scenarios["safe-snapshot"]["events"][0]
    initial_session = initial["client_sessions"][fixture["client"]]

    actual = {
        "initial-session-contiguous": {
            "initial_last_sequence": int(initial_session["last_sequence"]),
            "first_sequence": int(first_safe_event["sequence"]),
        },
        "safe-duplicate-sequence-3": {
            "counter": safe["e3"]["counter"],
            "result": safe["e3"]["result"],
            "additional_effects": safe["e3"]["additional_effects"],
        },
        "safe-restart-and-retry": {
            "counter": safe["e8"]["counter"],
            "last_sequence": safe["e8"]["sessions"][fixture["client"]]["last_sequence"],
            "result": safe["e8"]["result"],
            "additional_effects": safe["e8"]["additional_effects"],
        },
        "conflicting-fingerprint": {
            "status": safe["e9"]["status"],
            "counter": safe["e9"]["counter"],
        },
        "strict-gap-policy": {
            "status": safe["e10"]["status"],
            "counter": safe["e10"]["counter"],
        },
        "unsafe-snapshot-duplicate-effect": {
            "counter_in_wrong_implementation": unsafe["e6"]["counter"],
            "first_violation_event": "e6" if unsafe["e6"]["additional_effects"] else None,
        },
    }
    compare_compact_observations(expected, actual)


def quorum_size(nodes: list[str]) -> int:
    return len(nodes) // 2 + 1


def validate_membership_change(expected: dict[str, Any], fixtures: dict[str, Any]) -> None:
    fixture = fixtures["membership.json"]
    scenarios = {item["id"]: item for item in fixture["scenarios"]}
    safe = scenarios["safe-joint-consensus"]
    safe_events = {event["id"]: event for event in safe["events"]}
    catch_up = safe_events["e2"]
    joint = safe_events["e3"]
    joint_commit = safe_events["e5"]
    election = safe_events["e7"]
    final_entry = safe_events["e8"]
    final_commit = safe_events["e10"]
    stale_write = safe_events["e11"]

    old_votes = sorted(set(election["votes"]) & set(joint["old"]))
    new_votes = sorted(set(election["votes"]) & set(joint["new"]))
    require(len(old_votes) >= quorum_size(joint["old"]), "joint election lacks old quorum")
    require(len(new_votes) >= quorum_size(joint["new"]), "joint election lacks new quorum")
    require(
        len(set(final_commit["old_acks"]) & set(joint["old"])) >= quorum_size(joint["old"]),
        "final configuration lacks old quorum",
    )
    require(
        len(set(final_commit["new_acks"]) & set(joint["new"])) >= quorum_size(joint["new"]),
        "final configuration lacks new quorum",
    )

    disjoint = scenarios["unsafe-disjoint-switch"]
    disjoint_events = {event["id"]: event for event in disjoint["events"]}
    switch = disjoint_events["e2"]
    old_quorum = sorted(disjoint_events["e1"]["acks"])
    new_quorum = sorted(disjoint_events["e3"]["votes"])
    intersection = sorted(set(old_quorum) & set(new_quorum))

    premature = scenarios["unsafe-promote-before-catchup"]
    promotion = next(event for event in premature["events"] if event["kind"] == "promote_learner")
    eligible = int(promotion["node_match_index"]) >= int(promotion["required_index"])

    actual = {
        "learner-caught-up-before-joint": {
            "match_index": int(catch_up["through_index"]),
            "required_index": int(safe["initial"]["commit_index"]),
            "eligible": int(catch_up["through_index"]) >= int(safe["initial"]["commit_index"]),
        },
        "joint-configuration-dual-quorum": {
            "old_quorum": quorum_size(joint["old"]),
            "new_quorum": quorum_size(joint["new"]),
            "old_acks": sorted(joint_commit["old_acks"]),
            "new_acks": sorted(joint_commit["new_acks"]),
        },
        "joint-election-after-crash": {
            "leader": election["candidate"],
            "term": int(election["term"]),
            "old_votes": old_votes,
            "new_votes": new_votes,
        },
        "final-configuration-and-fence": {
            "voters": sorted(final_entry["voters"]),
            "configuration_epoch": int(final_commit["index"]),
            "A_status": (
                "STALE_CONFIGURATION"
                if int(stale_write["configuration_epoch"]) < int(stale_write["expected_current_epoch"])
                else "ACCEPTED"
            ),
        },
        "disjoint-switch-has-no-intersection": {
            "old_quorum": old_quorum,
            "new_quorum": new_quorum,
            "intersection": intersection,
            "safe": bool(intersection),
            "first_unsafe_event": switch["id"] if not intersection else None,
        },
        "premature-promotion-rejected": {
            "node": promotion["node"],
            "match_index": int(promotion["node_match_index"]),
            "required_index": int(promotion["required_index"]),
            "eligible": eligible,
        },
    }
    compare_compact_observations(expected, actual)


def validate_shard_rebalance(expected: dict[str, Any], fixtures: dict[str, Any]) -> None:
    fixture = fixtures["rebalance.json"]
    plans = {item["id"]: item for item in fixture["plans"]}
    safe = plans["safe-plan"]
    events = {event["id"]: event for event in safe["events"]}
    cutover = events["e8"]
    target_frontier = max(
        int(event.get("through_index", 0))
        for event in safe["events"]
        if event["kind"] in {"copy_snapshot", "stream_delta"} and event["id"] < cutover["id"]
    )
    source_final = int(events["e7"]["final_index"])
    require(target_frontier >= int(cutover["required_target_index"]), "safe cutover precedes target catch-up")
    current_epoch = int(cutover["metadata_epoch"])
    stale = events["e10"]
    retry = events["e11"]
    effect_count = sum(
        event["kind"] == "client_retry" and event.get("write_id") == stale["write_id"]
        for event in safe["events"]
    )

    unsafe = plans["unsafe-early-cutover"]
    source_write = next(
        event for event in unsafe["events"]
        if event["kind"] == "client_write" and event["target"] == fixture["shard"]["source"]
    )
    target_write = next(
        event for event in unsafe["events"]
        if event["kind"] == "client_write" and event["target"] == fixture["shard"]["target"]
    )
    late_delta = next(event for event in unsafe["events"] if event["kind"] == "late_delta")
    same_index = int(late_delta["source_index"]) == int(target_write["target_index_after"])

    actual = {
        "safe-catch-up-before-cutover": {
            "source_final_index": source_final,
            "target_applied_index": target_frontier,
            "cutover_event": cutover["id"],
        },
        "single-write-authority": {
            "before_e7": fixture["shard"]["source"],
            "after_e7_before_e9": None,
            "after_e9": fixture["shard"]["target"],
        },
        "stale-router-retry": {
            "e10_status": "STALE_EPOCH" if int(stale["router_epoch"]) < current_epoch else "ACCEPTED",
            "applied_at": retry["target"],
            "applied_index": int(retry["target_index_after"]),
            "effect_count": effect_count,
        },
        "unsafe-index-conflict": {
            "source_write": source_write["write_id"],
            "source_index": int(source_write["source_index_after"]),
            "target_write": target_write["write_id"],
            "target_index": int(target_write["target_index_after"]),
            "safe": not same_index,
        },
    }
    compare_compact_observations(expected, actual)


def validate_atomic_commit(expected: dict[str, Any], fixtures: dict[str, Any]) -> None:
    fixture = fixtures["transactions.json"]
    scenarios = {item["id"]: item for item in fixture["scenarios"]}
    observations: dict[str, Any] = {}
    for scenario_id, scenario in scenarios.items():
        states = {participant: "INIT" for participant in fixture["participants"]}
        decision: str | None = None
        recovery_source: str | None = None
        client_timeout = False
        for event in scenario["events"]:
            kind = event["kind"]
            if kind == "persist_prepared":
                states[event["participant"]] = "PREPARED"
            elif kind == "persist_global_decision":
                decision = event["decision"]
            elif kind == "persist_commit":
                states[event["participant"]] = "COMMIT"
            elif kind == "persist_abort":
                states[event["participant"]] = "ABORT"
            elif kind == "read_durable_decision":
                require(event["decision"] == decision, f"recovery read differs from decision: {scenario_id}")
                recovery_source = event["id"]
            elif kind == "client_timeout":
                client_timeout = True
        if decision == "ABORT":
            states = {participant: "ABORT" for participant in states}

        if scenario_id == "commit-decision-survives":
            observations["commit-decision-survives"] = {
                "global_decision": decision,
                "shard-A": states["shard-A"],
                "shard-B": states["shard-B"],
                "recovery_source_event": recovery_source,
            }
        elif scenario_id == "prepared-without-decision":
            blocked = decision is None and all(state == "PREPARED" for state in states.values())
            observations["prepared-without-decision-blocks"] = {
                "shard-A": states["shard-A"],
                "shard-B": states["shard-B"],
                "global_decision": decision,
                "client_result": "UNKNOWN" if client_timeout and decision is None else decision,
                "progress": "BLOCKED" if blocked else "READY",
            }
        elif scenario_id == "participant-votes-no":
            observations["participant-no-aborts"] = {
                "global_decision": decision,
                "shard-A": states["shard-A"],
                "shard-B": states["shard-B"],
                "commit_allowed": decision == "COMMIT",
            }
    compare_compact_observations(expected, observations)


def explanatory_counterexample(history: dict[str, Any], initial: Any) -> list[str]:
    operations = history["operations"]
    reads = [item for item in operations if item["op"] == "read"]
    writes = [item for item in operations if item["op"] == "write"]
    selected: set[str] = {item["id"] for item in reads}
    for write in writes:
        observed = any(read.get("result") == write.get("value") for read in reads)
        violates_later_read = any(
            write.get("complete") is not None
            and write["complete"] < read["invoke"]
            and read.get("result") != write.get("value")
            for read in reads
        )
        if observed or violates_later_read:
            selected.add(write["id"])
    reduced = copy.deepcopy(history)
    reduced["operations"] = [item for item in operations if item["id"] in selected]
    witness, _ = search_history(reduced, initial, real_time=True)
    require(witness is None, f"derived counterexample is linearizable: {history['id']}")
    return [item["id"] for item in operations if item["id"] in selected]


def validate_linearizability(expected: dict[str, Any], fixtures: dict[str, Any]) -> None:
    fixture = fixtures["histories.json"]
    initial = fixture["object"]["initial"]
    actual: dict[str, Any] = {}
    for history in fixture["histories"]:
        witness, included_pending = search_history(history, initial, real_time=True)
        if witness is not None:
            result: dict[str, Any] = {
                "linearizable": True,
                "witness": witness,
            }
            if history["id"] in {"completed-write-then-read", "pending-write-observed"}:
                result["included_pending"] = included_pending
        else:
            result = {
                "linearizable": False,
                "minimal_counterexample": explanatory_counterexample(history, initial),
            }
        actual[history["id"]] = result
    compare_compact_observations(expected, actual)


def contains_todo(value: Any) -> bool:
    if isinstance(value, str):
        return "TODO" in value
    if isinstance(value, dict):
        return any(contains_todo(item) for item in value.values())
    if isinstance(value, list):
        return any(contains_todo(item) for item in value)
    return False


def completed_simulation_plan(template: dict[str, Any]) -> dict[str, Any]:
    plan = copy.deepcopy(template)
    plan["protocol"] = "three-node Raft election and one-entry replication"
    plan["implementation_revision"] = "reference-plan-v1"
    plan["system_model"].update({
        "nodes": ["A", "B", "C"],
        "storage": "atomic durable term, vote and log",
        "clients": "one client with invocation, completion and unknown states",
    })
    plan["state"]["node_state"] = ["role", "term", "voted_for", "log", "commit_index", "last_applied"]
    plan["state"]["storage_state"] = ["durable_term", "durable_vote", "durable_log"]
    plan["state"]["client_state"] = ["operation_id", "status", "result"]
    plan["events"][-1] = {"kind": "complete_disk", "parameters": ["operation_id"]}
    plan["faults"][-1] = "storage_failure"
    plan["safety_invariants"] = [
        "one leader per term",
        "one durable vote per node and term",
        "log matching",
        "last_applied <= commit_index",
    ]
    plan["liveness_expectations"] = [{
        "condition": "a connected majority remains up",
        "fairness_assumption": "enabled delivery, timer and storage completion are eventually selected",
        "bound": 200,
    }]
    plan["schedules"] = [
        {"id": "normal-1", "seed": 1, "events": ["elect-A", "append-x", "commit-x"]},
        {"id": "fault-split-vote", "seed": 2, "events": ["timeout-A", "timeout-B", "drop-to-C"]},
        {"id": "fault-vote-crash", "seed": 3, "events": ["persist-vote", "crash-A", "restart-A"]},
        {"id": "fault-leader-crash", "seed": 4, "events": ["append-x", "crash-leader", "elect-B"]},
        {"id": "fault-one-way-partition", "seed": 5, "events": ["partition-A-B", "timeout-B"]},
        {"id": "fault-response-loss", "seed": 6, "events": ["commit-x", "drop-response", "retry-x"]},
    ]
    plan["shrinking_strategy"] = ["remove event chunks and require the same first invariant violation"]
    plan["model_gaps"] = ["filesystem durability", "serialization", "thread memory ordering"]
    plan["external_integration_tests"] = ["process crash with filesystem-backed storage"]
    return plan


def validate_simulation_plan(expected: dict[str, Any], fixtures: dict[str, Any]) -> None:
    template = fixtures["plan-template.json"]
    plan = completed_simulation_plan(template)
    schedule_ids = [item["id"] for item in plan["schedules"]]
    require(len(schedule_ids) == len(set(schedule_ids)), "simulation schedule ids are not unique")
    require(
        all(isinstance(item.get("seed"), int) and nonempty_strings(item.get("events")) for item in plan["schedules"]),
        "simulation schedule lacks seed or explicit events",
    )
    normal = [item for item in plan["schedules"] if item["id"].startswith("normal-")]
    faults = [item for item in plan["schedules"] if item["id"].startswith("fault-")]
    actual = {
        "canonical-template-is-incomplete": {"contains_todo": contains_todo(template)},
        "completed-plan-required-state": {
            "contains_todo": contains_todo(plan),
            "state_sections": list(plan["state"]),
        },
        "completed-plan-schedule-coverage": {
            "minimum_normal_schedules": len(normal),
            "minimum_fault_schedules": len(faults),
            "records_seed": all("seed" in item for item in plan["schedules"]),
            "records_explicit_events": all(nonempty_strings(item.get("events")) for item in plan["schedules"]),
        },
        "completed-plan-artifacts": {"required": list(plan["failure_artifacts"])},
    }
    compare_compact_observations(expected, actual)


SEMANTIC_CHECKERS: dict[str, Callable[[dict[str, Any], dict[str, Any]], None]] = {
    "causality-v1": validate_causality,
    "failure-model-v1": validate_failure_model,
    "consistency-history-v1": validate_consistency_history,
    "quorum-register-v1": validate_quorum_register,
    "failure-detector-v1": validate_failure_detector,
    "anti-entropy-v1": validate_anti_entropy,
}

COMPACT_SEMANTIC_CHECKERS: dict[
    str,
    Callable[[dict[str, Any], dict[str, Any]], None],
] = {
    "03-consensus-and-membership/01-election-trace": validate_election_trace,
    "03-consensus-and-membership/02-log-reconciliation": validate_log_reconciliation,
    "03-consensus-and-membership/03-client-session": validate_client_session,
    "03-consensus-and-membership/04-membership-change": validate_membership_change,
    "04-partitioning-and-atomicity/01-shard-rebalance": validate_shard_rebalance,
    "04-partitioning-and-atomicity/02-atomic-commit": validate_atomic_commit,
    "05-validation/01-linearizability": validate_linearizability,
    "05-validation/02-simulation-plan": validate_simulation_plan,
}


def mutate_election(fixtures: dict[str, Any]) -> None:
    scenario = find_object_with_id(fixtures["election.json"], "split-vote-and-retry")
    require(scenario is not None, "mutant cannot find split-vote scenario")
    event = find_object_with_id(scenario, "e5")
    require(event is not None, "mutant cannot find split-vote event e5")
    event.update({
        "kind": "deliver_request_vote",
        "last_log_index": 4,
        "last_log_term": 8,
    })


def mutate_log(fixtures: dict[str, Any]) -> None:
    scenario = find_object_with_id(fixtures["logs.json"], "conflicting-suffix")
    require(scenario is not None, "mutant cannot find conflicting-suffix scenario")
    entry = next(item for item in scenario["follower"]["log"] if item["index"] == 3)
    entry["term"] = 9


def mutate_session(fixtures: dict[str, Any]) -> None:
    fixtures["sessions.json"]["sequential_spec"]["initial"]["client_sessions"]["client-7"]["last_sequence"] = 1


def mutate_membership(fixtures: dict[str, Any]) -> None:
    scenario = find_object_with_id(fixtures["membership.json"], "safe-joint-consensus")
    require(scenario is not None, "mutant cannot find safe membership scenario")
    event = find_object_with_id(scenario, "e2")
    require(event is not None, "mutant cannot find catch-up event")
    event["through_index"] = 9


def mutate_shard(fixtures: dict[str, Any]) -> None:
    plan = find_object_with_id(fixtures["rebalance.json"], "safe-plan")
    require(plan is not None, "mutant cannot find safe rebalance plan")
    event = find_object_with_id(plan, "e6")
    require(event is not None, "mutant cannot find final delta event")
    event["through_index"] = 121


def mutate_atomic(fixtures: dict[str, Any]) -> None:
    scenario = find_object_with_id(fixtures["transactions.json"], "commit-decision-survives")
    require(scenario is not None, "mutant cannot find commit scenario")
    event = find_object_with_id(scenario, "e8")
    require(event is not None, "mutant cannot find durable decision event")
    event["decision"] = "ABORT"


def mutate_linearizability(fixtures: dict[str, Any]) -> None:
    history = find_object_with_id(fixtures["histories.json"], "stale-read-after-completion")
    require(history is not None, "mutant cannot find stale-read history")
    read = next(item for item in history["operations"] if item["id"] == "r1")
    read["result"] = 1


def mutate_simulation(fixtures: dict[str, Any]) -> None:
    fixtures["plan-template.json"]["failure_artifacts"].pop()


COMPACT_MUTATORS: dict[str, Callable[[dict[str, Any]], None]] = {
    "03-consensus-and-membership/01-election-trace": mutate_election,
    "03-consensus-and-membership/02-log-reconciliation": mutate_log,
    "03-consensus-and-membership/03-client-session": mutate_session,
    "03-consensus-and-membership/04-membership-change": mutate_membership,
    "04-partitioning-and-atomicity/01-shard-rebalance": mutate_shard,
    "04-partitioning-and-atomicity/02-atomic-commit": mutate_atomic,
    "05-validation/01-linearizability": mutate_linearizability,
    "05-validation/02-simulation-plan": mutate_simulation,
}


def require_mutant_rejected(
    exercise_id: str,
    checker: Callable[[dict[str, Any], dict[str, Any]], None],
    expected: dict[str, Any],
    fixtures: dict[str, Any],
) -> None:
    mutant = copy.deepcopy(fixtures)
    COMPACT_MUTATORS[exercise_id](mutant)
    try:
        checker(expected, mutant)
    except CheckError:
        return
    raise CheckError(f"representative semantic mutant was accepted: {exercise_id}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate expected/reference exercise contracts and semantic outcomes."
    )
    parser.add_argument(
        "paths",
        nargs="*",
        help="Exercise directories or expected.json files; default scans every exercise.",
    )
    args = parser.parse_args()

    expected_paths = discover_expected(args.paths)
    require(expected_paths, "no expected.json files found")
    total_cases = 0
    semantic_count = 0
    mutant_count = 0
    for path in expected_paths:
        expected, fixtures = validate_generic(path)
        exercise_id = expected["exercise_id"]
        if "automated_checks" in expected:
            require(
                exercise_id in COMPACT_SEMANTIC_CHECKERS,
                f"compact exercise has no semantic checker: {exercise_id}",
            )
            checker = COMPACT_SEMANTIC_CHECKERS[exercise_id]
            checker(expected, fixtures)
            require(
                exercise_id in COMPACT_MUTATORS,
                f"compact exercise has no representative mutant: {exercise_id}",
            )
            require_mutant_rejected(exercise_id, checker, expected, fixtures)
            semantic_count += 1
            mutant_count += 1
            print(f"OK semantics {exercise_id} checker=compact-v1 mutant=rejected")
        else:
            checker_name = expected.get("semantic_checker")
            require(
                isinstance(checker_name, str) and checker_name,
                f"generic exercise has no semantic_checker: {exercise_id}",
            )
            require(checker_name in SEMANTIC_CHECKERS, f"unknown semantic_checker {checker_name}: {exercise_id}")
            SEMANTIC_CHECKERS[checker_name](expected, fixtures)
            semantic_count += 1
            print(f"OK semantics {exercise_id} checker={checker_name}")
        contract_items = expected.get("cases", expected.get("automated_checks", []))
        print(f"OK contract {exercise_id} cases={len(contract_items)}")
        total_cases += len(contract_items)

    print(
        f"CHECK_EXERCISES OK exercises={len(expected_paths)} "
        f"semantic={semantic_count} cases={total_cases} mutants={mutant_count}"
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except CheckError as exc:
        print(f"ERROR {exc}", file=sys.stderr)
        raise SystemExit(1)
