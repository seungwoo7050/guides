"""Stage 05 starter: inspect and isolate Git state without destroying user work."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable, Mapping

from .types import RepositorySnapshot


class GitAdapter:
    def __init__(self, workspace: Path) -> None:
        raise NotImplementedError("discover and pin the repository root")

    def snapshot(self) -> RepositorySnapshot:
        raise NotImplementedError("capture HEAD, branch, index, dirty paths, and file digests")

    def status(self) -> Mapping[str, object]:
        raise NotImplementedError

    def diff(self, *, staged: bool = False, paths: Iterable[str] = ()) -> str:
        raise NotImplementedError

    def assert_snapshot(self, snapshot: RepositorySnapshot) -> None:
        raise NotImplementedError

    def create_worktree(self, destination: Path, *, ref: str = "HEAD") -> Mapping[str, str]:
        raise NotImplementedError("create a detached agent worktree and preserve the source")

    create_isolated_worktree = create_worktree

    def remove_worktree(self, destination: Path) -> None:
        raise NotImplementedError("remove only a clean worktree created by this adapter")
