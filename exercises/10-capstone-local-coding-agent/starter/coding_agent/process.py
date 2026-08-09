"""Stage 05 starter: exact command catalog and bounded POSIX runner."""

from __future__ import annotations

import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable, Mapping, Sequence

from .types import CommandRequest, CommandResult


@dataclass(frozen=True)
class CommandSpec:
    command_id: str
    argv: tuple[str, ...]
    cwd: str = "."
    environment_keys: tuple[str, ...] = ()
    network_profiles: tuple[str, ...] = ("deny",)


class CommandCatalog:
    def __init__(self, specs: Iterable[CommandSpec] = ()) -> None:
        raise NotImplementedError("store and validate exact reviewed command entries")

    def register(
        self,
        spec: CommandSpec | str,
        argv: Sequence[str] | None = None,
        *,
        cwd: str = ".",
        environment_keys: Sequence[str] = (),
        network_profiles: Sequence[str] = ("deny",),
    ) -> CommandSpec:
        raise NotImplementedError

    def get(self, command_id: str) -> CommandSpec:
        raise NotImplementedError

    def validate(self, request: CommandRequest) -> CommandSpec:
        raise NotImplementedError("reject same ID with different argv/cwd/env/network")

    def entry_digest(self, command_id: str) -> str:
        raise NotImplementedError

    @property
    def digest(self) -> str:
        raise NotImplementedError


def workspace_digest(root: Path, *, excluded: Iterable[Path] = ()) -> str:
    raise NotImplementedError("hash file identity, bytes, symlinks, and modes")


class ProcessRunner:
    def __init__(
        self,
        workspace: Path,
        *,
        catalog: CommandCatalog,
        network_wrapper: Callable[[CommandRequest], Sequence[str]] | None = None,
        termination_grace_seconds: float = 0.25,
    ) -> None:
        raise NotImplementedError("initialize process-group and cancellation state")

    def cancel(self, command_id: str) -> bool:
        raise NotImplementedError

    def run(self, request: CommandRequest, *, cancel_event: threading.Event | None = None) -> CommandResult:
        raise NotImplementedError("bound time/output, drain pipes, and terminate descendants")
