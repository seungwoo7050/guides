from __future__ import annotations

import time
import uuid
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any, Protocol

from .budget import BudgetLedger
from .checkpoint import CheckpointStore
from .errors import AgentError, BudgetExceeded, ContractError, PolicyDenied
from .loop import IterationTracker
from .model import ModelAdapter, parse_action
from .trace import EventLog
from .types import CommandResult, ModelRequest, RunBudget, RunResult, ToolRequest, UsageReceipt
from .util import value_digest


class ToolInvoker(Protocol):
    def invoke(self, request: ToolRequest): ...


class InjectedCrash(RuntimeError):
    """A deliberate crash point used by the durable-session exercises."""


TOOL_ACTIONS = {
    "REPOSITORY_STATUS": "repository_status",
    "LIST_FILES": "list_files",
    "READ_FILE": "read_file",
    "SEARCH_TEXT": "search_text",
    "SEARCH_KNOWLEDGE": "search_knowledge",
    "SHOW_DIFF": "show_diff",
    "PREPARE_PATCH": "prepare_patch",
    "APPLY_PATCH": "apply_patch",
    "RUN_CHECK": "run_check",
    "RESTORE_CHANGE_SET": "restore_change_set",
}

TERMINAL = {"SUCCEEDED", "FAILED", "POLICY_BLOCKED", "BUDGET_EXHAUSTED", "CANCELLED"}


