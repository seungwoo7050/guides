"""Stable public data shapes shared by starter and reference."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping


@dataclass(frozen=True)
class UsageReceipt:
    input_tokens: int = 0
    output_tokens: int = 0
    cost_microunits: int = 0


@dataclass(frozen=True)
class ModelRequest:
    request_id: str
    session_id: str
    task: str
    instruction_blocks: tuple[Mapping[str, Any], ...]
    context_items: tuple[Mapping[str, Any], ...]
    tool_definitions: tuple[Mapping[str, Any], ...]
    deadline_epoch_ms: int | None = None


@dataclass(frozen=True)
class ModelEvent:
    kind: str
    sequence: int
    payload: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Action:
    contract_version: str
    action_id: str
    kind: str
    arguments: Mapping[str, Any]
    purpose: str


@dataclass(frozen=True)
class RepositorySnapshot:
    snapshot_id: str
    root: str
    head: str | None
    branch: str | None
    index_tree: str | None
    staged: tuple[str, ...]
    unstaged: tuple[str, ...]
    untracked: tuple[str, ...]
    files: Mapping[str, str]


@dataclass(frozen=True)
class SourceRef:
    source_id: str
    origin: str
    location: str
    revision: str
    digest: str
    trust: str
    scope: str
    freshness: str
    retrieved_at: str


@dataclass(frozen=True)
class ContextItem:
    reference: SourceRef
    excerpt: str
    kind: str = "FACT"


@dataclass(frozen=True)
class PatchOperation:
    kind: str
    path: str
    before_digest: str | None = None
    content: str | None = None
    new_path: str | None = None


@dataclass(frozen=True)
class PatchArtifact:
    patch_id: str
    snapshot_id: str
    operations: tuple[PatchOperation, ...]
    digest: str


@dataclass(frozen=True)
class ToolRequest:
    request_id: str
    principal: str
    tool: str
    arguments: Mapping[str, Any]
    operation_id: str | None = None
    approval_id: str | None = None


@dataclass(frozen=True)
class ToolReceipt:
    receipt_id: str
    tool: str
    status: str
    effect: str
    resource: str | None
    output: Mapping[str, Any]
    duplicate: bool = False


@dataclass(frozen=True)
class CommandRequest:
    command_id: str
    argv: tuple[str, ...]
    cwd: str
    environment: Mapping[str, str]
    timeout_seconds: float
    max_output_bytes: int
    network: str = "deny"


@dataclass(frozen=True)
class CommandResult:
    command_id: str
    exit_kind: str
    exit_code: int | None
    signal: int | None
    stdout: str
    stderr: str
    truncated: bool
    duration_ms: int
    cleanup_status: str
    workspace_before: str
    workspace_after: str


@dataclass(frozen=True)
class Grant:
    grant_id: str
    principal: str
    purpose: str
    read_paths: tuple[str, ...]
    write_paths: tuple[str, ...]
    command_ids: tuple[str, ...]
    knowledge_scopes: tuple[str, ...]
    network: str
    expires_at: str
    revoked: bool = False


@dataclass(frozen=True)
class Approval:
    approval_id: str
    principal: str
    patch_id: str
    patch_digest: str
    expires_at: str
    operation_id: str | None = None
    used: bool = False


@dataclass
class RunBudget:
    max_steps: int = 40
    max_model_calls: int = 20
    max_tool_calls: int = 80
    max_read_bytes: int = 2_000_000
    max_writes: int = 10
    max_command_seconds: float = 120.0
    max_tokens: int = 100_000
    max_cost_microunits: int = 1_000_000
    max_wall_seconds: float = 600.0
    steps: int = 0
    model_calls: int = 0
    tool_calls: int = 0
    read_bytes: int = 0
    writes: int = 0
    command_seconds: float = 0.0
    tokens: int = 0
    cost_microunits: int = 0


@dataclass(frozen=True)
class RunResult:
    session_id: str
    state: str
    events: tuple[Mapping[str, Any], ...]
    artifacts: tuple[str, ...]
    verification: Mapping[str, Any] | None = None
