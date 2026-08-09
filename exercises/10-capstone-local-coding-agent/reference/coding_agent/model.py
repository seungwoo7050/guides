from __future__ import annotations

import json
import re
import time
import urllib.error
import urllib.request
from collections.abc import Iterable, Iterator, Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable
from urllib.parse import urlparse

from .contracts import (
    ACTION_CONTRACT_VERSION,
    MODEL_EVENT_CONTRACT_VERSION,
    action_to_dict,
    model_event_to_dict,
    model_request_to_dict,
    parse_action as _parse_action,
    parse_model_event,
)
from .errors import ContractError
from .types import Action, ModelEvent, ModelRequest
from .util import canonical_json, value_digest


def parse_action(value: Mapping[str, Any]) -> Action:
    """Parse one strict, versioned model action.

    Kept in this module as the runtime-facing entrypoint; the schema details live
    in :mod:`coding_agent.contracts` so tools and tests use the same contract.
    """

    return _parse_action(value)


@runtime_checkable
class ModelAdapter(Protocol):
    def stream(self, request: ModelRequest) -> Iterator[ModelEvent]:
        """Yield one validated event stream for ``request``."""


@dataclass(frozen=True)
class HttpTransportResponse:
    status: int
    headers: Mapping[str, str]
    body: bytes


class HttpTransport(Protocol):
    def __call__(
        self,
        endpoint: str,
        body: bytes,
        headers: Mapping[str, str],
        timeout_seconds: float,
    ) -> HttpTransportResponse | tuple[int, Mapping[str, str], bytes] | Mapping[str, Any]: ...


_TERMINAL = {"COMPLETED", "ERROR"}


def _event(value: ModelEvent | Mapping[str, Any]) -> ModelEvent:
    if isinstance(value, ModelEvent):
        return parse_model_event(model_event_to_dict(value))
    return parse_model_event(value)


def validate_event_stream(events: Sequence[ModelEvent], request: ModelRequest) -> tuple[ModelEvent, ...]:
    if not events:
        raise ContractError("model returned an empty event stream")
    expected_sequence = 0
    terminal_seen = False
    action_count = 0
    usage_count = 0
    action_delta_id: str | None = None
    completed_action_id: str | None = None
    normalized: list[ModelEvent] = []
    for index, raw_event in enumerate(events):
        event = _event(raw_event)
        if event.sequence != expected_sequence:
            raise ContractError(
                f"model event sequence must be contiguous from zero; expected {expected_sequence}, got {event.sequence}"
            )
        expected_sequence += 1
        if terminal_seen:
            raise ContractError("model emitted an event after a terminal event")
        if event.kind == "ACTION_COMPLETE":
            action_count += 1
            completed_action_id = str(event.payload["action"]["action_id"])
            if action_delta_id is not None and completed_action_id != action_delta_id:
                raise ContractError("ACTION_DELTA and ACTION_COMPLETE refer to different action IDs")
        elif event.kind == "ACTION_DELTA":
            if action_count:
                raise ContractError("ACTION_DELTA may not follow ACTION_COMPLETE")
            current_id = str(event.payload["action_id"])
            if action_delta_id is None:
                action_delta_id = current_id
            elif action_delta_id != current_id:
                raise ContractError("one model turn may not interleave action deltas for different IDs")
        elif event.kind == "USAGE":
            usage_count += 1
            if usage_count > 1:
                raise ContractError("model stream contains more than one USAGE event")
        if event.kind in _TERMINAL:
            terminal_seen = True
            if index != len(events) - 1:
                raise ContractError("terminal model event must be last")
        normalized.append(event)
    if not terminal_seen:
        raise ContractError("model stream lacks a terminal event")
    terminal = normalized[-1].kind
    if terminal == "COMPLETED" and action_count != 1:
        raise ContractError("a successful model turn must contain exactly one ACTION_COMPLETE event")
    if terminal == "ERROR" and action_count:
        raise ContractError("a failed model turn may not publish an action")
    return tuple(normalized)


