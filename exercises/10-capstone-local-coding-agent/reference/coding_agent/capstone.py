"""Executable deterministic profile that composes the ten learning stages."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from dataclasses import asdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

from evaluator.harness import ExternalEvaluator, materialize_task
from evaluator.solutions import SOLUTIONS

from .git_adapter import GitAdapter
from .model import ScriptedModelAdapter
from .patching import PatchEngine
from .policy import ApprovalStore, PolicyEngine
from .process import CommandCatalog, CommandSpec, ProcessRunner
from .runtime import AgentRuntime, InjectedCrash
from .tools import ToolGateway
from .types import Approval, Grant, PatchOperation, RunBudget, RunResult
from .util import atomic_write_json, read_json, value_digest


ACTION_VERSION = "1.0"
PRINCIPAL = "coding-agent:fixture"
PURPOSE = "complete the reviewed local coding task"


def _git(cwd: Path, *arguments: str, input_bytes: bytes | None = None) -> bytes:
    completed = subprocess.run(
        ["git", "-C", str(cwd), *arguments],
        input=input_bytes,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        env={
            "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
            "LANG": "C",
            "LC_ALL": "C",
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_TERMINAL_PROMPT": "0",
        },
    )
    if completed.returncode != 0:
        raise RuntimeError(completed.stderr.decode("utf-8", "replace"))
    return completed.stdout


def create_agent_worktree(source: Path, destination: Path) -> Mapping[str, Any]:
    """Replay user state into a detached worktree without changing the source."""
    source_adapter = GitAdapter(source)
    baseline = source_adapter.snapshot()
    created = source_adapter.create_worktree(destination)

    tracked_delta = _git(source, "diff", "--binary", "HEAD", "--")
    if tracked_delta:
        _git(destination, "apply", "--whitespace=nowarn", "-", input_bytes=tracked_delta)
    for relative in baseline.untracked:
        origin = source / relative
        target = destination / relative
        if origin.is_symlink() or not origin.is_file():
            raise RuntimeError(f"initial untracked path is not a regular file: {relative}")
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(origin, target)
    # The index in this detached worktree is the immutable initial-user baseline.
    _git(destination, "add", "-A", "--")
    source_adapter.assert_snapshot(baseline)
    return {
        **dict(created),
        "source_root": str(source.resolve()),
        "source_snapshot_id": baseline.snapshot_id,
        "initial_user_paths": tuple(sorted(set(baseline.staged + baseline.unstaged + baseline.untracked))),
    }


def _action(number: int, kind: str, arguments: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "contract_version": ACTION_VERSION,
        "action_id": f"action-{number:03d}",
        "kind": kind,
        "arguments": dict(arguments),
        "purpose": PURPOSE,
    }


def _turn(
    number: int,
    kind: str,
    arguments: Mapping[str, Any],
    *,
    last_tool: str | None = None,
    last_status: str = "OK",
) -> dict[str, Any]:
    turn: dict[str, Any] = {
        "action": _action(number, kind, arguments),
        "usage": {"input_tokens": 12, "output_tokens": 8, "cost_microunits": 20},
    }
    if last_tool is not None:
        turn["expect"] = {"tool": last_tool, "status": last_status}
    return turn


def _operations(worktree: Path, content: Mapping[str, str]) -> list[dict[str, Any]]:
    engine = PatchEngine(worktree)
    operations: list[dict[str, Any]] = []
    for relative, final_content in content.items():
        before = engine.read(relative)
        operations.append(
            {
                "kind": "MODIFY",
                "path": relative,
                "before_digest": before["digest"],
                "content": final_content,
            }
        )
    return operations


def fixture_script(task_id: str, worktree: Path) -> tuple[dict[str, Any], ...]:
    """Build a deterministic script that still consumes every tool receipt."""
    number = 0
    turns: list[dict[str, Any]] = []

    def add(kind: str, arguments: Mapping[str, Any], last_tool: str | None = None) -> None:
        nonlocal number
        number += 1
        turns.append(_turn(number, kind, arguments, last_tool=last_tool))

    add("REPOSITORY_STATUS", {})
    add("LIST_FILES", {"path": ".", "max_results": 100}, "repository_status")

    if task_id == "token-expiry-boundary":
        add("READ_FILE", {"path": "app/tokens.py"}, "list_files")
        add("SEARCH_TEXT", {"query": "expires_at", "paths": ["app", "tests"]}, "read_file")
        patch = _operations(worktree, SOLUTIONS[task_id])
        add("PREPARE_PATCH", {"operations": patch}, "search_text")
        add("ASK_USER", {"question": "Apply the exact two-file expiry-boundary patch?"}, "prepare_patch")
        add(
            "APPLY_PATCH",
            {
                "patch_id": "${last_tool.output.artifact.patch_id}",
                "approval_id": "approval-001",
                "operation_id": "effect-apply-001",
            },
            "prepare_patch",
        )
        add("RUN_CHECK", {"check_id": "unit", "operation_id": "effect-check-001"}, "apply_patch")
    elif task_id == "dry-run-multifile":
        add("READ_FILE", {"path": "app/cli.py"}, "list_files")
        add("READ_FILE", {"path": "app/service.py"}, "read_file")
        # First patch adds the regression test only: the narrow existing test
        # passes, while the broad suite exposes the missing implementation.
        first = _operations(worktree, {"tests/test_cli.py": SOLUTIONS[task_id]["tests/test_cli.py"]})
        add("PREPARE_PATCH", {"operations": first}, "read_file")
        add("ASK_USER", {"question": "Apply the exact regression-test patch?"}, "prepare_patch")
        add(
            "APPLY_PATCH",
            {
                "patch_id": "${last_tool.output.artifact.patch_id}",
                "approval_id": "approval-001",
                "operation_id": "effect-apply-001",
            },
            "prepare_patch",
        )
        add("RUN_CHECK", {"check_id": "narrow", "operation_id": "effect-check-001"}, "apply_patch")
        add("RUN_CHECK", {"check_id": "broad", "operation_id": "effect-check-002"}, "run_check")
        repair_content = {
            key: value for key, value in SOLUTIONS[task_id].items() if key != "tests/test_cli.py"
        }
        repair = _operations(worktree, repair_content)
        add("PREPARE_PATCH", {"operations": repair}, "run_check")
        add("ASK_USER", {"question": "Apply the exact implementation repair?"}, "prepare_patch")
        add(
            "APPLY_PATCH",
            {
                "patch_id": "${last_tool.output.artifact.patch_id}",
                "approval_id": "approval-002",
                "operation_id": "effect-apply-002",
            },
            "prepare_patch",
        )
        add("RUN_CHECK", {"check_id": "broad", "operation_id": "effect-check-003"}, "apply_patch")
    elif task_id == "refresh-token-race":
        add("READ_FILE", {"path": "README.md"}, "list_files")
        add("READ_FILE", {"path": "app/store.py"}, "read_file")
        add(
            "SEARCH_KNOWLEDGE",
            {"query": "refresh token atomic consume", "scopes": ["auth-internal"], "limit": 5},
            "read_file",
        )
        patch = _operations(worktree, SOLUTIONS[task_id])
        add("PREPARE_PATCH", {"operations": patch}, "search_knowledge")
        add("ASK_USER", {"question": "Apply the exact race-condition patch?"}, "prepare_patch")
        add(
            "APPLY_PATCH",
            {
                "patch_id": "${last_tool.output.artifact.patch_id}",
                "approval_id": "approval-001",
                "operation_id": "effect-apply-001",
            },
            "prepare_patch",
        )
        add("RUN_CHECK", {"check_id": "race", "operation_id": "effect-check-001"}, "apply_patch")
    else:
        raise ValueError(f"unknown task fixture: {task_id}")

    add("SHOW_DIFF", {}, "run_check")
    submit_expect = "show_diff"
    artifact_ids = ["${last_tool.receipt_id}"]
    citations = ["fixture task manifest", "tool receipts", "external verifier report"]
    if task_id == "refresh-token-race":
        # Refresh the authorized knowledge evidence after the final diff so the
        # submitted citation and artifact ID come from the actual receipt that
        # the external evaluator will inspect, not from a scripted constant.
        add(
            "SEARCH_KNOWLEDGE",
            {"query": "refresh token atomic consume", "scopes": ["auth-internal"], "limit": 5},
            "show_diff",
        )
        submit_expect = "search_knowledge"
        citations.insert(0, "${last_tool.output.matches.0.citation}")
    add(
        "SUBMIT_RESULT",
        {
            "artifact_ids": artifact_ids,
            "summary": f"completed {task_id} with reviewed changes and checks",
            "risks": ["reference uses an application-level local sandbox"],
            "citations": citations,
        },
        submit_expect,
    )
    return tuple(turns)


def _source_citation(reference: Mapping[str, Any]) -> str:
    identity = {
        field: str(reference[field])
        for field in ("source_id", "origin", "scope", "location", "revision", "digest")
    }
    return "source-ref:" + json.dumps(identity, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _knowledge_provider(directory: Path):
    def search(query: str, scopes: Sequence[str], limit: int) -> Sequence[Mapping[str, Any]]:
        terms = {part.casefold() for part in query.split() if part}
        matches: list[dict[str, Any]] = []
        for path in sorted(directory.glob("*.json")):
            value = json.loads(path.read_text(encoding="utf-8"))
            if value.get("scope") not in scopes:
                continue
            text = f"{value.get('title', '')}\n{value.get('content', '')}"
            if terms and not any(term in text.casefold() for term in terms):
                continue
            reference = {
                "source_id": value["source_id"],
                "origin": "knowledge",
                "location": path.name,
                "revision": str(value["revision"]),
                "digest": value_digest(value),
                "trust": value["trust"],
                "scope": value["scope"],
                "freshness": value["freshness"],
                "retrieved_at": datetime.now(timezone.utc).isoformat(),
            }
            matches.append(
                {
                    "reference": reference,
                    "excerpt": str(value["content"])[:800],
                    "kind": "FACT",
                    "citation": _source_citation(reference),
                }
            )
        return tuple(matches[:limit])

    return search


class FixtureCapstone:
    """Materialize, isolate, run, resume, inspect, and export one task fixture."""

    VERSION = "1.0"

    def __init__(self, guide_root: Path) -> None:
        self.guide_root = guide_root.resolve()
        self.capstone_root = self.guide_root / "exercises" / "10-capstone-local-coding-agent"

    def create(self, task_id: str, session_dir: Path) -> Mapping[str, Any]:
        if session_dir.is_symlink() or os.path.lexists(session_dir):
            raise FileExistsError(f"session destination already exists: {session_dir}")
        task_root = self.capstone_root / "fixtures" / "tasks" / task_id
        if not task_root.is_dir():
            raise ValueError(f"unknown task fixture: {task_id}")
        session_dir.mkdir(parents=True)
        source = session_dir / "source"
        task = materialize_task(task_root, source)
        worktree = session_dir / "agent-worktree"
        isolation = create_agent_worktree(source, worktree)
        manifest = {
            "session_version": self.VERSION,
            "task_id": task_id,
            "task": task,
            "source": str(source),
            "worktree": str(worktree),
            "state_dir": str(session_dir / "state"),
            "isolation": isolation,
            "status": "CREATED",
        }
        atomic_write_json(session_dir / "session.json", manifest)
        return manifest

    def _components(self, manifest: Mapping[str, Any], *, crash_after: str | None = None):
        worktree = Path(str(manifest["worktree"]))
        state_dir = Path(str(manifest["state_dir"]))
        task = dict(manifest["task"])
        approval_store = ApprovalStore(state_dir / "approvals.json")
        expiry = (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat()
        grant = Grant(
            grant_id="grant-fixture",
            principal=PRINCIPAL,
            purpose=PURPOSE,
            read_paths=(".",),
            write_paths=tuple(task["allowed_changes"]),
            command_ids=tuple(task["commands"]),
            knowledge_scopes=tuple(task.get("knowledge_scopes", ())),
            network="deny",
            expires_at=expiry,
        )
        policy = PolicyEngine(worktree, grants=(grant,), approval_store=approval_store)
        catalog = CommandCatalog(
            CommandSpec(command_id=key, argv=tuple(value), cwd=".", network_profiles=("deny",))
            for key, value in task["commands"].items()
        )
        patch_engine = PatchEngine(worktree, journal_dir=state_dir / "patch-journal")
        tools = ToolGateway(
            worktree,
            policy=policy,
            patch_engine=patch_engine,
            process_runner=ProcessRunner(worktree, catalog=catalog),
            git_adapter=GitAdapter(worktree),
            knowledge_search=_knowledge_provider(self.capstone_root / "fixtures" / "knowledge"),
            state_dir=state_dir,
        )
        model = ScriptedModelAdapter(fixture_script(str(manifest["task_id"]), worktree))
        evaluator = ExternalEvaluator(task, worktree)

        def verify(_artifacts, events):
            return asdict(evaluator.evaluate(events))

        budget_values = dict(task.get("budget", {}))
        budget = RunBudget(**budget_values)
        return approval_store, patch_engine, tools, model, verify, budget

    @staticmethod
    def _approve_waiting(
        runtime: AgentRuntime,
        approval_store: ApprovalStore,
        patch_engine: PatchEngine,
        ordinal: int,
    ) -> None:
        prepared = [
            item["output"]["artifact"]
            for item in runtime.state["observations"]
            if item.get("kind") == "TOOL_RECEIPT" and item.get("tool") == "prepare_patch"
        ]
        if not prepared:
            raise RuntimeError("agent requested approval without a prepared patch")
        artifact = prepared[-1]
        patch = patch_engine.get(str(artifact["patch_id"]))
        operation_id = f"effect-apply-{ordinal:03d}"
        approval_store.add(
            Approval(
                approval_id=f"approval-{ordinal:03d}",
                principal=PRINCIPAL,
                patch_id=patch.patch_id,
                patch_digest=patch.digest,
                operation_id=operation_id,
                expires_at=(datetime.now(timezone.utc) + timedelta(minutes=30)).isoformat(),
            )
        )
        runtime.provide_user_input(f"approved exact patch {patch.patch_id}")

    def run(
        self,
        session_dir: Path,
        *,
        task_id: str | None = None,
        crash_after_effect: str | None = None,
        resume: bool = False,
    ) -> RunResult:
        manifest_path = session_dir / "session.json"
        if not manifest_path.exists():
            if resume or task_id is None:
                raise FileNotFoundError(f"session manifest is missing: {manifest_path}")
            manifest = self.create(task_id, session_dir)
        else:
            manifest = read_json(manifest_path)
            if task_id is not None and task_id != manifest.get("task_id"):
                raise ValueError("task ID differs from the existing session")
        approval_store, patch_engine, tools, model, verify, budget = self._components(
            manifest, crash_after=crash_after_effect
        )
        state_dir = Path(str(manifest["state_dir"]))
        if resume:
            runtime = AgentRuntime.resume(
                model=model,
                tools=tools,
                state_dir=state_dir,
                principal=PRINCIPAL,
                verifier=verify,
            )
        else:
            runtime = AgentRuntime(
                model=model,
                tools=tools,
                state_dir=state_dir,
                principal=PRINCIPAL,
                task=str(manifest["task"]["task"]),
                budget=budget,
                verifier=verify,
                crash_after=(f"AFTER_EFFECT:{crash_after_effect}" if crash_after_effect else None),
            )
        approvals = sum(
            1 for event in runtime.event_log.events if event.get("type") == "USER_INPUT_RECEIVED"
        )
        try:
            while True:
                result = runtime.run()
                if result.state != "WAITING_USER":
                    break
                approvals += 1
                self._approve_waiting(runtime, approval_store, patch_engine, approvals)
        except InjectedCrash:
            manifest = dict(manifest, status="CRASHED")
            atomic_write_json(manifest_path, manifest)
            raise
        manifest = dict(manifest, status=result.state, session_id=result.session_id)
        atomic_write_json(manifest_path, manifest)
        atomic_write_json(session_dir / "evaluation-report.json", dict(result.verification or {}))
        return result

    @staticmethod
    def status(session_dir: Path) -> Mapping[str, Any]:
        manifest = read_json(session_dir / "session.json")
        checkpoint = read_json(Path(str(manifest["state_dir"])) / "checkpoint.json")
        return {
            "task_id": manifest["task_id"],
            "session_id": checkpoint["body"]["state"]["session_id"],
            "status": checkpoint["body"]["state"]["status"],
            "step": checkpoint["body"]["state"]["step"],
            "worktree": manifest["worktree"],
        }

    @staticmethod
    def diff(session_dir: Path) -> str:
        manifest = read_json(session_dir / "session.json")
        return _git(Path(str(manifest["worktree"])), "diff", "--binary", "--").decode(
            "utf-8", "replace"
        )

    @staticmethod
    def cancel(session_dir: Path) -> Mapping[str, Any]:
        manifest_path = session_dir / "session.json"
        manifest = read_json(manifest_path)
        marker = Path(str(manifest["state_dir"])) / "cancel.requested"
        marker.parent.mkdir(parents=True, exist_ok=True)
        marker.write_text("cancel requested\n", encoding="utf-8")
        manifest = dict(manifest, status="CANCEL_REQUESTED")
        atomic_write_json(manifest_path, manifest)
        return {"status": "CANCEL_REQUESTED", "marker": str(marker)}

    @staticmethod
    def export(session_dir: Path, destination: Path) -> Path:
        if destination.is_symlink() or os.path.lexists(destination):
            raise FileExistsError(f"refusing to overwrite export: {destination}")
        destination.mkdir(parents=True)
        (destination / "agent.patch").write_text(FixtureCapstone.diff(session_dir), encoding="utf-8")
        for name in ("session.json", "evaluation-report.json"):
            shutil.copy2(session_dir / name, destination / name)
        manifest = read_json(session_dir / "session.json")
        state_dir = Path(str(manifest["state_dir"]))
        shutil.copy2(state_dir / "events.jsonl", destination / "events.jsonl")
        return destination
