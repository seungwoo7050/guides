from __future__ import annotations

import hashlib
import math
import os
import signal
import subprocess
import sys
import threading
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Callable, Iterable, Mapping, Sequence

from .errors import ContractError, PolicyDenied
from .patching import canonical_path
from .types import CommandRequest, CommandResult
from .util import value_digest


@dataclass(frozen=True)
class CommandSpec:
    command_id: str
    argv: tuple[str, ...]
    cwd: str = "."
    environment_keys: tuple[str, ...] = ()
    network_profiles: tuple[str, ...] = ("deny",)


class CommandCatalog:
    """An immutable-by-entry catalog: a command ID is an exact argv contract."""

    VERSION = "1"

    def __init__(self, specs: Iterable[CommandSpec] = ()) -> None:
        self._specs: dict[str, CommandSpec] = {}
        for spec in specs:
            self.register(spec)

    def register(
        self,
        spec: CommandSpec | str,
        argv: Sequence[str] | None = None,
        *,
        cwd: str = ".",
        environment_keys: Sequence[str] = (),
        network_profiles: Sequence[str] = ("deny",),
    ) -> CommandSpec:
        if isinstance(spec, str):
            spec = CommandSpec(
                command_id=spec,
                argv=tuple(argv or ()),
                cwd=cwd,
                environment_keys=tuple(environment_keys),
                network_profiles=tuple(network_profiles),
            )
        elif argv is not None:
            raise ContractError("argv must not be supplied with a CommandSpec")
        self._validate_spec(spec)
        existing = self._specs.get(spec.command_id)
        if existing is not None and existing != spec:
            raise ContractError("command ID reused with a different specification")
        self._specs[spec.command_id] = spec
        return spec

    @staticmethod
    def _validate_spec(spec: CommandSpec) -> None:
        if not spec.command_id or not spec.argv or any(not isinstance(value, str) or not value or "\x00" in value for value in spec.argv):
            raise ContractError("catalog commands require an ID and non-empty NUL-free argv")
        if not isinstance(spec.cwd, str) or not spec.cwd or "\x00" in spec.cwd:
            raise ContractError("catalog cwd must be a non-empty string")
        if any(profile not in {"deny", "loopback", "allow"} for profile in spec.network_profiles):
            raise ContractError("invalid command network profile")
        if not spec.network_profiles:
            raise ContractError("a command must publish at least one network profile")
        if len(set(spec.environment_keys)) != len(spec.environment_keys):
            raise ContractError("duplicate environment key in command catalog")
        for key in spec.environment_keys:
            if not key or not key.replace("_", "A").isalnum() or key[0].isdigit():
                raise ContractError(f"invalid environment key: {key!r}")

    def get(self, command_id: str) -> CommandSpec:
        try:
            return self._specs[command_id]
        except KeyError as exc:
            raise PolicyDenied(f"command is not registered: {command_id}") from exc

    def validate(self, request: CommandRequest) -> CommandSpec:
        spec = self.get(request.command_id)
        if request.argv != spec.argv:
            raise PolicyDenied("command argv differs from its reviewed catalog entry")
        if request.cwd != spec.cwd:
            raise PolicyDenied("command cwd differs from its reviewed catalog entry")
        if request.network not in spec.network_profiles:
            raise PolicyDenied("command network profile is not registered")
        unknown = set(request.environment) - set(spec.environment_keys)
        if unknown:
            raise PolicyDenied(f"command environment keys are not registered: {sorted(unknown)!r}")
        return spec

    def entry_digest(self, command_id: str) -> str:
        return value_digest(asdict(self.get(command_id)))

    @property
    def digest(self) -> str:
        return value_digest(
            {
                "catalog_version": self.VERSION,
                "commands": [asdict(self._specs[key]) for key in sorted(self._specs)],
            }
        )


class _OutputBudget:
    def __init__(self, limit: int) -> None:
        self.limit = limit
        self.remaining = limit
        self.truncated = False
        self._lock = threading.Lock()

    def take(self, value: bytes) -> bytes:
        with self._lock:
            amount = min(self.remaining, len(value))
            self.remaining -= amount
            if amount != len(value):
                self.truncated = True
            return value[:amount]


