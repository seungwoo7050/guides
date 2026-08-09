#!/usr/bin/env python3
"""Cross-check published schemas, runtime routes, policy IDs, and fixtures."""

from __future__ import annotations

import ast
import json
import re
import sys
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[1]
CAPSTONE = ROOT / "exercises" / "10-capstone-local-coding-agent"
REFERENCE = CAPSTONE / "reference" / "coding_agent"
SCHEMAS = ROOT / "contracts"
CONTRACT_VERSION = "1.0"
GUIDE_ID = "agentic-systems"
PROFILE_ID = "local-coding-agent"

CONTROL_ACTIONS = {"ASK_USER", "SUBMIT_RESULT", "ABORT"}
EXPECTED_ACTIONS = {
    "REPOSITORY_STATUS",
    "LIST_FILES",
    "READ_FILE",
    "SEARCH_TEXT",
    "SEARCH_KNOWLEDGE",
    "PREPARE_PATCH",
    "APPLY_PATCH",
    "RUN_CHECK",
    "SHOW_DIFF",
    "RESTORE_CHANGE_SET",
    "ASK_USER",
    "SUBMIT_RESULT",
    "ABORT",
}
EXPECTED_TOOL_ROUTES = {
    "repository_status",
    "list_files",
    "read_file",
    "search_text",
    "search_knowledge",
    "prepare_patch",
    "apply_patch",
    "run_check",
    "show_diff",
    "restore_change_set",
}
EXPECTED_MODEL_EVENTS = {
    "TEXT_DELTA",
    "ACTION_DELTA",
    "ACTION_COMPLETE",
    "USAGE",
    "COMPLETED",
    "ERROR",
}
EXPECTED_TERMINAL_STATES = {"SUCCEEDED", "FAILED", "POLICY_BLOCKED", "BUDGET_EXHAUSTED", "CANCELLED"}
EXPECTED_NETWORK_PROFILES = {"deny", "loopback", "allow"}


def fail(messages: Iterable[str]) -> None:
    values = list(messages)
    for message in values:
        print(f"ERROR: {message}", file=sys.stderr)
    raise SystemExit(1)


def parse_python(path: Path) -> ast.Module:
    try:
        return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except (OSError, UnicodeDecodeError, SyntaxError) as exc:
        fail([f"Python 계약을 읽을 수 없습니다: {path.relative_to(ROOT)}: {exc}"])


