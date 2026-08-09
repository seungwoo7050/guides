"""Stage 07 starter: task-scoped grants, exact approvals, and revocation."""

from __future__ import annotations

import datetime as dt
from pathlib import Path
from typing import Iterable, Sequence

from .types import Approval, Grant, PatchArtifact


class ApprovalStore:
    def __init__(self, path: Path) -> None:
        raise NotImplementedError("create an atomic durable approval/revocation store")

    def add(self, approval: Approval) -> None:
        raise NotImplementedError

    put = add

    def get(self, approval_id: str) -> Approval:
        raise NotImplementedError

    def consume(
        self,
        approval_id: str | None,
        *,
        principal: str,
        patch_id: str,
        patch_digest: str,
        operation_id: str | None,
        now: dt.datetime | None = None,
    ) -> Approval:
        raise NotImplementedError("require exact principal/patch/digest/operation and expiry")

    def revoke_approval(self, approval_id: str) -> None:
        raise NotImplementedError

    def revoke_grant(self, grant_id: str) -> None:
        raise NotImplementedError

    def grant_is_revoked(self, grant_id: str) -> bool:
        raise NotImplementedError


class PolicyEngine:
    def __init__(
        self,
        workspace: Path,
        *,
        grants: Iterable[Grant] = (),
        approval_store: ApprovalStore | None = None,
        protected_paths: Iterable[str] = (".git", ".env", ".agent-state", ".verifier"),
    ) -> None:
        raise NotImplementedError("compile grants and deny rules outside the model")

    def add_grant(self, grant: Grant) -> None:
        raise NotImplementedError

    def revoke(self, grant_id: str) -> None:
        raise NotImplementedError

    revoke_grant = revoke

    def authorize_read(self, principal: str, path: str, *, purpose: str | None = None) -> str:
        raise NotImplementedError

    def authorize_write(self, principal: str, path: str, *, purpose: str | None = None) -> str:
        raise NotImplementedError

    def authorize_patch(
        self,
        principal: str,
        artifact: PatchArtifact,
        *,
        approval_id: str | None,
        operation_id: str | None,
        purpose: str | None = None,
    ) -> Approval:
        raise NotImplementedError

    def authorize_command(
        self,
        principal: str,
        command_id: str,
        *,
        network: str = "deny",
        purpose: str | None = None,
        argv: Sequence[str] = (),
    ) -> str:
        raise NotImplementedError

    def authorize_knowledge(
        self,
        principal: str,
        scopes: Sequence[str],
        *,
        purpose: str | None = None,
    ) -> tuple[str, ...]:
        raise NotImplementedError("authorize scopes before retrieval")