def workspace_digest(root: Path, *, excluded: Iterable[Path] = ()) -> str:
    root = root.resolve(strict=True)
    excluded_resolved = tuple(path.resolve() for path in excluded)
    digest = hashlib.sha256()
    for path in sorted(root.rglob("*"), key=lambda item: item.relative_to(root).as_posix()):
        try:
            if any(path == item or item in path.parents for item in excluded_resolved):
                continue
            relative = path.relative_to(root).as_posix().encode("utf-8")
            metadata = path.lstat()
            if path.is_symlink():
                kind = b"L"
                content = os.readlink(path).encode("utf-8", "surrogateescape")
            elif path.is_file():
                kind = b"F"
                file_hash = hashlib.sha256()
                with path.open("rb") as handle:
                    for block in iter(lambda: handle.read(64 * 1024), b""):
                        file_hash.update(block)
                content = file_hash.digest()
            elif path.is_dir():
                continue
            else:
                kind = b"S"
                content = b""
            digest.update(kind + b"\0" + relative + b"\0")
            digest.update(f"{metadata.st_mode & 0o7777:o}".encode("ascii") + b"\0" + content + b"\0")
        except FileNotFoundError:
            # A concurrently changing workspace is represented by a different
            # after digest; disappearing paths need not crash the collector.
            digest.update(b"RACE\0")
    return "sha256:" + digest.hexdigest()


