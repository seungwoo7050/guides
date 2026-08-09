from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from pathlib import PurePosixPath
from typing import Any, Callable

from .errors import ContractError
from .types import Action, ModelEvent, ModelRequest


ACTION_CONTRACT_VERSION = "1.0"
MODEL_EVENT_CONTRACT_VERSION = "1.0"

_IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")


def _mapping(value: Any, name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ContractError(f"{name} must be an object")
    if not all(isinstance(key, str) for key in value):
        raise ContractError(f"{name} keys must be strings")
    return value


def _exact_keys(
    value: Mapping[str, Any],
    *,
    required: set[str],
    optional: set[str] = frozenset(),
    name: str,
) -> None:
    keys = set(value)
    missing = required - keys
    extra = keys - required - optional
    if missing:
        raise ContractError(f"{name} is missing: {', '.join(sorted(missing))}")
    if extra:
        raise ContractError(f"{name} has unknown fields: {', '.join(sorted(extra))}")


def _text(value: Any, name: str, *, maximum: int = 4096, allow_empty: bool = False) -> str:
    if not isinstance(value, str):
        raise ContractError(f"{name} must be a string")
    if "\x00" in value:
        raise ContractError(f"{name} contains NUL")
    if not allow_empty and not value.strip():
        raise ContractError(f"{name} must not be empty")
    if len(value) > maximum:
        raise ContractError(f"{name} exceeds {maximum} characters")
    return value


def _identifier(value: Any, name: str) -> str:
    text = _text(value, name, maximum=128)
    if not _IDENTIFIER.fullmatch(text):
        raise ContractError(f"{name} is not a valid identifier")
    return text


def _integer(value: Any, name: str, *, minimum: int = 0, maximum: int = 1_000_000) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ContractError(f"{name} must be an integer")
    if not minimum <= value <= maximum:
        raise ContractError(f"{name} must be between {minimum} and {maximum}")
    return value


def _relative_path(value: Any, name: str) -> str:
    text = _text(value, name, maximum=4096)
    candidate = PurePosixPath(text.replace("\\", "/"))
    if candidate.is_absolute() or any(part in {"", ".."} for part in candidate.parts):
        raise ContractError(f"{name} must stay inside the repository")
    normalized = candidate.as_posix()
    if normalized == ".":
        return normalized
    if normalized.startswith(".git/") or normalized == ".git":
        raise ContractError(f"{name} may not address Git metadata")
    return normalized


def _string_list(
    value: Any,
    name: str,
    *,
    maximum_items: int = 100,
    item_validator: Callable[[Any, str], str] | None = None,
) -> list[str]:
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        raise ContractError(f"{name} must be an array")
    if len(value) > maximum_items:
        raise ContractError(f"{name} exceeds {maximum_items} items")
    validate = item_validator or (lambda item, item_name: _text(item, item_name))
    result = [validate(item, f"{name}[{index}]") for index, item in enumerate(value)]
    if len(set(result)) != len(result):
        raise ContractError(f"{name} contains duplicate values")
    return result


def _no_arguments(arguments: Mapping[str, Any]) -> dict[str, Any]:
    _exact_keys(arguments, required=set(), name="arguments")
    return {}


def _list_files(arguments: Mapping[str, Any]) -> dict[str, Any]:
    _exact_keys(arguments, required=set(), optional={"path", "max_results"}, name="arguments")
    return {
        "path": _relative_path(arguments.get("path", "."), "arguments.path"),
        "max_results": _integer(
            arguments.get("max_results", 200), "arguments.max_results", minimum=1, maximum=10_000
        ),
    }


def _read_file(arguments: Mapping[str, Any]) -> dict[str, Any]:
    _exact_keys(
        arguments,
        required={"path"},
        optional={"start_line", "end_line", "max_bytes"},
        name="arguments",
    )
    start = _integer(arguments.get("start_line", 1), "arguments.start_line", minimum=1)
    end_value = arguments.get("end_line")
    end = None if end_value is None else _integer(end_value, "arguments.end_line", minimum=1)
    if end is not None and end < start:
        raise ContractError("arguments.end_line must not precede start_line")
    return {
        "path": _relative_path(arguments["path"], "arguments.path"),
        "start_line": start,
        "end_line": end,
        "max_bytes": _integer(
            arguments.get("max_bytes", 262_144), "arguments.max_bytes", minimum=1, maximum=2_000_000
        ),
    }


def _search_text(arguments: Mapping[str, Any]) -> dict[str, Any]:
    _exact_keys(
        arguments,
        required={"query"},
        optional={"paths", "case_sensitive", "max_results"},
        name="arguments",
    )
    case_sensitive = arguments.get("case_sensitive", False)
    if not isinstance(case_sensitive, bool):
        raise ContractError("arguments.case_sensitive must be a boolean")
    return {
        "query": _text(arguments["query"], "arguments.query", maximum=4096),
        "paths": _string_list(
            arguments.get("paths", ["."]),
            "arguments.paths",
            item_validator=_relative_path,
        ),
        "case_sensitive": case_sensitive,
        "max_results": _integer(
            arguments.get("max_results", 50), "arguments.max_results", minimum=1, maximum=1_000
        ),
    }


def _search_knowledge(arguments: Mapping[str, Any]) -> dict[str, Any]:
    _exact_keys(
        arguments,
        required={"query"},
        optional={"scopes", "limit"},
        name="arguments",
    )
    return {
        "query": _text(arguments["query"], "arguments.query", maximum=4096),
        "scopes": _string_list(arguments.get("scopes", []), "arguments.scopes", maximum_items=50),
        "limit": _integer(arguments.get("limit", 20), "arguments.limit", minimum=1, maximum=200),
    }


def _patch_operation(value: Any, name: str) -> dict[str, Any]:
    operation = _mapping(value, name)
    _exact_keys(
        operation,
        required={"kind", "path"},
        optional={"before_digest", "content", "new_path"},
        name=name,
    )
    kind = _text(operation["kind"], f"{name}.kind", maximum=16).upper()
    if kind not in {"CREATE", "MODIFY", "DELETE", "RENAME"}:
        raise ContractError(f"{name}.kind is not supported")
    before = operation.get("before_digest")
    content = operation.get("content")
    new_path = operation.get("new_path")
    if before is not None:
        before = _text(before, f"{name}.before_digest", maximum=80)
    if content is not None:
        content = _text(content, f"{name}.content", maximum=2_000_000, allow_empty=True)
    if new_path is not None:
        new_path = _relative_path(new_path, f"{name}.new_path")
    if kind == "CREATE" and (before is not None or content is None):
        raise ContractError(f"{name}: CREATE requires content and forbids before_digest")
    if kind == "MODIFY" and (before is None or content is None):
        raise ContractError(f"{name}: MODIFY requires before_digest and content")
    if kind == "DELETE" and (before is None or content is not None or new_path is not None):
        raise ContractError(f"{name}: DELETE requires only before_digest")
    if kind == "RENAME" and (before is None or new_path is None or content is not None):
        raise ContractError(f"{name}: RENAME requires before_digest and new_path")
    return {
        "kind": kind,
        "path": _relative_path(operation["path"], f"{name}.path"),
        **({"before_digest": before} if before is not None else {}),
        **({"content": content} if content is not None else {}),
        **({"new_path": new_path} if new_path is not None else {}),
    }


def _prepare_patch(arguments: Mapping[str, Any]) -> dict[str, Any]:
    _exact_keys(arguments, required={"operations"}, name="arguments")
    raw = arguments["operations"]
    if isinstance(raw, (str, bytes)) or not isinstance(raw, Sequence):
        raise ContractError("arguments.operations must be an array")
    if not 1 <= len(raw) <= 100:
        raise ContractError("arguments.operations must contain 1 to 100 operations")
    operations = [_patch_operation(item, f"arguments.operations[{index}]") for index, item in enumerate(raw)]
    targets: list[str] = []
    for operation in operations:
        targets.append(operation["path"])
        if "new_path" in operation:
            targets.append(operation["new_path"])
    if len(set(targets)) != len(targets):
        raise ContractError("arguments.operations address the same path more than once")
    return {"operations": operations}


def _identifier_fields(arguments: Mapping[str, Any], *fields: str) -> dict[str, Any]:
    _exact_keys(arguments, required=set(fields), name="arguments")
    return {field: _identifier(arguments[field], f"arguments.{field}") for field in fields}


def _ask_user(arguments: Mapping[str, Any]) -> dict[str, Any]:
    _exact_keys(arguments, required={"question"}, optional={"choices"}, name="arguments")
    result: dict[str, Any] = {"question": _text(arguments["question"], "arguments.question", maximum=4000)}
    if "choices" in arguments:
        choices = _string_list(arguments["choices"], "arguments.choices", maximum_items=10)
        if len(choices) < 2:
            raise ContractError("arguments.choices must contain at least two choices")
        result["choices"] = choices
    return result


def _submit_result(arguments: Mapping[str, Any]) -> dict[str, Any]:
    _exact_keys(
        arguments,
        required={"artifact_ids", "summary", "risks", "citations"},
        name="arguments",
    )
    artifact_ids = _string_list(arguments["artifact_ids"], "arguments.artifact_ids", maximum_items=500)
    if not artifact_ids:
        raise ContractError("arguments.artifact_ids must contain at least one artifact")
    return {
        "artifact_ids": artifact_ids,
        "summary": _text(arguments["summary"], "arguments.summary", maximum=10_000),
        "risks": _string_list(arguments["risks"], "arguments.risks", maximum_items=100),
        "citations": _string_list(arguments["citations"], "arguments.citations", maximum_items=500),
    }


def _abort(arguments: Mapping[str, Any]) -> dict[str, Any]:
    _exact_keys(arguments, required={"reason"}, name="arguments")
    return {"reason": _text(arguments["reason"], "arguments.reason", maximum=2000)}


_ACTION_VALIDATORS: dict[str, Callable[[Mapping[str, Any]], dict[str, Any]]] = {
    "REPOSITORY_STATUS": _no_arguments,
    "LIST_FILES": _list_files,
    "READ_FILE": _read_file,
    "SEARCH_TEXT": _search_text,
    "SEARCH_KNOWLEDGE": _search_knowledge,
    "PREPARE_PATCH": _prepare_patch,
    "APPLY_PATCH": lambda arguments: _identifier_fields(
        arguments, "patch_id", "approval_id", "operation_id"
    ),
    "RUN_CHECK": lambda arguments: _identifier_fields(arguments, "check_id", "operation_id"),
    "SHOW_DIFF": _no_arguments,
    "RESTORE_CHANGE_SET": lambda arguments: _identifier_fields(
        arguments, "change_set_id", "operation_id"
    ),
    "ASK_USER": _ask_user,
    "SUBMIT_RESULT": _submit_result,
    "ABORT": _abort,
}


def parse_action(value: Mapping[str, Any]) -> Action:
    action = _mapping(value, "action")
    _exact_keys(
        action,
        required={"contract_version", "action_id", "kind", "arguments", "purpose"},
        name="action",
    )
    version = _text(action["contract_version"], "action.contract_version", maximum=16)
    if version != ACTION_CONTRACT_VERSION:
        raise ContractError(f"unsupported action contract version: {version}")
    kind = _text(action["kind"], "action.kind", maximum=64).upper()
    validator = _ACTION_VALIDATORS.get(kind)
    if validator is None:
        raise ContractError(f"unknown action kind: {kind}")
    arguments = validator(_mapping(action["arguments"], "action.arguments"))
    return Action(
        contract_version=version,
        action_id=_identifier(action["action_id"], "action.action_id"),
        kind=kind,
        arguments=arguments,
        purpose=_text(action["purpose"], "action.purpose", maximum=4000),
    )


def action_to_dict(action: Action) -> dict[str, Any]:
    return {
        "contract_version": action.contract_version,
        "action_id": action.action_id,
        "kind": action.kind,
        "arguments": dict(action.arguments),
        "purpose": action.purpose,
    }


def parse_model_event(value: Mapping[str, Any]) -> ModelEvent:
    event = _mapping(value, "model event")
    _exact_keys(
        event,
        required={"contract_version", "kind", "sequence", "payload"},
        name="model event",
    )
    version = _text(event["contract_version"], "model event.contract_version", maximum=16)
    if version != MODEL_EVENT_CONTRACT_VERSION:
        raise ContractError(f"unsupported model event contract version: {version}")
    kind = _text(event["kind"], "model event.kind", maximum=64).upper()
    sequence = _integer(event["sequence"], "model event.sequence", maximum=10_000_000)
    payload = _mapping(event["payload"], "model event.payload")

    normalized: dict[str, Any]
    if kind == "TEXT_DELTA":
        _exact_keys(payload, required={"text"}, name="model event.payload")
        normalized = {"text": _text(payload["text"], "payload.text", maximum=1_000_000, allow_empty=True)}
    elif kind == "ACTION_DELTA":
        _exact_keys(payload, required={"action_id", "delta"}, name="model event.payload")
        normalized = {
            "action_id": _identifier(payload["action_id"], "payload.action_id"),
            "delta": _text(payload["delta"], "payload.delta", maximum=1_000_000, allow_empty=True),
        }
    elif kind == "ACTION_COMPLETE":
        _exact_keys(payload, required={"action"}, name="model event.payload")
        normalized = {"action": action_to_dict(parse_action(_mapping(payload["action"], "payload.action")))}
    elif kind == "USAGE":
        _exact_keys(
            payload,
            required={"input_tokens", "output_tokens", "cost_microunits"},
            name="model event.payload",
        )
        normalized = {
            field: _integer(payload[field], f"payload.{field}", maximum=10_000_000_000)
            for field in ("input_tokens", "output_tokens", "cost_microunits")
        }
    elif kind == "COMPLETED":
        _exact_keys(payload, required=set(), optional={"finish_reason"}, name="model event.payload")
        normalized = {}
        if "finish_reason" in payload:
            normalized["finish_reason"] = _text(payload["finish_reason"], "payload.finish_reason", maximum=128)
    elif kind == "ERROR":
        _exact_keys(payload, required={"code", "message"}, optional={"retryable"}, name="model event.payload")
        retryable = payload.get("retryable", False)
        if not isinstance(retryable, bool):
            raise ContractError("payload.retryable must be a boolean")
        normalized = {
            "code": _identifier(payload["code"], "payload.code"),
            "message": _text(payload["message"], "payload.message", maximum=10_000),
            "retryable": retryable,
        }
    else:
        raise ContractError(f"unknown model event kind: {kind}")
    return ModelEvent(kind=kind, sequence=sequence, payload=normalized)


def model_event_to_dict(event: ModelEvent) -> dict[str, Any]:
    return {
        "contract_version": MODEL_EVENT_CONTRACT_VERSION,
        "kind": event.kind,
        "sequence": event.sequence,
        "payload": dict(event.payload),
    }


def model_request_to_dict(request: ModelRequest) -> dict[str, Any]:
    _identifier(request.request_id, "request.request_id")
    _identifier(request.session_id, "request.session_id")
    _text(request.task, "request.task", maximum=100_000)
    for name, values in (
        ("instruction_blocks", request.instruction_blocks),
        ("context_items", request.context_items),
        ("tool_definitions", request.tool_definitions),
    ):
        for index, value in enumerate(values):
            _mapping(value, f"request.{name}[{index}]")
    if request.deadline_epoch_ms is not None:
        _integer(request.deadline_epoch_ms, "request.deadline_epoch_ms", maximum=10**16)
    return {
        "request_id": request.request_id,
        "session_id": request.session_id,
        "task": request.task,
        "instruction_blocks": [dict(value) for value in request.instruction_blocks],
        "context_items": [dict(value) for value in request.context_items],
        "tool_definitions": [dict(value) for value in request.tool_definitions],
        "deadline_epoch_ms": request.deadline_epoch_ms,
    }