class AgentRuntime:
    """A provider-neutral model/action/tool loop with durable evidence."""

    def __init__(
        self,
        *,
        model: ModelAdapter,
        tools: ToolInvoker,
        state_dir: Path,
        principal: str,
        task: str,
        budget: RunBudget | None = None,
        session_id: str | None = None,
        verifier: Callable[[tuple[str, ...], tuple[Mapping[str, Any], ...]], Mapping[str, Any]] | None = None,
        crash_after: str | None = None,
    ) -> None:
        self.model = model
        self.tools = tools
        self.state_dir = state_dir.resolve()
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.principal = principal
        self.task = task
        self.session_id = session_id or "session-" + uuid.uuid4().hex
        self.verifier = verifier
        self.crash_after = crash_after
        self.cancel_requested = False
        self.iterations = IterationTracker()
        self.event_log = EventLog(self.state_dir / "events.jsonl", session_id=self.session_id)
        self.checkpoints = CheckpointStore(self.state_dir / "checkpoint.json")
        self.budget = BudgetLedger(budget)
        self.state: dict[str, Any] = {
            "session_id": self.session_id,
            "task": task,
            "status": "CREATED",
            "step": 0,
            "observations": [],
            "artifacts": [],
            "last_action_id": None,
            "model_position": 0,
        }
        self._event("SESSION_CREATED", {"task_digest": self._digest_text(task), "principal": principal})
        self._checkpoint()

    @staticmethod
    def _digest_text(value: str) -> str:
        from .util import sha256_text

        return sha256_text(value)

    def _event(self, event_type: str, payload: Mapping[str, Any] | None = None) -> None:
        self.event_log.append(event_type, payload)
        if self.crash_after == event_type:
            raise InjectedCrash(f"crash after {event_type}")

    def _checkpoint(self) -> None:
        position = getattr(self.model, "position", self.state.get("model_position", 0))
        self.state["model_position"] = int(position)
        self.state["budget"] = self.budget.to_mapping()
        self.checkpoints.save(self.state, event_head=self.event_log.head)

    def _model_request(self) -> ModelRequest:
        return ModelRequest(
            request_id=f"{self.session_id}:model:{self.state['step'] + 1}",
            session_id=self.session_id,
            task=self.task,
            instruction_blocks=(
                {"origin": "SYSTEM_POLICY", "trust": "AUTHORITY", "text": "Use only published actions and tools."},
                {"origin": "USER", "trust": "AUTHORITY", "text": self.task},
            ),
            context_items=tuple(self.state["observations"][-20:]),
            tool_definitions=tuple({"id": item} for item in TOOL_ACTIONS.values()),
            deadline_epoch_ms=int((time.time() + max(0.0, self.budget.remaining()["wall_seconds"])) * 1000),
        )

    def _next_action(self):
        self.budget.reserve_model_call()
        complete: list[Mapping[str, Any]] = []
        for event in self.model.stream(self._model_request()):
            self._event("MODEL_EVENT", {"kind": event.kind, "sequence": event.sequence, "payload": event.payload})
            if event.kind == "USAGE":
                self.budget.record_usage(
                    UsageReceipt(
                        input_tokens=int(event.payload.get("input_tokens", 0)),
                        output_tokens=int(event.payload.get("output_tokens", 0)),
                        cost_microunits=int(event.payload.get("cost_microunits", 0)),
                    )
                )
            elif event.kind == "ACTION_COMPLETE":
                action = event.payload.get("action")
                if not isinstance(action, Mapping):
                    raise ContractError("ACTION_COMPLETE requires an action mapping")
                complete.append(action)
            elif event.kind == "ERROR":
                raise ContractError(f"model adapter error: {event.payload.get('code', 'UNKNOWN')}")
        if len(complete) != 1:
            raise ContractError("each model turn must produce exactly one complete action")
        return parse_action(complete[0])

    def _record_tool_receipt(self, tool: str, receipt) -> None:
        encoded_size = len(str(receipt.output).encode("utf-8"))
        if tool in {"read_file", "search_text", "search_knowledge", "list_files"}:
            self.budget.record_read_bytes(encoded_size)
        observation = {
            "kind": "TOOL_RECEIPT",
            "tool": receipt.tool,
            "status": receipt.status,
            "receipt_id": receipt.receipt_id,
            "resource": receipt.resource,
            "output": dict(receipt.output),
            "duplicate": receipt.duplicate,
        }
        if tool == "run_check":
            command_result = CommandResult(
                **{key: receipt.output[key] for key in CommandResult.__dataclass_fields__}
            )
            classification = self.iterations.record(command_result)
            observation["classification"] = classification
            self.budget.record_command_seconds(command_result.duration_ms / 1000)
            self._event(
                "CHECK_CLASSIFIED",
                {
                    "command_id": command_result.command_id,
                    "classification": classification,
                    "plan_revision": self.iterations.plan_revision,
                },
            )
        self.state["observations"].append(observation)
        self.state["artifacts"].append(receipt.receipt_id)
        event_payload: dict[str, Any] = {
            "tool": receipt.tool,
            "receipt_id": receipt.receipt_id,
            "status": receipt.status,
            "effect": receipt.effect,
            "resource": receipt.resource,
            "output_digest": value_digest(dict(receipt.output)),
            "duplicate": receipt.duplicate,
        }
        if tool == "search_knowledge":
            scopes = receipt.output.get("scopes", ())
            matches = receipt.output.get("matches", ())
            source_refs: list[dict[str, Any]] = []
            if isinstance(matches, (list, tuple)):
                for match in matches:
                    reference = match.get("reference") if isinstance(match, Mapping) else None
                    if not isinstance(reference, Mapping):
                        continue
                    fields = (
                        "source_id",
                        "origin",
                        "location",
                        "revision",
                        "digest",
                        "trust",
                        "scope",
                        "freshness",
                        "retrieved_at",
                    )
                    if all(field in reference for field in fields):
                        source_refs.append({field: reference[field] for field in fields})
            event_payload["authorized_scopes"] = tuple(scopes) if isinstance(scopes, (list, tuple)) else ()
            event_payload["source_refs"] = tuple(source_refs)
        self._event("TOOL_COMPLETED", event_payload)

    def run(self) -> RunResult:
        if self.state["status"] in TERMINAL:
            return self.result()
        self.state["status"] = "RUNNING"
        while self.state["status"] == "RUNNING":
            if self.cancel_requested or (self.state_dir / "cancel.requested").exists():
                self.state["status"] = "CANCELLED"
                self._event("SESSION_CANCELLED", {})
                self._checkpoint()
                break
            try:
                self.budget.reserve_step()
                self.state["step"] += 1
                action = self._next_action()
                if self.state.get("last_action_id") == action.action_id:
                    raise ContractError("action ID was replayed")
                self.state["last_action_id"] = action.action_id
                self._event(
                    "ACTION_ACCEPTED",
                    {"action_id": action.action_id, "kind": action.kind, "purpose": action.purpose},
                )

                if action.kind == "ASK_USER":
                    self.state["status"] = "WAITING_USER"
                    self._event("USER_INPUT_REQUIRED", {"question": action.arguments["question"]})
                    self._checkpoint()
                    break
                if action.kind == "ABORT":
                    self.state["status"] = "CANCELLED"
                    self._event("MODEL_ABORTED", {})
                    self._checkpoint()
                    break
                if action.kind == "SUBMIT_RESULT":
                    artifacts = tuple(str(item) for item in action.arguments["artifact_ids"])
                    if not artifacts:
                        raise ContractError("SUBMIT_RESULT requires evidence artifacts")
                    self.state["artifacts"] = list(artifacts)
                    report = self.verifier(artifacts, self.event_log.events) if self.verifier else {"passed": True}
                    self.state["verification"] = dict(report)
                    self.state["status"] = "SUCCEEDED" if report.get("passed") is True else "FAILED"
                    self._event("EXTERNAL_VERIFIER_COMPLETED", {"passed": report.get("passed") is True})
                    self._checkpoint()
                    break

                tool = TOOL_ACTIONS.get(action.kind)
                if tool is None:
                    raise ContractError(f"action has no runtime route: {action.kind}")
                writes = 1 if tool in {"apply_patch", "restore_change_set"} else 0
                self.budget.reserve_tool_call(writes=writes)
                arguments = dict(action.arguments)
                operation_id = arguments.pop("operation_id", None)
                approval_id = arguments.pop("approval_id", None)
                arguments["purpose"] = action.purpose
                tool_request = ToolRequest(
                    request_id=action.action_id,
                    principal=self.principal,
                    tool=tool,
                    arguments=arguments,
                    operation_id=operation_id,
                    approval_id=approval_id,
                )
                self.state["pending_effect"] = {
                    "request_id": tool_request.request_id,
                    "principal": tool_request.principal,
                    "tool": tool_request.tool,
                    "arguments": dict(tool_request.arguments),
                    "operation_id": tool_request.operation_id,
                    "approval_id": tool_request.approval_id,
                }
                # The intent and model cursor are durable before the effect.  A
                # completed operation can then be reconciled by operation_id.
                self._checkpoint()
                receipt = self.tools.invoke(tool_request)
                if self.crash_after == f"AFTER_EFFECT:{tool}":
                    raise InjectedCrash(f"crash after effect {tool}")
                self._record_tool_receipt(tool, receipt)
                self.state.pop("pending_effect", None)
                self._checkpoint()
            except BudgetExceeded as exc:
                self.state["status"] = "BUDGET_EXHAUSTED"
                self._event("BUDGET_EXHAUSTED", {"message": str(exc)})
                self._checkpoint()
            except PolicyDenied as exc:
                self.state["status"] = "POLICY_BLOCKED"
                self._event("POLICY_BLOCKED", {"message": str(exc)})
                self._checkpoint()
            except AgentError as exc:
                self.state["status"] = "FAILED"
                self._event("RUN_FAILED", {"error": type(exc).__name__, "message": str(exc)})
                self._checkpoint()
        return self.result()

    def provide_user_input(self, answer: str) -> None:
        if self.state["status"] != "WAITING_USER":
            raise ContractError("session is not waiting for user input")
        self.state["observations"].append(
            {"kind": "USER_INPUT", "digest": self._digest_text(answer), "text": answer}
        )
        self.state["status"] = "RUNNING"
        self._event("USER_INPUT_RECEIVED", {"answer_digest": self._digest_text(answer)})
        self._checkpoint()

    def cancel(self) -> None:
        self.cancel_requested = True

    def result(self) -> RunResult:
        return RunResult(
            session_id=self.session_id,
            state=self.state["status"],
            events=self.event_log.events,
            artifacts=tuple(self.state.get("artifacts", ())),
            verification=self.state.get("verification"),
        )

    @classmethod
    def resume(
        cls,
        *,
        model: ModelAdapter,
        tools: ToolInvoker,
        state_dir: Path,
        principal: str,
        verifier: Callable[[tuple[str, ...], tuple[Mapping[str, Any], ...]], Mapping[str, Any]] | None = None,
    ) -> "AgentRuntime":
        body = CheckpointStore(state_dir / "checkpoint.json").load()
        state = body["state"]
        runtime = cls.__new__(cls)
        runtime.model = model
        runtime.tools = tools
        runtime.state_dir = state_dir.resolve()
        runtime.principal = principal
        runtime.task = state["task"]
        runtime.session_id = state["session_id"]
        runtime.verifier = verifier
        runtime.crash_after = None
        runtime.cancel_requested = False
        runtime.iterations = IterationTracker()
        runtime.event_log = EventLog(state_dir / "events.jsonl", session_id=runtime.session_id)
        if body["event_head"] != runtime.event_log.head:
            raise ContractError("checkpoint and event log diverged")
        runtime.checkpoints = CheckpointStore(state_dir / "checkpoint.json")
        budget_mapping = dict(state.pop("budget"))
        runtime.budget = BudgetLedger.from_mapping(budget_mapping)
        runtime.state = state
        position = int(state.get("model_position", 0))
        if hasattr(model, "restore_position"):
            model.restore_position(position)
        runtime.state["status"] = "RUNNING"
        runtime._event("SESSION_RESUMED", {"model_position": position})
        pending = runtime.state.get("pending_effect")
        if pending:
            receipt = runtime.tools.invoke(ToolRequest(**pending))
            runtime._record_tool_receipt(str(pending["tool"]), receipt)
            runtime.state.pop("pending_effect", None)
            runtime._event(
                "EFFECT_RECONCILED",
                {"tool": pending["tool"], "receipt_id": receipt.receipt_id, "duplicate": receipt.duplicate},
            )
        runtime._checkpoint()
        return runtime