def literal_assignment(tree: ast.Module, name: str) -> Any:
    for node in tree.body:
        if isinstance(node, (ast.Assign, ast.AnnAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            if any(isinstance(target, ast.Name) and target.id == name for target in targets):
                try:
                    return ast.literal_eval(node.value)
                except (ValueError, TypeError) as exc:
                    fail([f"{name}은 정적 literal이어야 합니다: {exc}"])
    fail([f"Python 계약 상수를 찾지 못했습니다: {name}"])


def class_literal_assignment(tree: ast.Module, class_name: str, name: str) -> Any:
    for node in tree.body:
        if not isinstance(node, ast.ClassDef) or node.name != class_name:
            continue
        for child in node.body:
            if isinstance(child, (ast.Assign, ast.AnnAssign)):
                targets = child.targets if isinstance(child, ast.Assign) else [child.target]
                if any(isinstance(target, ast.Name) and target.id == name for target in targets):
                    return ast.literal_eval(child.value)
    fail([f"Python class 계약 상수를 찾지 못했습니다: {class_name}.{name}"])


def dataclass_fields(tree: ast.Module, class_name: str) -> tuple[str, ...]:
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            return tuple(
                child.target.id
                for child in node.body
                if isinstance(child, ast.AnnAssign) and isinstance(child.target, ast.Name)
            )
    fail([f"dataclass를 찾지 못했습니다: {class_name}"])


def mapping_keys(tree: ast.Module, name: str) -> set[str]:
    for node in tree.body:
        if not isinstance(node, (ast.Assign, ast.AnnAssign)):
            continue
        targets = node.targets if isinstance(node, ast.Assign) else [node.target]
        if not any(isinstance(target, ast.Name) and target.id == name for target in targets):
            continue
        if not isinstance(node.value, ast.Dict):
            fail([f"{name}은 mapping literal이어야 합니다."])
        keys: set[str] = set()
        for key in node.value.keys:
            if not isinstance(key, ast.Constant) or not isinstance(key.value, str):
                fail([f"{name}은 string key mapping이어야 합니다."])
            keys.add(key.value)
        return keys
    fail([f"Python 계약 mapping을 찾지 못했습니다: {name}"])


def gateway_tool_ids(tree: ast.Module) -> set[str]:
    values: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Compare) or len(node.ops) != 1 or len(node.comparators) != 1:
            continue
        if not isinstance(node.left, ast.Name) or node.left.id != "tool":
            continue
        comparator = node.comparators[0]
        if isinstance(node.ops[0], ast.Eq) and isinstance(comparator, ast.Constant) and isinstance(comparator.value, str):
            values.add(comparator.value)
        elif isinstance(node.ops[0], ast.In) and isinstance(comparator, (ast.Set, ast.Tuple, ast.List)):
            for element in comparator.elts:
                if isinstance(element, ast.Constant) and isinstance(element.value, str):
                    values.add(element.value)
    return values


def function_comparison_ids(tree: ast.Module, function_name: str, variable: str) -> set[str]:
    function = next(
        (node for node in tree.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == function_name),
        None,
    )
    if function is None:
        fail([f"Python 계약 함수를 찾지 못했습니다: {function_name}"])
    values: set[str] = set()
    for node in ast.walk(function):
        if not isinstance(node, ast.Compare) or len(node.ops) != 1 or len(node.comparators) != 1:
            continue
        if not isinstance(node.left, ast.Name) or node.left.id != variable:
            continue
        comparator = node.comparators[0]
        if isinstance(node.ops[0], ast.Eq) and isinstance(comparator, ast.Constant) and isinstance(comparator.value, str):
            values.add(comparator.value)
        elif isinstance(node.ops[0], ast.In) and isinstance(comparator, (ast.Set, ast.Tuple, ast.List)):
            values.update(
                element.value
                for element in comparator.elts
                if isinstance(element, ast.Constant) and isinstance(element.value, str)
            )
    return values


def class_membership_ids(tree: ast.Module, class_name: str, variable: str) -> set[str]:
    class_node = next((node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == class_name), None)
    if class_node is None:
        fail([f"Python 계약 class를 찾지 못했습니다: {class_name}"])
    values: set[str] = set()
    for node in ast.walk(class_node):
        if not isinstance(node, ast.Compare) or len(node.ops) != 1 or len(node.comparators) != 1:
            continue
        if not isinstance(node.left, ast.Name) or node.left.id != variable:
            continue
        comparator = node.comparators[0]
        if isinstance(node.ops[0], (ast.In, ast.NotIn)) and isinstance(comparator, (ast.Set, ast.Tuple, ast.List)):
            values.update(
                element.value
                for element in comparator.elts
                if isinstance(element, ast.Constant) and isinstance(element.value, str)
            )
    return values


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        fail([f"JSON 계약을 읽을 수 없습니다: {path.relative_to(ROOT)}: {exc}"])


def schema_action_kinds(schema: dict[str, Any]) -> set[str]:
    try:
        values = schema["properties"]["kind"]["enum"]
    except (KeyError, TypeError):
        fail(["contracts/action.schema.json에 kind enum이 없습니다."])
    if not isinstance(values, list) or not all(isinstance(value, str) for value in values):
        fail(["action kind enum은 string array여야 합니다."])
    return set(values)


def schema_required(schema: dict[str, Any]) -> set[str]:
    value = schema.get("required")
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        fail([f"schema required가 string array가 아닙니다: {schema.get('$id', '<unknown>')}"])
    return set(value)


def check_schema_refs(schema_path: Path, value: Any, problems: list[str]) -> None:
    if isinstance(value, dict):
        reference = value.get("$ref")
        if isinstance(reference, str) and not reference.startswith(("#", "http://", "https://")):
            target = reference.split("#", 1)[0]
            if not (schema_path.parent / target).is_file():
                problems.append(f"{schema_path.relative_to(ROOT)}: 깨진 schema $ref {reference}")
        for child in value.values():
            check_schema_refs(schema_path, child, problems)
    elif isinstance(value, list):
        for child in value:
            check_schema_refs(schema_path, child, problems)


def check_schemas(problems: list[str]) -> dict[str, dict[str, Any]]:
    schemas: dict[str, dict[str, Any]] = {}
    identifiers: set[str] = set()
    for path in sorted(SCHEMAS.glob("*.schema.json")):
        value = load_json(path)
        if not isinstance(value, dict):
            problems.append(f"{path.relative_to(ROOT)}: schema root는 object여야 합니다.")
            continue
        identifier = value.get("$id")
        if not isinstance(identifier, str) or f"-{CONTRACT_VERSION}.schema.json" not in identifier:
            problems.append(f"{path.relative_to(ROOT)}: $id에 contract version {CONTRACT_VERSION}이 없습니다.")
        elif identifier in identifiers:
            problems.append(f"중복 schema $id: {identifier}")
        else:
            identifiers.add(identifier)
        if value.get("$schema") != "https://json-schema.org/draft/2020-12/schema":
            problems.append(f"{path.relative_to(ROOT)}: JSON Schema Draft 2020-12가 아닙니다.")
        check_schema_refs(path, value, problems)
        schemas[path.name] = value
    expected = {
        "action.schema.json",
        "model-event.schema.json",
        "model-request.schema.json",
        "repository-snapshot.schema.json",
        "context-item.schema.json",
    }
    if set(schemas) != expected:
        problems.append(f"schema 파일 집합 불일치: expected={sorted(expected)} actual={sorted(schemas)}")
    for name in ("action.schema.json", "model-event.schema.json"):
        if name in schemas and schemas[name].get("properties", {}).get("contract_version", {}).get("const") != CONTRACT_VERSION:
            problems.append(f"{name}: contract_version const는 {CONTRACT_VERSION}이어야 합니다.")
    return schemas


def check_runtime(schemas: dict[str, dict[str, Any]], problems: list[str]) -> None:
    contracts_tree = parse_python(REFERENCE / "contracts.py")
    runtime_tree = parse_python(REFERENCE / "runtime.py")
    tools_tree = parse_python(REFERENCE / "tools.py")
    types_tree = parse_python(REFERENCE / "types.py")
    process_tree = parse_python(REFERENCE / "process.py")
    policy_tree = parse_python(REFERENCE / "policy.py")
    checkpoint_tree = parse_python(REFERENCE / "checkpoint.py")
    patching_tree = parse_python(REFERENCE / "patching.py")
    capstone_tree = parse_python(REFERENCE / "capstone.py")

    for constant in ("ACTION_CONTRACT_VERSION", "MODEL_EVENT_CONTRACT_VERSION"):
        actual = literal_assignment(contracts_tree, constant)
        if actual != CONTRACT_VERSION:
            problems.append(f"{constant}={actual!r}, expected {CONTRACT_VERSION!r}")
    if literal_assignment(capstone_tree, "ACTION_VERSION") != CONTRACT_VERSION:
        problems.append("capstone ACTION_VERSION이 published action contract와 다릅니다.")
    if class_literal_assignment(capstone_tree, "FixtureCapstone", "VERSION") != CONTRACT_VERSION:
        problems.append("FixtureCapstone session version이 guide contract와 다릅니다.")
    for tree, class_name in (
        (checkpoint_tree, "CheckpointStore"),
        (patching_tree, "PatchEngine"),
        (policy_tree, "ApprovalStore"),
        (process_tree, "CommandCatalog"),
    ):
        if class_literal_assignment(tree, class_name, "VERSION") != "1":
            problems.append(f"{class_name}.VERSION은 runtime schema version '1'이어야 합니다.")

    schema_actions = schema_action_kinds(schemas["action.schema.json"])
    raw_schema_actions = schemas["action.schema.json"].get("properties", {}).get("kind", {}).get("enum", [])
    if isinstance(raw_schema_actions, list) and len(raw_schema_actions) != len(schema_actions):
        problems.append("action schema kind enum에 중복 ID가 있습니다.")
    if schema_actions != EXPECTED_ACTIONS:
        problems.append(
            f"published action ID 집합 불일치: missing={sorted(EXPECTED_ACTIONS-schema_actions)} "
            f"extra={sorted(schema_actions-EXPECTED_ACTIONS)}"
        )
    validator_actions = mapping_keys(contracts_tree, "_ACTION_VALIDATORS")
    if validator_actions != schema_actions:
        problems.append(
            f"action schema/validator ID 불일치: schema_only={sorted(schema_actions-validator_actions)} "
            f"validator_only={sorted(validator_actions-schema_actions)}"
        )

    tool_actions = literal_assignment(runtime_tree, "TOOL_ACTIONS")
    if not isinstance(tool_actions, dict) or not all(isinstance(key, str) and isinstance(value, str) for key, value in tool_actions.items()):
        problems.append("runtime TOOL_ACTIONS는 string→string mapping이어야 합니다.")
        tool_actions = {}
    expected_routed_actions = schema_actions - CONTROL_ACTIONS
    if set(tool_actions) != expected_routed_actions:
        problems.append(
            f"action/runtime route 불일치: missing={sorted(expected_routed_actions-set(tool_actions))} "
            f"extra={sorted(set(tool_actions)-expected_routed_actions)}"
        )

    gateway_ids = gateway_tool_ids(tools_tree)
    runtime_tool_ids = set(tool_actions.values())
    if runtime_tool_ids != EXPECTED_TOOL_ROUTES:
        problems.append(
            f"published tool route ID 집합 불일치: missing={sorted(EXPECTED_TOOL_ROUTES-runtime_tool_ids)} "
            f"extra={sorted(runtime_tool_ids-EXPECTED_TOOL_ROUTES)}"
        )
    if gateway_ids != runtime_tool_ids:
        problems.append(
            f"runtime/gateway tool ID 불일치: runtime_only={sorted(runtime_tool_ids-gateway_ids)} "
            f"gateway_only={sorted(gateway_ids-runtime_tool_ids)}"
        )

    model_event_schema = schemas["model-event.schema.json"]
    raw_model_events = model_event_schema.get("properties", {}).get("kind", {}).get("enum", [])
    schema_model_events = set(raw_model_events) if isinstance(raw_model_events, list) else set()
    if isinstance(raw_model_events, list) and len(raw_model_events) != len(schema_model_events):
        problems.append("model-event schema kind enum에 중복 ID가 있습니다.")
    parser_model_events = function_comparison_ids(contracts_tree, "parse_model_event", "kind")
    if schema_model_events != EXPECTED_MODEL_EVENTS or parser_model_events != EXPECTED_MODEL_EVENTS:
        problems.append(
            f"model event ID 불일치: schema={sorted(schema_model_events)} parser={sorted(parser_model_events)}"
        )

    terminal = literal_assignment(runtime_tree, "TERMINAL")
    if set(terminal) != EXPECTED_TERMINAL_STATES:
        problems.append(f"terminal state 불일치: expected={sorted(EXPECTED_TERMINAL_STATES)} actual={sorted(terminal)}")

    process_profiles = class_membership_ids(process_tree, "CommandCatalog", "profile")
    policy_profiles = set(class_literal_assignment(policy_tree, "PolicyEngine", "_NETWORK_ORDER"))
    if process_profiles != EXPECTED_NETWORK_PROFILES or policy_profiles != EXPECTED_NETWORK_PROFILES:
        problems.append(
            f"network profile ID 불일치: process={sorted(process_profiles)} policy={sorted(policy_profiles)}"
        )

    shape_checks = {
        "model-request.schema.json": ("ModelRequest", None),
        "repository-snapshot.schema.json": ("RepositorySnapshot", None),
        "context-item.schema.json": ("ContextItem", None),
        "action.schema.json": ("Action", None),
    }
    for schema_name, (class_name, _unused) in shape_checks.items():
        required = schema_required(schemas[schema_name])
        fields = set(dataclass_fields(types_tree, class_name))
        if required != fields:
            problems.append(
                f"{schema_name}/{class_name} field ID 불일치: schema_only={sorted(required-fields)} "
                f"runtime_only={sorted(fields-required)}"
            )
    reference_required = set(schemas["context-item.schema.json"]["properties"]["reference"].get("required", []))
    source_fields = set(dataclass_fields(types_tree, "SourceRef"))
    if reference_required != source_fields:
        problems.append(
            f"context reference/SourceRef field ID 불일치: schema_only={sorted(reference_required-source_fields)} "
            f"runtime_only={sorted(source_fields-reference_required)}"
        )

    grant_fields = set(dataclass_fields(types_tree, "Grant"))
    for required_field in {"principal", "command_ids", "knowledge_scopes", "network", "expires_at", "revoked"}:
        if required_field not in grant_fields:
            problems.append(f"Grant policy field 누락: {required_field}")
    tool_request_fields = set(dataclass_fields(types_tree, "ToolRequest"))
    for required_field in {"request_id", "principal", "tool", "arguments", "operation_id", "approval_id"}:
        if required_field not in tool_request_fields:
            problems.append(f"ToolRequest identity field 누락: {required_field}")


def check_fixtures(problems: list[str]) -> tuple[int, int, int]:
    task_paths = sorted((CAPSTONE / "fixtures" / "tasks").glob("*/task.json"))
    task_ids: set[str] = set()
    command_ids: set[str] = set()
    requested_scopes: set[str] = set()
    for path in task_paths:
        value = load_json(path)
        if not isinstance(value, dict):
            problems.append(f"{path.relative_to(ROOT)}: task root는 object여야 합니다.")
            continue
        task_id = value.get("id")
        if task_id != path.parent.name:
            problems.append(f"{path.relative_to(ROOT)}: task id/folder 불일치: {task_id!r}")
        if not isinstance(task_id, str) or task_id in task_ids:
            problems.append(f"{path.relative_to(ROOT)}: 중복 또는 잘못된 task id: {task_id!r}")
        else:
            task_ids.add(task_id)
        if not isinstance(value.get("task"), str) or not value["task"].strip():
            problems.append(f"{path.relative_to(ROOT)}: task 설명이 비었습니다.")
        allowed = value.get("allowed_changes")
        if not isinstance(allowed, list) or not allowed or not all(isinstance(item, str) and item for item in allowed):
            problems.append(f"{path.relative_to(ROOT)}: allowed_changes가 비었거나 잘못되었습니다.")
        commands = value.get("commands")
        if not isinstance(commands, dict) or not commands:
            problems.append(f"{path.relative_to(ROOT)}: command catalog가 비었습니다.")
        else:
            for command_id, argv in commands.items():
                qualified = f"{task_id}:{command_id}"
                if not isinstance(command_id, str) or not command_id or qualified in command_ids:
                    problems.append(f"{path.relative_to(ROOT)}: 잘못되거나 중복된 command ID: {command_id!r}")
                else:
                    command_ids.add(qualified)
                if not isinstance(argv, list) or not argv or not all(isinstance(item, str) and item and "\0" not in item for item in argv):
                    problems.append(f"{path.relative_to(ROOT)}: {command_id} argv가 잘못되었습니다.")
        budget = value.get("budget")
        if not isinstance(budget, dict):
            problems.append(f"{path.relative_to(ROOT)}: budget가 없습니다.")
        else:
            for field in ("max_steps", "max_writes", "max_wall_seconds"):
                amount = budget.get(field)
                if isinstance(amount, bool) or not isinstance(amount, (int, float)) or amount <= 0:
                    problems.append(f"{path.relative_to(ROOT)}: budget {field}가 양수가 아닙니다.")
        scopes = value.get("knowledge_scopes", [])
        if not isinstance(scopes, list) or not all(isinstance(item, str) and item for item in scopes):
            problems.append(f"{path.relative_to(ROOT)}: knowledge_scopes가 잘못되었습니다.")
        else:
            requested_scopes.update(scopes)

    knowledge_paths = sorted((CAPSTONE / "fixtures" / "knowledge").glob("*.json"))
    source_ids: set[str] = set()
    available_scopes: set[str] = set()
    for path in knowledge_paths:
        value = load_json(path)
        required = {"source_id", "scope", "revision", "trust", "freshness", "title", "content", "claims"}
        if not isinstance(value, dict) or set(value) != required:
            problems.append(f"{path.relative_to(ROOT)}: knowledge field ID 불일치")
            continue
        source_id = value.get("source_id")
        if not isinstance(source_id, str) or not source_id or source_id in source_ids:
            problems.append(f"{path.relative_to(ROOT)}: 중복 또는 잘못된 source_id: {source_id!r}")
        else:
            source_ids.add(source_id)
        scope = value.get("scope")
        if isinstance(scope, str) and scope:
            available_scopes.add(scope)
        else:
            problems.append(f"{path.relative_to(ROOT)}: knowledge scope가 잘못되었습니다.")
        if value.get("freshness") not in {"current", "stale"}:
            problems.append(f"{path.relative_to(ROOT)}: freshness ID가 잘못되었습니다.")
    if requested_scopes - available_scopes:
        problems.append(f"task가 존재하지 않는 knowledge scope를 요청함: {sorted(requested_scopes-available_scopes)}")

    mutant_path = CAPSTONE / "mutants" / "cases.json"
    mutants = load_json(mutant_path)
    cases = mutants.get("cases") if isinstance(mutants, dict) else None
    mutant_ids: set[str] = set()
    if not isinstance(cases, list) or not cases:
        problems.append(f"{mutant_path.relative_to(ROOT)}: mutant cases가 비었습니다.")
    else:
        for case in cases:
            case_id = case.get("id") if isinstance(case, dict) else None
            expected = case.get("expected") if isinstance(case, dict) else None
            if not isinstance(case_id, str) or not case_id or case_id in mutant_ids:
                problems.append(f"{mutant_path.relative_to(ROOT)}: 중복 또는 잘못된 mutant ID: {case_id!r}")
            else:
                mutant_ids.add(case_id)
            if not isinstance(expected, str) or not re.fullmatch(r"[A-Z][A-Z0-9_]*", expected):
                problems.append(f"{mutant_path.relative_to(ROOT)}: 잘못된 mutant expected ID: {expected!r}")
    if mutants.get("mutant_version") != CONTRACT_VERSION:
        problems.append(f"mutant_version은 {CONTRACT_VERSION}이어야 합니다.")
    return len(task_ids), len(command_ids), len(mutant_ids)


def check_profile_identity(problems: list[str]) -> None:
    new_workspace = (ROOT / "scripts" / "new_workspace.py").read_text(encoding="utf-8")
    for literal in (f'"guide": "{GUIDE_ID}"', f'"profile": "{PROFILE_ID}"', f'"contract_version": "{CONTRACT_VERSION}"'):
        if literal not in new_workspace:
            problems.append(f"new_workspace manifest identity 누락: {literal}")


def check_runner_surface(problems: list[str]) -> None:
    tests = CAPSTONE / "tests"
    required = {f"test_stage_{stage:02d}_" for stage in range(1, 11)}
    actual_prefixes = {
        re.match(r"(test_stage_\d{2}_)", path.name).group(1)
        for path in tests.glob("test_stage_*.py")
        if re.match(r"(test_stage_\d{2}_)", path.name)
    }
    if required != actual_prefixes:
        problems.append(
            f"stage test surface 불일치: missing={sorted(required-actual_prefixes)} extra={sorted(actual_prefixes-required)}"
        )
    for relative in ("run.py", "test_mutants.py"):
        if not (tests / relative).is_file():
            problems.append(f"zero-test를 막는 필수 runner 파일 누락: tests/{relative}")


def main() -> None:
    problems: list[str] = []
    schemas = check_schemas(problems)
    if all(name in schemas for name in ("action.schema.json", "model-event.schema.json", "model-request.schema.json", "repository-snapshot.schema.json", "context-item.schema.json")):
        check_runtime(schemas, problems)
    tasks, commands, mutants = check_fixtures(problems)
    check_profile_identity(problems)
    check_runner_surface(problems)
    if problems:
        fail(sorted(set(problems)))
    print(
        f"CONTRACTS OK schemas={len(schemas)} tasks={tasks} commands={commands} "
        f"mutants={mutants} profile={PROFILE_ID} version={CONTRACT_VERSION}"
    )


if __name__ == "__main__":
    main()
