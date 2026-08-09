from __future__ import annotations

import datetime as dt
import fcntl
import os
import threading
from contextlib import contextmanager
from dataclasses import asdict, replace
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from .errors import ApprovalRequired, ContractError, PolicyDenied
from .patching import canonical_path
from .types import Approval, Grant, PatchArtifact
from .util import atomic_write_json, read_json, value_digest


def _utc_now() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


def _parse_time(value: str) -> dt.datetime:
    if not isinstance(value, str) or not value:
        raise ContractError("expiry must be a non-empty RFC 3339 timestamp")
    normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        parsed = dt.datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise ContractError(f"invalid expiry timestamp: {value!r}") from exc
    if parsed.tzinfo is None:
        raise ContractError("expiry timestamp must include a timezone")
    return parsed.astimezone(dt.timezone.utc)


class ApprovalStore:
    """Durable, one-shot exact approvals plus durable revocation records."""

    VERSION = "1"

    def __init__(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        candidate = path.parent.resolve(strict=True) / path.name
        if candidate.is_symlink():
            raise ContractError("approval store may not be a symlink")
        self.path = candidate
        self._lock = threading.RLock()
        self._lock_path = candidate.with_name(candidate.name + ".lock")
        with self._locked():
            if not candidate.exists():
                self._save(
                    {"approval_store_version": self.VERSION, "approvals": {}, "revoked_grants": []}
                )

    @contextmanager
    def _locked(self):
        with self._lock:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            descriptor = os.open(self._lock_path, os.O_CREAT | os.O_RDWR, 0o600)
            try:
                fcntl.flock(descriptor, fcntl.LOCK_EX)
                yield
            finally:
                fcntl.flock(descriptor, fcntl.LOCK_UN)
                os.close(descriptor)

    def _save(self, body: Mapping[str, Any]) -> None:
        atomic_write_json(self.path, {"body": dict(body), "digest": value_digest(body)})

    def _load(self) -> dict[str, Any]:
        envelope = read_json(self.path)
        value = envelope.get("body") if isinstance(envelope, dict) else None
        if (
            not isinstance(value, dict)
            or envelope.get("digest") != value_digest(value)
            or value.get("approval_store_version") != self.VERSION
            or not isinstance(value.get("approvals"), dict)
            or not isinstance(value.get("revoked_grants"), list)
        ):
            raise ContractError("invalid approval store")
        return value

    def add(self, approval: Approval) -> None:
        _parse_time(approval.expires_at)
        with self._locked():
            value = self._load()
            encoded = asdict(approval)
            existing = value["approvals"].get(approval.approval_id)
            if existing is not None and existing != encoded:
                raise ContractError("approval ID reused with different authority")
            value["approvals"][approval.approval_id] = encoded
            self._save(value)

    put = add

    def get(self, approval_id: str) -> Approval:
        with self._locked():
            encoded = self._load()["approvals"].get(approval_id)
        if encoded is None:
            raise ApprovalRequired(f"unknown approval: {approval_id}")
        try:
            return Approval(**encoded)
        except TypeError as exc:
            raise ContractError("invalid approval record") from exc

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
        if not approval_id:
            raise ApprovalRequired("an exact patch approval is required")
        with self._locked():
            value = self._load()
            encoded = value["approvals"].get(approval_id)
            if encoded is None:
                raise ApprovalRequired(f"unknown approval: {approval_id}")
            approval = Approval(**encoded)
            current = (now or _utc_now()).astimezone(dt.timezone.utc)
            if approval.used:
                raise ApprovalRequired("approval was already consumed")
            if _parse_time(approval.expires_at) <= current:
                raise ApprovalRequired("approval expired")
            if approval.principal != principal:
                raise ApprovalRequired("approval principal mismatch")
            if approval.patch_id != patch_id or approval.patch_digest != patch_digest:
                raise ApprovalRequired("approval is not for this exact patch")
            if approval.operation_id is not None and approval.operation_id != operation_id:
                raise ApprovalRequired("approval operation mismatch")
            used = replace(approval, used=True)
            value["approvals"][approval_id] = asdict(used)
            self._save(value)
            return used

    def revoke_approval(self, approval_id: str) -> None:
        with self._locked():
            value = self._load()
            encoded = value["approvals"].get(approval_id)
            if encoded is None:
                return
            encoded["used"] = True
            value["approvals"][approval_id] = encoded
            self._save(value)

    def revoke_grant(self, grant_id: str) -> None:
        with self._locked():
            value = self._load()
            if grant_id not in value["revoked_grants"]:
                value["revoked_grants"].append(grant_id)
                value["revoked_grants"].sort()
                self._save(value)

    def grant_is_revoked(self, grant_id: str) -> bool:
        with self._locked():
            return grant_id in self._load()["revoked_grants"]


class PolicyEngine:
    """Task-scoped grants enforced outside the model prompt.

    Path permissions are checked against canonical workspace-relative resources.
    A write grant never implies command, Git, knowledge, or network authority.
    """

    _NETWORK_ORDER = {"deny": 0, "loopback": 1, "allow": 2}
    _NETWORK_CLIENTS = {
        "curl",
        "wget",
        "nc",
        "netcat",
        "ncat",
        "ssh",
        "scp",
        "sftp",
        "ftp",
        "telnet",
    }

    def __init__(
        self,
        workspace: Path,
        *,
        grants: Iterable[Grant] = (),
        approval_store: ApprovalStore | None = None,
        protected_paths: Iterable[str] = (".git", ".env", ".agent-state", ".verifier"),
    ) -> None:
        self.workspace = workspace.resolve(strict=True)
        if not self.workspace.is_dir():
            raise ContractError("policy workspace must be a directory")
        self.approval_store = approval_store
        self._grants: dict[str, Grant] = {}
        self.protected_paths = tuple(protected_paths)
        for grant in grants:
            self.add_grant(grant)

    def add_grant(self, grant: Grant) -> None:
        _parse_time(grant.expires_at)
        if grant.network not in self._NETWORK_ORDER:
            raise ContractError("grant network must be deny, loopback, or allow")
        if not grant.grant_id or not grant.principal or not grant.purpose:
            raise ContractError("grant identity, principal, and purpose are required")
        for value in (*grant.read_paths, *grant.write_paths):
            self._normalize_scope(value)
        existing = self._grants.get(grant.grant_id)
        if existing is not None and existing != grant:
            raise ContractError("grant ID reused with different authority")
        self._grants[grant.grant_id] = grant

    def revoke(self, grant_id: str) -> None:
        if self.approval_store is not None:
            self.approval_store.revoke_grant(grant_id)
        elif grant_id in self._grants:
            self._grants[grant_id] = replace(self._grants[grant_id], revoked=True)

    revoke_grant = revoke

    def _active_grants(self, principal: str, *, purpose: str | None = None) -> list[Grant]:
        current = _utc_now()
        result: list[Grant] = []
        for grant in self._grants.values():
            durable_revoked = self.approval_store is not None and self.approval_store.grant_is_revoked(grant.grant_id)
            if (
                grant.principal == principal
                and not grant.revoked
                and not durable_revoked
                and _parse_time(grant.expires_at) > current
                and (purpose is None or grant.purpose == purpose)
            ):
                result.append(grant)
        return result

    @staticmethod
    def _normalize_scope(value: str) -> str:
        if not isinstance(value, str) or not value or "\x00" in value:
            raise ContractError("path scope must be a non-empty string")
        stripped = value.rstrip("/")
        if stripped in {"", "."}:
            return "."
        candidate = Path(stripped)
        if candidate.is_absolute() or ".." in candidate.parts:
            raise ContractError("path scopes must be canonical workspace-relative paths")
        return candidate.as_posix()

    def _resource(self, path: str) -> str:
        target = canonical_path(self.workspace, path)
        relative = target.relative_to(self.workspace).as_posix()
        self._deny_protected(relative)
        return relative

    def _deny_protected(self, relative: str) -> None:
        parts = Path(relative).parts
        for protected in self.protected_paths:
            protected_parts = Path(protected).parts
            if parts[: len(protected_parts)] == protected_parts:
                raise PolicyDenied(f"protected path denied: {relative}")
        # All dotenv variants are credentials, but .env.example remains a safe
        # documentation fixture.
        name = Path(relative).name
        if name.startswith(".env") and name != ".env.example":
            raise PolicyDenied(f"credential path denied: {relative}")

    @classmethod
    def _scope_contains(cls, scope: str, resource: str) -> bool:
        normalized = cls._normalize_scope(scope)
        return normalized == "." or resource == normalized or resource.startswith(normalized + "/")

    def _authorize_path(self, principal: str, path: str, *, write: bool, purpose: str | None) -> str:
        resource = self._resource(path)
        for grant in self._active_grants(principal, purpose=purpose):
            scopes = grant.write_paths if write else grant.read_paths
            if any(self._scope_contains(scope, resource) for scope in scopes):
                return resource
        effect = "write" if write else "read"
        raise PolicyDenied(f"{effect} not granted for {resource}")

    def authorize_read(self, principal: str, path: str, *, purpose: str | None = None) -> str:
        return self._authorize_path(principal, path, write=False, purpose=purpose)

    def authorize_write(self, principal: str, path: str, *, purpose: str | None = None) -> str:
        return self._authorize_path(principal, path, write=True, purpose=purpose)

    def authorize_patch(
        self,
        principal: str,
        artifact: PatchArtifact,
        *,
        approval_id: str | None,
        operation_id: str | None,
        purpose: str | None = None,
    ) -> Approval:
        for operation in artifact.operations:
            self.authorize_write(principal, operation.path, purpose=purpose)
            if operation.new_path:
                self.authorize_write(principal, operation.new_path, purpose=purpose)
        if self.approval_store is None:
            raise ApprovalRequired("no durable approval store is configured")
        return self.approval_store.consume(
            approval_id,
            principal=principal,
            patch_id=artifact.patch_id,
            patch_digest=artifact.digest,
            operation_id=operation_id,
        )

    def authorize_command(
        self,
        principal: str,
        command_id: str,
        *,
        network: str = "deny",
        purpose: str | None = None,
        argv: Sequence[str] = (),
    ) -> str:
        if network not in self._NETWORK_ORDER:
            raise PolicyDenied("unknown network profile")
        basename = os.path.basename(argv[0]) if argv else ""
        if network != "allow" and basename in self._NETWORK_CLIENTS:
            raise PolicyDenied("general network client requires the allow profile")
        for grant in self._active_grants(principal, purpose=purpose):
            if command_id in grant.command_ids and self._NETWORK_ORDER[network] <= self._NETWORK_ORDER[grant.network]:
                return command_id
        raise PolicyDenied(f"command or network profile not granted: {command_id}")

    def authorize_knowledge(
        self,
        principal: str,
        scopes: Sequence[str],
        *,
        purpose: str | None = None,
    ) -> tuple[str, ...]:
        requested = tuple(scopes)
        if not requested:
            raise PolicyDenied("knowledge search requires an explicit scope")
        allowed: set[str] = set()
        for grant in self._active_grants(principal, purpose=purpose):
            allowed.update(grant.knowledge_scopes)
        if any(scope not in allowed for scope in requested):
            raise PolicyDenied("knowledge scope not granted")
        return requested
