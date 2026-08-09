from __future__ import annotations

import hashlib
import os
import subprocess
from pathlib import Path
from typing import Iterable, Mapping, Sequence

from .errors import ContractError, OperationConflict, PolicyDenied
from .types import RepositorySnapshot
from .util import sha256_bytes, value_digest


class GitAdapter:
    """A local-only Git adapter that never resets, cleans, commits, or contacts remotes."""

    def __init__(self, workspace: Path) -> None:
        candidate = workspace.resolve(strict=True)
        top = self._raw(candidate, ("rev-parse", "--show-toplevel"), check=True).strip()
        self.workspace = Path(top).resolve(strict=True)
        try:
            candidate.relative_to(self.workspace)
        except ValueError as exc:
            raise ContractError("workspace is not inside the discovered repository") from exc
        self._created_worktrees: set[Path] = set()

    @staticmethod
    def _raw(cwd: Path, arguments: Sequence[str], *, check: bool) -> str:
        environment = {
            "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
            "LANG": "C",
            "LC_ALL": "C",
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_TERMINAL_PROMPT": "0",
        }
        completed = subprocess.run(
            ("git", "-c", "core.hooksPath=/dev/null", "-c", "core.fsmonitor=false", "-C", str(cwd), *arguments),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=environment,
            check=False,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        if check and completed.returncode != 0:
            raise ContractError(f"git {' '.join(arguments)} failed: {completed.stderr.strip()}")
        return completed.stdout

    def _git(self, arguments: Sequence[str], *, check: bool = True) -> str:
        forbidden = {"push", "fetch", "pull", "clone", "reset", "clean", "checkout", "commit"}
        if arguments and arguments[0] in forbidden:
            raise PolicyDenied(f"Git operation is outside this adapter: {arguments[0]}")
        return self._raw(self.workspace, arguments, check=check)

    def _optional(self, arguments: Sequence[str]) -> str | None:
        output = self._git(arguments, check=False).strip()
        return output or None

    def _names(self, arguments: Sequence[str]) -> tuple[str, ...]:
        output = self._git(arguments)
        return tuple(sorted(value for value in output.split("\0") if value))

    def _file_digests(self) -> Mapping[str, str]:
        names = self._names(("ls-files", "-co", "--exclude-standard", "-z"))
        result: dict[str, str] = {}
        for name in names:
            path = self.workspace / name
            try:
                metadata = path.lstat()
            except FileNotFoundError:
                continue
            if path.is_symlink():
                result[name] = sha256_bytes(b"SYMLINK\0" + os.readlink(path).encode("utf-8", "surrogateescape"))
            elif path.is_file():
                digest = hashlib.sha256()
                with path.open("rb") as handle:
                    for block in iter(lambda: handle.read(64 * 1024), b""):
                        digest.update(block)
                result[name] = "sha256:" + digest.hexdigest()
            else:
                result[name] = value_digest({"kind": "special", "mode": metadata.st_mode})
        return result

    def snapshot(self) -> RepositorySnapshot:
        head = self._optional(("rev-parse", "--verify", "HEAD"))
        branch = self._optional(("symbolic-ref", "--quiet", "--short", "HEAD"))
        staged = self._names(("diff", "--cached", "--name-only", "-z"))
        unstaged = self._names(("diff", "--name-only", "-z"))
        untracked = self._names(("ls-files", "--others", "--exclude-standard", "-z"))
        index_lines = self._git(("ls-files", "--stage", "-z"))
        index_tree = value_digest({"index": index_lines})
        files = self._file_digests()
        identity = {
            "root": str(self.workspace),
            "head": head,
            "branch": branch,
            "index_tree": index_tree,
            "staged": staged,
            "unstaged": unstaged,
            "untracked": untracked,
            "files": files,
        }
        return RepositorySnapshot(
            snapshot_id="snapshot-" + value_digest(identity).removeprefix("sha256:")[:20],
            root=str(self.workspace),
            head=head,
            branch=branch,
            index_tree=index_tree,
            staged=staged,
            unstaged=unstaged,
            untracked=untracked,
            files=files,
        )

    def status(self) -> Mapping[str, object]:
        snapshot = self.snapshot()
        return {
            "snapshot_id": snapshot.snapshot_id,
            "root": snapshot.root,
            "head": snapshot.head,
            "branch": snapshot.branch,
            "index_tree": snapshot.index_tree,
            "staged": snapshot.staged,
            "unstaged": snapshot.unstaged,
            "untracked": snapshot.untracked,
        }

    def diff(self, *, staged: bool = False, paths: Iterable[str] = ()) -> str:
        arguments = ["diff", "--no-ext-diff", "--no-color", "--binary"]
        if staged:
            arguments.append("--cached")
        safe_paths: list[str] = []
        for value in paths:
            candidate = Path(value)
            if candidate.is_absolute() or ".." in candidate.parts or not value:
                raise PolicyDenied("diff paths must be workspace-relative")
            safe_paths.append(value)
        if safe_paths:
            arguments.extend(("--", *safe_paths))
        return self._git(tuple(arguments))

    def assert_snapshot(self, snapshot: RepositorySnapshot) -> None:
        current = self.snapshot()
        fields = ("root", "head", "branch", "index_tree", "staged", "unstaged", "untracked", "files")
        if any(getattr(current, field) != getattr(snapshot, field) for field in fields):
            raise OperationConflict("repository diverged from the expected snapshot")

    def create_worktree(self, destination: Path, *, ref: str = "HEAD") -> Mapping[str, str]:
        if not ref or ref.startswith("-") or "\x00" in ref:
            raise ContractError("invalid worktree ref")
        before = self.snapshot()
        target = destination.resolve()
        if target == self.workspace or self.workspace in target.parents:
            raise PolicyDenied("agent worktree must not be nested inside the source workspace")
        if target.exists():
            raise OperationConflict("worktree destination must not already exist")
        self._git(("worktree", "add", "--detach", str(target), ref))
        self._created_worktrees.add(target)
        # Adding Git metadata must not alter the source worktree/index.
        self.assert_snapshot(before)
        head = self._raw(target, ("rev-parse", "--verify", "HEAD"), check=True).strip()
        return {
            "path": str(target),
            "head": head,
            "source_snapshot_id": before.snapshot_id,
        }

    create_isolated_worktree = create_worktree

    def remove_worktree(self, destination: Path) -> None:
        target = destination.resolve()
        if target not in self._created_worktrees:
            raise PolicyDenied("adapter only removes worktrees it created in this process")
        status = self._raw(
            target,
            ("status", "--porcelain", "--untracked-files=all", "--ignored=matching"),
            check=True,
        )
        if status:
            raise OperationConflict("refusing to remove a dirty agent worktree")
        self._git(("worktree", "remove", str(target)))
        self._created_worktrees.remove(target)