class ProcessRunner:
    """POSIX argv runner with bounded output and process-group cancellation.

    Network isolation cannot be implemented portably with Python's standard
    library.  The optional ``network_wrapper`` must therefore be supplied by a
    real sandbox for untrusted commands.  The catalog and policy still prevent a
    model from selecting an unreviewed network command or profile.
    """

    _NETWORK_CLIENTS = {"curl", "wget", "nc", "netcat", "ncat", "ssh", "scp", "sftp", "ftp", "telnet"}

    def __init__(
        self,
        workspace: Path,
        *,
        catalog: CommandCatalog,
        network_wrapper: Callable[[CommandRequest], Sequence[str]] | None = None,
        termination_grace_seconds: float = 0.25,
    ) -> None:
        self.workspace = workspace.resolve(strict=True)
        if not self.workspace.is_dir():
            raise ContractError("process workspace must be a directory")
        self.catalog = catalog
        self.network_wrapper = network_wrapper
        self.termination_grace_seconds = max(0.01, termination_grace_seconds)
        self._cancel_events: dict[str, threading.Event] = {}
        self._lock = threading.Lock()

    def cancel(self, command_id: str) -> bool:
        with self._lock:
            event = self._cancel_events.get(command_id)
            if event is None:
                return False
            event.set()
            return True

    def _cwd(self, value: str) -> Path:
        if value == ".":
            return self.workspace
        target = canonical_path(self.workspace, value, must_exist=True)
        if not target.is_dir():
            raise PolicyDenied("command cwd is not a directory")
        return target

    @staticmethod
    def _clean_environment(extra: Mapping[str, str]) -> dict[str, str]:
        environment = {
            "PATH": f"{Path(sys.executable).resolve().parent}:/usr/bin:/bin",
            "LANG": "C.UTF-8",
            "LC_ALL": "C.UTF-8",
            "PYTHONUNBUFFERED": "1",
        }
        for key, value in extra.items():
            if not isinstance(key, str) or not isinstance(value, str) or "\x00" in key or "\x00" in value or "=" in key:
                raise ContractError("command environment must contain NUL-free string pairs")
            environment[key] = value
        return environment

    def run(self, request: CommandRequest, *, cancel_event: threading.Event | None = None) -> CommandResult:
        if not request.command_id or not request.argv:
            raise ContractError("command ID and argv are required")
        if (
            isinstance(request.timeout_seconds, bool)
            or not isinstance(request.timeout_seconds, (int, float))
            or not math.isfinite(request.timeout_seconds)
            or request.timeout_seconds <= 0
        ):
            raise ContractError("timeout_seconds must be positive")
        if (
            isinstance(request.max_output_bytes, bool)
            or not isinstance(request.max_output_bytes, int)
            or request.max_output_bytes < 0
        ):
            raise ContractError("max_output_bytes must be a non-negative integer")
        self.catalog.validate(request)
        cwd = self._cwd(request.cwd)
        executable = os.path.basename(request.argv[0])
        if request.network != "allow" and executable in self._NETWORK_CLIENTS:
            raise PolicyDenied("general network client requires the allow profile")
        argv = list(request.argv)
        if self.network_wrapper is not None:
            argv = list(self.network_wrapper(request)) + argv
        before = workspace_digest(self.workspace)
        started = time.monotonic()
        local_cancel = cancel_event or threading.Event()
        with self._lock:
            if request.command_id in self._cancel_events:
                raise ContractError(f"command already running: {request.command_id}")
            self._cancel_events[request.command_id] = local_cancel
        process: subprocess.Popen[bytes] | None = None
        try:
            try:
                process = subprocess.Popen(
                    argv,
                    cwd=cwd,
                    env=self._clean_environment(request.environment),
                    stdin=subprocess.DEVNULL,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    shell=False,
                    start_new_session=True,
                )
            except OSError as exc:
                duration_ms = int((time.monotonic() - started) * 1000)
                return CommandResult(
                    command_id=request.command_id,
                    exit_kind="SPAWN_ERROR",
                    exit_code=None,
                    signal=None,
                    stdout="",
                    stderr=str(exc),
                    truncated=False,
                    duration_ms=duration_ms,
                    cleanup_status="NOT_STARTED",
                    workspace_before=before,
                    workspace_after=workspace_digest(self.workspace),
                )
            budget = _OutputBudget(request.max_output_bytes)
            stdout_chunks: list[bytes] = []
            stderr_chunks: list[bytes] = []

            def drain(stream, destination: list[bytes]) -> None:
                try:
                    while True:
                        block = stream.read(16 * 1024)
                        if not block:
                            break
                        kept = budget.take(block)
                        if kept:
                            destination.append(kept)
                finally:
                    stream.close()

            stdout_thread = threading.Thread(target=drain, args=(process.stdout, stdout_chunks), daemon=True)
            stderr_thread = threading.Thread(target=drain, args=(process.stderr, stderr_chunks), daemon=True)
            stdout_thread.start()
            stderr_thread.start()
            stop_reason: str | None = None
            deadline = started + request.timeout_seconds
            while process.poll() is None:
                if local_cancel.is_set():
                    stop_reason = "CANCELLED"
                    break
                if time.monotonic() >= deadline:
                    stop_reason = "TIMEOUT"
                    break
                time.sleep(0.01)
            cleanup_status = "CLEAN"
            if stop_reason is not None:
                cleanup_status = self._terminate_group(process)
            return_code = process.wait()
            if stop_reason is None:
                # A successful parent may have left a server or other descendant
                # alive with inherited pipes.  No command outlives its receipt.
                try:
                    os.killpg(process.pid, 0)
                except ProcessLookupError:
                    pass
                else:
                    cleanup_status = self._terminate_group(process)
            stdout_thread.join(timeout=2.0)
            stderr_thread.join(timeout=2.0)
            if stdout_thread.is_alive() or stderr_thread.is_alive():
                cleanup_status = "OUTPUT_DRAIN_FAILED"
            duration_ms = int((time.monotonic() - started) * 1000)
            terminating_signal = -return_code if return_code < 0 else None
            if stop_reason is not None:
                exit_kind = stop_reason
                exit_code = None
            elif terminating_signal is not None:
                exit_kind = "SIGNAL"
                exit_code = None
            elif return_code == 0:
                exit_kind = "SUCCESS"
                exit_code = 0
            else:
                exit_kind = "NONZERO"
                exit_code = return_code
            return CommandResult(
                command_id=request.command_id,
                exit_kind=exit_kind,
                exit_code=exit_code,
                signal=terminating_signal,
                stdout=b"".join(stdout_chunks).decode("utf-8", "replace"),
                stderr=b"".join(stderr_chunks).decode("utf-8", "replace"),
                truncated=budget.truncated,
                duration_ms=duration_ms,
                cleanup_status=cleanup_status,
                workspace_before=before,
                workspace_after=workspace_digest(self.workspace),
            )
        finally:
            if process is not None and process.poll() is None:
                self._terminate_group(process)
            with self._lock:
                self._cancel_events.pop(request.command_id, None)

    def _terminate_group(self, process: subprocess.Popen[bytes]) -> str:
        try:
            os.killpg(process.pid, signal.SIGTERM)
        except ProcessLookupError:
            return "CLEAN"
        try:
            process.wait(timeout=self.termination_grace_seconds)
        except subprocess.TimeoutExpired:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            try:
                process.wait(timeout=self.termination_grace_seconds)
            except subprocess.TimeoutExpired:
                return "PROCESS_GROUP_SURVIVED"
            return "KILLED"
        # The group may still contain a child after its leader exits. Give every
        # descendant the same grace interval to run its SIGTERM cleanup handler.
        deadline = time.monotonic() + self.termination_grace_seconds
        while time.monotonic() < deadline:
            try:
                os.killpg(process.pid, 0)
            except ProcessLookupError:
                return "TERMINATED"
            time.sleep(0.01)
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            return "TERMINATED"
        return "KILLED"
