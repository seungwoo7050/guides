from __future__ import annotations

import base64
import fcntl
import os
import stat
import threading
from contextlib import contextmanager
from dataclasses import asdict
from pathlib import Path
from typing import Any, Iterable, Mapping

from .errors import ContractError, OperationConflict, PolicyDenied
from .types import PatchArtifact, PatchOperation
from .util import atomic_write_bytes, atomic_write_json, read_json, sha256_bytes, value_digest


_MISSING = "MISSING"


def canonical_path(root: Path, value: str, *, must_exist: bool = False) -> Path:
    """Resolve a workspace-relative path without following a symlink boundary.

    The function deliberately rejects every symlink in the existing prefix.  That
    policy is stricter than merely checking where the link currently resolves and
    avoids a check/use race in this small, portable reference implementation.
    """

    if not isinstance(value, str) or not value or "\x00" in value:
        raise ContractError("path must be a non-empty string without NUL")
    candidate = Path(value)
    if candidate.is_absolute() or any(part in {"", ".", ".."} for part in candidate.parts):
        raise PolicyDenied(f"path is not canonical workspace-relative: {value!r}")
    root = root.resolve(strict=True)
    current = root
    for part in candidate.parts:
        current = current / part
        if current.is_symlink():
            raise PolicyDenied(f"symlink paths are outside the portable workspace policy: {value!r}")
    try:
        current.relative_to(root)
    except ValueError as exc:  # Defensive; absolute and '..' were already rejected.
        raise PolicyDenied(f"path escapes workspace: {value!r}") from exc
    if must_exist and not current.exists():
        raise OperationConflict(f"path does not exist: {value}")
    return current


def _regular_file(path: Path) -> os.stat_result:
    try:
        metadata = path.lstat()
    except FileNotFoundError as exc:
        raise OperationConflict(f"path does not exist: {path}") from exc
    if not stat.S_ISREG(metadata.st_mode):
        raise PolicyDenied(f"only regular files are supported: {path}")
    return metadata


def read_text_file(root: Path, path: str, *, max_bytes: int = 1_000_000) -> Mapping[str, Any]:
    if isinstance(max_bytes, bool) or not isinstance(max_bytes, int) or max_bytes < 0:
        raise ContractError("max_bytes must be a non-negative integer")
    target = canonical_path(root, path, must_exist=True)
    metadata = _regular_file(target)
    if metadata.st_size > max_bytes:
        raise PolicyDenied(f"file exceeds read limit ({metadata.st_size} > {max_bytes})")
    data = target.read_bytes()
    if b"\x00" in data:
        raise PolicyDenied("binary file rejected")
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise PolicyDenied("non-UTF-8 file rejected") from exc
    return {
        "path": path,
        "content": text,
        "digest": sha256_bytes(data),
        "size": len(data),
        "mode": stat.S_IMODE(metadata.st_mode),
    }


def _artifact_body(snapshot_id: str, operations: Iterable[PatchOperation]) -> dict[str, Any]:
    return {"snapshot_id": snapshot_id, "operations": [asdict(item) for item in operations]}


def make_patch(snapshot_id: str, operations: Iterable[PatchOperation], *, patch_id: str | None = None) -> PatchArtifact:
    operation_tuple = tuple(operations)
    body = _artifact_body(snapshot_id, operation_tuple)
    digest = value_digest(body)
    return PatchArtifact(
        patch_id=patch_id or "patch-" + digest.removeprefix("sha256:")[:20],
        snapshot_id=snapshot_id,
        operations=operation_tuple,
        digest=digest,
    )