def action_event_stream(
    request: ModelRequest,
    action: Action | Mapping[str, Any],
    *,
    text: str | None = None,
    usage: Mapping[str, int] | None = None,
    model: str = "scripted",
) -> tuple[ModelEvent, ...]:
    parsed = action if isinstance(action, Action) else parse_action(action)
    sequence = 0
    events: list[Mapping[str, Any]] = []
    if text is not None:
        events.append(
            {
                "contract_version": MODEL_EVENT_CONTRACT_VERSION,
                "kind": "TEXT_DELTA",
                "sequence": sequence,
                "payload": {"text": text},
            }
        )
        sequence += 1
    events.append(
        {
            "contract_version": MODEL_EVENT_CONTRACT_VERSION,
            "kind": "ACTION_COMPLETE",
            "sequence": sequence,
            "payload": {"action": action_to_dict(parsed)},
        }
    )
    sequence += 1
    if usage is not None:
        events.append(
            {
                "contract_version": MODEL_EVENT_CONTRACT_VERSION,
                "kind": "USAGE",
                "sequence": sequence,
                "payload": dict(usage),
            }
        )
        sequence += 1
    events.append(
        {
            "contract_version": MODEL_EVENT_CONTRACT_VERSION,
            "kind": "COMPLETED",
            "sequence": sequence,
            "payload": {"finish_reason": "action"},
        }
    )
    return validate_event_stream(tuple(parse_model_event(item) for item in events), request)


