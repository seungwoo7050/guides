"""Stage 04 starter: implement the safe filesystem and patch transaction."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable, Mapping

from .types import PatchArtifact, PatchOperation


def canonical_path(root: Path, value: str, *, must_exist: bool = False) -> Path:
    """Return a canonical in-workspace path; reject traversal and symlinks."""

    raise NotImplementedError("implement path canonicalization and symlink policy")


def read_text_file(root: Path, path: str, *, max_bytes: int = 1_000_000) -> Mapping[str, Any]:
    """Return bounded UTF-8 content, digest, size, and mode; reject binary/special files."""

    raise NotImplementedError("implement a bounded safe read")


def make_patch(snapshot_id: str, operations: Iterable[PatchOperation], *, patch_id: str | None = None) -> PatchArtifact:
    raise NotImplementedError("implement canonical patch artifact hashing")


class PatchEngine:
    def __init__(
        self,
        workspace: Path,
        *,
        journal_dir: Path | None = None,
        max_file_bytes: int = 1_000_000,
    ) -> None:
        raise NotImplementedError("initialize an isolated durable patch journal")

    def read(self, path: str, *, max_bytes: int | None = None) -> Mapping[str, Any]:
        raise NotImplementedError

    def prepare(
        self,
        snapshot_id: str,
        operations: Iterable[PatchOperation | Mapping[str, Any]],
        *,
        patch_id: str | None = None,
    ) -> PatchArtifact:
        raise NotImplementedError("validate the complete multi-file plan before mutation")

    def register(self, artifact: PatchArtifact) -> None:
        raise NotImplementedError

    def get(self, patch_id: str) -> PatchArtifact:
        raise NotImplementedError

    def apply(self, artifact: PatchArtifact | str) -> Mapping[str, Any]:
        raise NotImplementedError("journal, apply, verify, and compensate partial failure")

    def rollback(self, patch_id: str) -> Mapping[str, Any]:
        raise NotImplementedError("restore only the agent change set; preserve later user edits")

    def recover(self, patch_id: str) -> Mapping[str, Any]:
        raise NotImplementedError("reconcile PREPARED/APPLYING journal state")