class PatchEngine:
    """A bounded multi-file patch engine with preconditions and recovery journals."""

    VERSION = "1"

    def __init__(
        self,
        workspace: Path,
        *,
        journal_dir: Path | None = None,
        max_file_bytes: int = 1_000_000,
    ) -> None:
        if isinstance(max_file_bytes, bool) or not isinstance(max_file_bytes, int) or max_file_bytes <= 0:
            raise ContractError("max_file_bytes must be a positive integer")
        self.workspace = workspace.resolve(strict=True)
        if not self.workspace.is_dir():
            raise ContractError("workspace must be a directory")
        self.journal_dir = (journal_dir or self.workspace / ".agent-state" / "patches").resolve()
        self.max_file_bytes = max_file_bytes
        self._artifacts: dict[str, PatchArtifact] = {}
        self._lock = threading.RLock()

    @contextmanager
    def _effect_lock(self):
        with self._lock:
            self.journal_dir.mkdir(parents=True, exist_ok=True)
            descriptor = os.open(self.journal_dir / ".lock", os.O_CREAT | os.O_RDWR, 0o600)
            try:
                fcntl.flock(descriptor, fcntl.LOCK_EX)
                yield
            finally:
                fcntl.flock(descriptor, fcntl.LOCK_UN)
                os.close(descriptor)

    def read(self, path: str, *, max_bytes: int | None = None) -> Mapping[str, Any]:
        return read_text_file(
            self.workspace,
            path,
            max_bytes=self.max_file_bytes if max_bytes is None else max_bytes,
        )

    def prepare(
        self,
        snapshot_id: str,
        operations: Iterable[PatchOperation | Mapping[str, Any]],
        *,
        patch_id: str | None = None,
    ) -> PatchArtifact:
        parsed: list[PatchOperation] = []
        for raw in operations:
            if isinstance(raw, PatchOperation):
                parsed.append(raw)
            elif isinstance(raw, Mapping):
                try:
                    parsed.append(PatchOperation(**dict(raw)))
                except (TypeError, ValueError) as exc:
                    raise ContractError(f"invalid patch operation: {raw!r}") from exc
            else:
                raise ContractError("operations must contain PatchOperation values or mappings")
        if not parsed:
            raise ContractError("patch must contain at least one operation")
        artifact = make_patch(snapshot_id, parsed, patch_id=patch_id)
        self._validate_plan(artifact)
        self._journal_path(artifact.patch_id)
        existing = self._artifacts.get(artifact.patch_id)
        if existing is not None and existing.digest != artifact.digest:
            raise OperationConflict("patch ID reused with different content")
        self._artifacts[artifact.patch_id] = artifact
        return artifact

    def register(self, artifact: PatchArtifact) -> None:
        expected = value_digest(_artifact_body(artifact.snapshot_id, artifact.operations))
        if artifact.digest != expected:
            raise ContractError("patch artifact digest mismatch")
        self._validate_plan(artifact)
        self._journal_path(artifact.patch_id)
        existing = self._artifacts.get(artifact.patch_id)
        if existing is not None and existing.digest != artifact.digest:
            raise OperationConflict("patch ID reused with different content")
        self._artifacts[artifact.patch_id] = artifact

    def get(self, patch_id: str) -> PatchArtifact:
        try:
            return self._artifacts[patch_id]
        except KeyError:
            journal_path = self._journal_path(patch_id)
            if not journal_path.exists():
                raise ContractError(f"unknown patch: {patch_id}") from None
            journal = self._read_journal(journal_path)
            try:
                artifact = make_patch(
                    str(journal["snapshot_id"]),
                    (PatchOperation(**item) for item in journal["operations"]),
                    patch_id=patch_id,
                )
            except (KeyError, TypeError, ValueError) as exc:
                raise ContractError("invalid patch journal artifact") from exc
            if artifact.digest != journal.get("patch_digest"):
                raise ContractError("patch journal artifact digest mismatch")
            self._artifacts[patch_id] = artifact
            return artifact

    def _validate_plan(self, artifact: PatchArtifact) -> None:
        expected = value_digest(_artifact_body(artifact.snapshot_id, artifact.operations))
        if artifact.digest != expected:
            raise ContractError("patch artifact digest mismatch")
        touched: set[str] = set()
        portable_names: set[str] = set()
        for operation in artifact.operations:
            kind = operation.kind.upper()
            if kind not in {"CREATE", "MODIFY", "DELETE", "RENAME"}:
                raise ContractError(f"unsupported patch operation: {operation.kind}")
            canonical_path(self.workspace, operation.path)
            names = [operation.path]
            if kind == "RENAME":
                if not operation.new_path:
                    raise ContractError("RENAME requires new_path")
                canonical_path(self.workspace, operation.new_path)
                names.append(operation.new_path)
            elif operation.new_path is not None:
                raise ContractError(f"{kind} must not set new_path")
            if kind in {"CREATE", "MODIFY"}:
                if not isinstance(operation.content, str):
                    raise ContractError(f"{kind} requires UTF-8 text content")
                encoded = operation.content.encode("utf-8")
                if b"\x00" in encoded:
                    raise PolicyDenied("binary patch content rejected")
                if len(encoded) > self.max_file_bytes:
                    raise PolicyDenied("patch content exceeds file-size limit")
            elif operation.content is not None:
                raise ContractError(f"{kind} must not set content")
            if kind == "CREATE" and operation.before_digest is not None:
                raise ContractError("CREATE before_digest must be null")
            if kind != "CREATE" and not operation.before_digest:
                raise ContractError(f"{kind} requires before_digest")
            for name in names:
                if name in touched:
                    raise ContractError(f"path appears more than once in a change set: {name}")
                portable = name.casefold()
                if portable in portable_names:
                    raise ContractError(
                        f"case-colliding paths are not portable across supported workspaces: {name}"
                    )
                touched.add(name)
                portable_names.add(portable)

    def _capture(self, names: Iterable[str]) -> dict[str, dict[str, Any]]:
        result: dict[str, dict[str, Any]] = {}
        for name in sorted(set(names)):
            target = canonical_path(self.workspace, name)
            if not target.exists():
                result[name] = {"state": _MISSING}
                continue
            metadata = _regular_file(target)
            if metadata.st_size > self.max_file_bytes:
                raise PolicyDenied(f"file exceeds patch journal limit ({metadata.st_size} > {self.max_file_bytes})")
            data = target.read_bytes()
            result[name] = {
                "state": "FILE",
                "digest": sha256_bytes(data),
                "mode": stat.S_IMODE(metadata.st_mode),
                "data": base64.b64encode(data).decode("ascii"),
            }
        return result

    @staticmethod
    def _state_digest(state: Mapping[str, Any]) -> str:
        return _MISSING if state.get("state") == _MISSING else str(state["digest"])

    def _preflight(self, artifact: PatchArtifact) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
        names: list[str] = []
        for item in artifact.operations:
            names.append(item.path)
            if item.new_path:
                names.append(item.new_path)
        before = self._capture(names)
        after = {name: dict(value) for name, value in before.items()}
        for operation in artifact.operations:
            kind = operation.kind.upper()
            source = before[operation.path]
            if kind == "CREATE":
                if source["state"] != _MISSING:
                    raise OperationConflict(f"CREATE target already exists: {operation.path}")
                data = operation.content.encode("utf-8")  # validated by _validate_plan
                after[operation.path] = self._encoded_state(data, 0o644)
                continue
            if source["state"] == _MISSING or source["digest"] != operation.before_digest:
                raise OperationConflict(f"stale precondition: {operation.path}")
            if kind == "MODIFY":
                source_data = base64.b64decode(str(source["data"]), validate=True)
                if b"\x00" in source_data:
                    raise PolicyDenied(f"binary file modification rejected: {operation.path}")
                try:
                    source_data.decode("utf-8")
                except UnicodeDecodeError as exc:
                    raise PolicyDenied(f"non-UTF-8 file modification rejected: {operation.path}") from exc
                data = operation.content.encode("utf-8")
                after[operation.path] = self._encoded_state(data, int(source["mode"]))
            elif kind == "DELETE":
                after[operation.path] = {"state": _MISSING}
            else:
                destination = before[operation.new_path]
                if destination["state"] != _MISSING:
                    raise OperationConflict(f"RENAME destination exists: {operation.new_path}")
                after[operation.path] = {"state": _MISSING}
                after[operation.new_path] = dict(source)
        return before, after

    @staticmethod
    def _encoded_state(data: bytes, mode: int) -> dict[str, Any]:
        return {
            "state": "FILE",
            "digest": sha256_bytes(data),
            "mode": mode,
            "data": base64.b64encode(data).decode("ascii"),
        }

    def _journal_path(self, patch_id: str) -> Path:
        safe = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_."
        if not patch_id or any(char not in safe for char in patch_id):
            raise ContractError("patch_id contains unsafe characters")
        return self.journal_dir / f"{patch_id}.json"

    def _write_journal(self, journal: Mapping[str, Any]) -> None:
        body = dict(journal)
        body.pop("journal_digest", None)
        atomic_write_json(
            self._journal_path(str(journal["patch_id"])),
            {**body, "journal_digest": value_digest(body)},
        )

    @staticmethod
    def _read_journal(path: Path) -> dict[str, Any]:
        if path.is_symlink():
            raise PolicyDenied("patch journal may not be a symlink")
        value = read_json(path)
        if not isinstance(value, dict):
            raise ContractError("invalid patch journal")
        digest = value.pop("journal_digest", None)
        if digest != value_digest(value):
            raise ContractError("patch journal integrity failure")
        return value

    def apply(self, artifact: PatchArtifact | str) -> Mapping[str, Any]:
        with self._effect_lock():
            return self._apply_locked(artifact)

    def _apply_locked(self, artifact: PatchArtifact | str) -> Mapping[str, Any]:
        if isinstance(artifact, str):
            artifact = self.get(artifact)
        else:
            self.register(artifact)
        journal_path = self._journal_path(artifact.patch_id)
        if journal_path.exists():
            previous = self._read_journal(journal_path)
            if previous.get("patch_digest") != artifact.digest:
                raise OperationConflict("patch journal has a different digest")
            if previous.get("status") == "APPLIED":
                self._assert_matches(previous["after"], allow_before=False)
                return dict(previous["receipt"], duplicate=True)
            if previous.get("status") in {"PREPARED", "APPLYING", "ROLLBACK_REQUIRED"}:
                raise OperationConflict("incomplete patch journal requires recover()")
            if previous.get("status") == "ROLLED_BACK":
                raise OperationConflict("rolled-back patch IDs cannot be reused")
        before, after = self._preflight(artifact)
        journal: dict[str, Any] = {
            "journal_version": self.VERSION,
            "patch_id": artifact.patch_id,
            "patch_digest": artifact.digest,
            "snapshot_id": artifact.snapshot_id,
            "status": "PREPARED",
            "before": before,
            "after": after,
            "operations": [asdict(item) for item in artifact.operations],
        }
        self._write_journal(journal)
        journal["status"] = "APPLYING"
        self._write_journal(journal)
        try:
            # Write final states directly.  The complete before image in the
            # journal makes an interrupted sequence detectable and recoverable.
            self._materialize(after)
            self._assert_matches(after, allow_before=False)
        except BaseException:
            journal["status"] = "ROLLBACK_REQUIRED"
            self._write_journal(journal)
            try:
                self._safe_restore(before, acceptable=(before, after))
            except BaseException:
                raise
            journal["status"] = "ROLLED_BACK"
            self._write_journal(journal)
            raise
        changed = tuple(
            sorted(
                name
                for name in before
                if self._state_digest(before[name]) != self._state_digest(after[name])
            )
        )
        receipt = {
            "patch_id": artifact.patch_id,
            "change_set_id": artifact.patch_id,
            "patch_digest": artifact.digest,
            "snapshot_id": artifact.snapshot_id,
            "changed_paths": changed,
            "before": {name: self._state_digest(before[name]) for name in changed},
            "after": {name: self._state_digest(after[name]) for name in changed},
            "modes_before": {
                name: (None if before[name].get("state") == _MISSING else int(before[name]["mode"]))
                for name in changed
            },
            "modes_after": {
                name: (None if after[name].get("state") == _MISSING else int(after[name]["mode"]))
                for name in changed
            },
            "journal": str(journal_path),
        }
        receipt["actual_change_digest"] = value_digest(
            {
                "paths": receipt["changed_paths"],
                "before": receipt["before"],
                "after": receipt["after"],
                "modes_before": receipt["modes_before"],
                "modes_after": receipt["modes_after"],
            }
        )
        journal["status"] = "APPLIED"
        journal["receipt"] = receipt
        self._write_journal(journal)
        return receipt

    def _materialize(self, states: Mapping[str, Mapping[str, Any]]) -> None:
        # Remove first so rename sources disappear, then create final files.
        for name, state in states.items():
            target = canonical_path(self.workspace, name)
            if state.get("state") == _MISSING and target.exists():
                _regular_file(target)
                target.unlink()
        for name, state in states.items():
            if state.get("state") == _MISSING:
                continue
            target = canonical_path(self.workspace, name)
            data = base64.b64decode(str(state["data"]), validate=True)
            atomic_write_bytes(target, data, mode=int(state["mode"]))

    def _current_state(self, name: str) -> dict[str, Any]:
        return self._capture((name,))[name]

    def _assert_matches(self, states: Mapping[str, Mapping[str, Any]], *, allow_before: bool) -> None:
        del allow_before  # Kept explicit at call sites to make intent reviewable.
        for name, expected in states.items():
            actual = self._current_state(name)
            if not self._states_match(actual, expected):
                raise OperationConflict(f"workspace diverged at {name}")

    @classmethod
    def _states_match(cls, actual: Mapping[str, Any], expected: Mapping[str, Any]) -> bool:
        if cls._state_digest(actual) != cls._state_digest(expected):
            return False
        return expected.get("state") != "FILE" or int(actual["mode"]) == int(expected["mode"])

    def _safe_restore(
        self,
        before: Mapping[str, Mapping[str, Any]],
        *,
        acceptable: tuple[Mapping[str, Mapping[str, Any]], ...],
    ) -> None:
        for name in before:
            current = self._current_state(name)
            allowed = False
            for state_set in acceptable:
                expected = state_set[name]
                if self._states_match(current, expected):
                    allowed = True
                    break
            if not allowed:
                raise OperationConflict(f"refusing to overwrite post-patch user change: {name}")
        self._materialize(before)
        self._assert_matches(before, allow_before=False)

    def rollback(self, patch_id: str) -> Mapping[str, Any]:
        with self._effect_lock():
            return self._rollback_locked(patch_id)

    def _rollback_locked(self, patch_id: str) -> Mapping[str, Any]:
        path = self._journal_path(patch_id)
        if not path.exists():
            raise ContractError(f"unknown patch journal: {patch_id}")
        journal = self._read_journal(path)
        if journal.get("status") == "ROLLED_BACK":
            return {
                "patch_id": patch_id,
                "change_set_id": patch_id,
                "status": "ROLLED_BACK",
                "duplicate": True,
            }
        if journal.get("status") != "APPLIED":
            raise OperationConflict("only a completely applied patch can be rolled back; use recover()")
        self._safe_restore(journal["before"], acceptable=(journal["after"],))
        journal["status"] = "ROLLED_BACK"
        self._write_journal(journal)
        return {
            "patch_id": patch_id,
            "change_set_id": patch_id,
            "status": "ROLLED_BACK",
            "duplicate": False,
        }

    def recover(self, patch_id: str) -> Mapping[str, Any]:
        with self._effect_lock():
            return self._recover_locked(patch_id)

    def _recover_locked(self, patch_id: str) -> Mapping[str, Any]:
        path = self._journal_path(patch_id)
        if not path.exists():
            raise ContractError(f"unknown patch journal: {patch_id}")
        journal = self._read_journal(path)
        status = journal.get("status")
        if status in {"APPLIED", "ROLLED_BACK"}:
            return {
                "patch_id": patch_id,
                "change_set_id": patch_id,
                "status": status,
                "duplicate": True,
            }
        if status not in {"PREPARED", "APPLYING", "ROLLBACK_REQUIRED"}:
            raise ContractError("invalid patch journal state")
        self._safe_restore(journal["before"], acceptable=(journal["before"], journal["after"]))
        journal["status"] = "ROLLED_BACK"
        self._write_journal(journal)
        return {
            "patch_id": patch_id,
            "change_set_id": patch_id,
            "status": "ROLLED_BACK",
            "duplicate": False,
        }