class ScriptedModelAdapter:
    """Deterministic adapter for runtime, policy, failure, and resume tests.

    Scripts may be keyed by request ID or supplied as a sequence of turns. A
    turn can be a strict action mapping, ``{"action": ..., "text": ...}``, or
    a complete sequence of strict model-event mappings.
    """

    def __init__(
        self,
        scripts: Mapping[str, Any] | Sequence[Any],
        *,
        model_name: str = "scripted",
        allow_replay: bool = False,
    ) -> None:
        self._model_name = model_name
        self._allow_replay = allow_replay
        self._used: set[str] = set()
        self._position = 0
        if isinstance(scripts, Mapping):
            self._by_request: dict[str, Any] | None = dict(scripts)
            self._turns: tuple[Any, ...] = ()
        else:
            self._by_request = None
            self._turns = tuple(scripts)

    def _script_for(self, request: ModelRequest) -> Any:
        if self._by_request is not None:
            if request.request_id not in self._by_request:
                raise ContractError(f"no scripted response for request {request.request_id}")
            if not self._allow_replay and request.request_id in self._used:
                raise ContractError(f"scripted response already consumed for request {request.request_id}")
            self._used.add(request.request_id)
            return self._by_request[request.request_id]
        if self._position >= len(self._turns):
            raise ContractError("scripted model has no remaining turns")
        turn = self._turns[self._position]
        self._position += 1
        return turn

    @property
    def position(self) -> int:
        return len(self._used) if self._by_request is not None else self._position

    def restore_position(self, position: int) -> None:
        if isinstance(position, bool) or not isinstance(position, int) or position < 0:
            raise ContractError("scripted model position must be a non-negative integer")
        if self._by_request is not None:
            if position != 0:
                raise ContractError("request-ID scripts cannot restore a durable sequence position")
            self._used.clear()
            return
        if position > len(self._turns):
            raise ContractError("scripted model position exceeds the available turns")
        self._position = position

    @staticmethod
    def _last_tool_receipt(request: ModelRequest) -> Mapping[str, Any] | None:
        for item in reversed(request.context_items):
            if item.get("kind") == "TOOL_RECEIPT":
                return item
        return None

    @staticmethod
    def _check_expectation(expect: Any, last_tool: Mapping[str, Any] | None) -> None:
        if not isinstance(expect, Mapping):
            raise ContractError("scripted expect must be an object")
        required = {"tool", "status"}
        optional = {"observation_digest"}
        missing = required - set(expect)
        extra = set(expect) - required - optional
        if missing or extra:
            detail = []
            if missing:
                detail.append("missing " + ", ".join(sorted(missing)))
            if extra:
                detail.append("unknown " + ", ".join(sorted(extra)))
            raise ContractError("invalid scripted expect: " + "; ".join(detail))
        if last_tool is None:
            raise ContractError("script expected a prior TOOL_RECEIPT")
        for field in ("tool", "status"):
            if not isinstance(expect[field], str) or not expect[field]:
                raise ContractError(f"scripted expect.{field} must be a non-empty string")
            if last_tool.get(field) != expect[field]:
                raise ContractError(
                    f"scripted expect.{field} mismatch: expected {expect[field]!r}, got {last_tool.get(field)!r}"
                )
        if "observation_digest" in expect:
            digest = expect["observation_digest"]
            if not isinstance(digest, str) or not digest:
                raise ContractError("scripted expect.observation_digest must be a non-empty string")
            actual = value_digest(dict(last_tool))
            if digest != actual:
                raise ContractError("scripted observation digest mismatch")

    _PLACEHOLDER = re.compile(r"\$\{last_tool((?:\.[A-Za-z0-9_-]+)+)\}")

    @classmethod
    def _resolve_placeholders(cls, value: Any, last_tool: Mapping[str, Any] | None) -> Any:
        if isinstance(value, Mapping):
            return {key: cls._resolve_placeholders(item, last_tool) for key, item in value.items()}
        if isinstance(value, list):
            return [cls._resolve_placeholders(item, last_tool) for item in value]
        if isinstance(value, tuple):
            return tuple(cls._resolve_placeholders(item, last_tool) for item in value)
        if not isinstance(value, str) or "${last_tool" not in value:
            return value
        if last_tool is None:
            raise ContractError("script placeholder requires a prior TOOL_RECEIPT")

        def lookup(match: re.Match[str]) -> Any:
            current: Any = last_tool
            for component in match.group(1).lstrip(".").split("."):
                if isinstance(current, Mapping) and component in current:
                    current = current[component]
                    continue
                if (
                    isinstance(current, Sequence)
                    and not isinstance(current, (str, bytes))
                    and component.isdigit()
                    and int(component) < len(current)
                ):
                    current = current[int(component)]
                    continue
                else:
                    raise ContractError(f"script placeholder does not exist: {match.group(0)}")
            return current

        full = cls._PLACEHOLDER.fullmatch(value)
        if full:
            return lookup(full)

        def replace(match: re.Match[str]) -> str:
            resolved = lookup(match)
            if isinstance(resolved, (Mapping, list, tuple)):
                raise ContractError("structured placeholder values must occupy the entire string")
            return str(resolved)

        replaced = cls._PLACEHOLDER.sub(replace, value)
        if "${last_tool" in replaced:
            raise ContractError("script contains an invalid last_tool placeholder")
        return replaced

    def _events_for(self, request: ModelRequest, script: Any) -> tuple[ModelEvent, ...]:
        if isinstance(script, Action):
            return action_event_stream(request, script, model=self._model_name)
        if isinstance(script, Mapping):
            if "events" in script:
                if set(script) != {"events"}:
                    raise ContractError("script event envelope has unknown fields")
                script = script["events"]
            elif "action" in script:
                allowed = {"action", "text", "usage", "expect"}
                extra = set(script) - allowed
                if extra:
                    raise ContractError(f"scripted turn has unknown fields: {', '.join(sorted(extra))}")
                last_tool = self._last_tool_receipt(request)
                if "expect" in script:
                    self._check_expectation(script["expect"], last_tool)
                return action_event_stream(
                    request,
                    self._resolve_placeholders(script["action"], last_tool),
                    text=script.get("text"),
                    usage=script.get("usage"),
                    model=self._model_name,
                )
            elif {"contract_version", "action_id", "kind", "arguments", "purpose"} == set(script):
                return action_event_stream(request, script, model=self._model_name)
        if isinstance(script, (str, bytes)) or not isinstance(script, Iterable):
            raise ContractError("scripted turn must be an action or event sequence")
        return validate_event_stream(tuple(_event(value) for value in script), request)

    def stream(self, request: ModelRequest) -> Iterator[ModelEvent]:
        yield from self._events_for(request, self._script_for(request))


def _urllib_transport(
    endpoint: str,
    body: bytes,
    headers: Mapping[str, str],
    timeout_seconds: float,
) -> HttpTransportResponse:
    request = urllib.request.Request(endpoint, data=body, headers=dict(headers), method="POST")
    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            return HttpTransportResponse(
                status=response.status,
                headers={key.lower(): value for key, value in response.headers.items()},
                body=response.read(),
            )
    except urllib.error.HTTPError as error:
        return HttpTransportResponse(
            status=error.code,
            headers={key.lower(): value for key, value in error.headers.items()},
            body=error.read(),
        )
    except (urllib.error.URLError, TimeoutError, OSError) as error:
        raise ContractError(f"model transport failed: {error}") from error


class HttpModelAdapter:
    """Small HTTP adapter with an injectable transport and safe loopback default.

    The endpoint returns a JSON object with only an ``events`` array. Each event
    uses the same strict contract as ``ScriptedModelAdapter``. Remote endpoints
    require an explicit ``allow_remote=True`` decision.
    """

    def __init__(
        self,
        endpoint: str,
        *,
        model_name: str,
        transport: HttpTransport | None = None,
        api_key: str | None = None,
        timeout_seconds: float = 10.0,
        max_response_bytes: int = 2_000_000,
        allow_remote: bool = False,
    ) -> None:
        parsed = urlparse(endpoint)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            raise ValueError("model endpoint must be an absolute HTTP(S) URL")
        is_loopback = parsed.hostname.lower() in {"localhost", "127.0.0.1", "::1"}
        if not allow_remote and not is_loopback:
            raise ValueError("remote model endpoints require allow_remote=True")
        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")
        if max_response_bytes <= 0:
            raise ValueError("max_response_bytes must be positive")
        self._endpoint = endpoint
        self._model_name = model_name
        self._transport = transport or _urllib_transport
        self._api_key = api_key
        self._timeout_seconds = timeout_seconds
        self._max_response_bytes = max_response_bytes

    @staticmethod
    def _coerce_response(
        value: HttpTransportResponse | tuple[int, Mapping[str, str], bytes] | Mapping[str, Any],
    ) -> HttpTransportResponse:
        if isinstance(value, HttpTransportResponse):
            return value
        if isinstance(value, Mapping):
            return HttpTransportResponse(
                status=200,
                headers={"content-type": "application/json"},
                body=(canonical_json(value) + "\n").encode("utf-8"),
            )
        if isinstance(value, tuple) and len(value) == 3:
            status, headers, body = value
            if not isinstance(status, int) or not isinstance(headers, Mapping) or not isinstance(body, bytes):
                raise ContractError("injected model transport returned an invalid tuple")
            return HttpTransportResponse(status=status, headers=headers, body=body)
        raise ContractError("injected model transport returned an unsupported response")

    def stream(self, request: ModelRequest) -> Iterator[ModelEvent]:
        timeout = self._timeout_seconds
        if request.deadline_epoch_ms is not None:
            remaining = (request.deadline_epoch_ms - int(time.time() * 1000)) / 1000
            if remaining <= 0:
                raise ContractError("model request deadline has expired")
            timeout = min(timeout, remaining)
        envelope = {
            "contract_version": MODEL_EVENT_CONTRACT_VERSION,
            "action_contract_version": ACTION_CONTRACT_VERSION,
            "model": self._model_name,
            "request": model_request_to_dict(request),
        }
        headers = {"Content-Type": "application/json", "Accept": "application/json"}
        if self._api_key is not None:
            headers["Authorization"] = f"Bearer {self._api_key}"
        response = self._coerce_response(
            self._transport(
                self._endpoint,
                (canonical_json(envelope) + "\n").encode("utf-8"),
                headers,
                timeout,
            )
        )
        if not 200 <= response.status < 300:
            raise ContractError(f"model endpoint returned HTTP {response.status}")
        if len(response.body) > self._max_response_bytes:
            raise ContractError("model response exceeds the configured byte limit")
        content_type = next(
            (value for key, value in response.headers.items() if key.lower() == "content-type"),
            "application/json",
        )
        if "application/json" not in content_type.lower():
            raise ContractError("model endpoint did not return application/json")
        try:
            decoded = json.loads(response.body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise ContractError("model endpoint returned invalid JSON") from error
        if not isinstance(decoded, Mapping) or set(decoded) != {"events"}:
            raise ContractError("model response must contain only an events array")
        raw_events = decoded["events"]
        if isinstance(raw_events, (str, bytes)) or not isinstance(raw_events, Sequence):
            raise ContractError("model response events must be an array")
        events = validate_event_stream(tuple(_event(value) for value in raw_events), request)
        yield from events
