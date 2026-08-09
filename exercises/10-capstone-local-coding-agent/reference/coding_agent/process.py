from __future__ import annotations

import hashlib
import math
import os
import re
import signal
import shutil
import stat
import subprocess
import sys
import threading
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Callable, Iterable, Mapping, Sequence

from .errors import ContractError, OperationConflict, PolicyDenied
from .patching import canonical_path
from .types import CommandRequest, CommandResult
from .util import value_digest


@dataclass(frozen=True)
class CommandSpec:
    command_id: str
    argv: tuple[str, ...]
    cwd: str = "."
    environment: tuple[tuple[str, str], ...] = ()
    network_profiles: tuple[str, ...] = ("deny",)
    timeout_seconds: float = 30.0
    max_output_bytes: int = 100_000


class CommandCatalog:
    """An immutable-by-entry catalog: a command ID is an exact argv contract."""

    VERSION = "1"
    MAX_TIMEOUT_SECONDS = 300.0
    MAX_OUTPUT_BYTES = 2_000_000
    _IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
    _FORBIDDEN_ENVIRONMENT = {
        "PATH",
        "HOME",
        "SHELL",
        "ENV",
        "BASH_ENV",
        "CDPATH",
        "GIT_EXEC_PATH",
    }
    _FORBIDDEN_ENVIRONMENT_PREFIXES = ("PYTHON", "LD_", "DYLD_")

    def __init__(
        self,
        specs: Iterable[CommandSpec] = (),
        *,
        workspace: Path | None = None,
    ) -> None:
        self._specs: dict[str, CommandSpec] = {}
        self._integrity: dict[str, Mapping[str, str | None]] = {}
        self._workspace: Path | None = None
        self._frozen = False
        for spec in specs:
            self.register(spec)
        if workspace is not None:
            self.bind_workspace(workspace)

    def register(
        self,
        spec: CommandSpec | str,
        argv: Sequence[str] | None = None,
        *,
        cwd: str = ".",
        environment: Mapping[str, str] | None = None,
        network_profiles: Sequence[str] = ("deny",),
        timeout_seconds: float = 30.0,
        max_output_bytes: int = 100_000,
    ) -> CommandSpec:
        if self._frozen:
            raise ContractError("command catalog is frozen")
        if isinstance(spec, str):
            if argv is None or isinstance(argv, (str, bytes)):
                raise ContractError("catalog argv must be a non-string sequence")
            if environment is not None and not isinstance(environment, Mapping):
                raise ContractError("catalog environment must be an object")
            if isinstance(network_profiles, (str, bytes)):
                raise ContractError("network_profiles must be a non-string sequence")
            spec = CommandSpec(
                command_id=spec,
                argv=tuple(argv),
                cwd=cwd,
                environment=tuple(sorted((environment or {}).items())),
                network_profiles=tuple(network_profiles),
                timeout_seconds=timeout_seconds,
                max_output_bytes=max_output_bytes,
            )
        elif argv is not None:
            raise ContractError("argv must not be supplied with a CommandSpec")
        self._validate_spec(spec)
        existing = self._specs.get(spec.command_id)
        if existing is not None:
            if existing != spec:
                raise ContractError("command ID reused with a different specification")
            # Re-registering an identical entry must not silently move the
            # review baseline to bytes changed since the first registration.
            return existing
        self._specs[spec.command_id] = spec
        self._integrity[spec.command_id] = self._resolve_integrity(
            spec, workspace=self._workspace
        )
        return spec

    @classmethod
    def _validate_spec(cls, spec: CommandSpec) -> None:
        if not isinstance(spec, CommandSpec):
            raise ContractError("command catalog entries must be CommandSpec values")
        if (
            not isinstance(spec.command_id, str)
            or not cls._IDENTIFIER.fullmatch(spec.command_id)
        ):
            raise ContractError("command_id is not a valid bounded identifier")
        if not isinstance(spec.argv, tuple):
            raise ContractError("catalog argv must be a tuple")
        bad_argv = any(
            not isinstance(value, str) or not value or "\x00" in value for value in spec.argv
        )
        if not spec.argv or bad_argv:
            raise ContractError("catalog commands require an ID and non-empty NUL-free argv")
        if not isinstance(spec.cwd, str) or not spec.cwd or "\x00" in spec.cwd:
            raise ContractError("catalog cwd must be a non-empty string")
        cwd = Path(spec.cwd)
        if (
            cwd.is_absolute()
            or ".." in cwd.parts
            or (spec.cwd != "." and cwd.as_posix() != spec.cwd)
        ):
            raise ContractError("catalog cwd must be canonical and workspace-relative")
        if not isinstance(spec.network_profiles, tuple):
            raise ContractError("catalog network_profiles must be a tuple")
        if any(profile not in {"deny", "loopback", "allow"} for profile in spec.network_profiles):
            raise ContractError("invalid command network profile")
        if not spec.network_profiles:
            raise ContractError("a command must publish at least one network profile")
        if len(set(spec.network_profiles)) != len(spec.network_profiles):
            raise ContractError("duplicate command network profile")
        if not isinstance(spec.environment, tuple) or any(
            not isinstance(item, tuple) or len(item) != 2 for item in spec.environment
        ):
            raise ContractError("catalog environment must be a tuple of key/value tuples")
        keys = [key for key, _value in spec.environment]
        if len(set(keys)) != len(keys):
            raise ContractError("duplicate environment key in command catalog")
        for key, value in spec.environment:
            if (
                not isinstance(key, str)
                or not key
                or not key.isascii()
                or not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", key)
                or not isinstance(value, str)
                or "\x00" in key
                or "\x00" in value
            ):
                raise ContractError(f"invalid catalog environment entry: {key!r}")
            if key in cls._FORBIDDEN_ENVIRONMENT or key.startswith(
                cls._FORBIDDEN_ENVIRONMENT_PREFIXES
            ):
                raise ContractError(f"catalog environment may not alter execution identity: {key}")
        if spec.environment != tuple(sorted(spec.environment)):
            raise ContractError("catalog environment must use canonical key order")
        if (
            isinstance(spec.timeout_seconds, bool)
            or not isinstance(spec.timeout_seconds, (int, float))
            or not math.isfinite(spec.timeout_seconds)
            or spec.timeout_seconds <= 0
            or spec.timeout_seconds > cls.MAX_TIMEOUT_SECONDS
        ):
            raise ContractError(
                f"catalog timeout_seconds must be between 0 and {cls.MAX_TIMEOUT_SECONDS}"
            )
        if (
            isinstance(spec.max_output_bytes, bool)
            or not isinstance(spec.max_output_bytes, int)
            or spec.max_output_bytes < 0
            or spec.max_output_bytes > cls.MAX_OUTPUT_BYTES
        ):
            raise ContractError(
                f"catalog max_output_bytes must be between 0 and {cls.MAX_OUTPUT_BYTES}"
            )

    @staticmethod
    def _digest_file(path: Path) -> str:
        flags = os.O_RDONLY
        flags |= getattr(os, "O_CLOEXEC", 0)
        flags |= getattr(os, "O_NOFOLLOW", 0)
        try:
            descriptor = os.open(path, flags)
        except OSError as exc:
            raise ContractError(f"cannot open reviewed command file: {path}") from exc
        try:
            before = os.fstat(descriptor)
            if not stat.S_ISREG(before.st_mode):
                raise ContractError(f"reviewed command file is not regular: {path}")
            digest = hashlib.sha256()
            with os.fdopen(descriptor, "rb", closefd=False) as handle:
                for block in iter(lambda: handle.read(128 * 1024), b""):
                    digest.update(block)
            after = os.fstat(descriptor)
            identity_before = (
                before.st_dev,
                before.st_ino,
                before.st_size,
                before.st_mtime_ns,
                before.st_ctime_ns,
            )
            identity_after = (
                after.st_dev,
                after.st_ino,
                after.st_size,
                after.st_mtime_ns,
                after.st_ctime_ns,
            )
            if identity_before != identity_after:
                raise ContractError(f"reviewed command file changed while hashing: {path}")
            return "sha256:" + digest.hexdigest()
        finally:
            os.close(descriptor)

    @staticmethod
    def _python_script_argument(argv: tuple[str, ...]) -> str | None:
        index = 1
        while index < len(argv):
            argument = argv[index]
            if argument in {"-c", "-m"}:
                return None
            if argument == "--":
                return argv[index + 1] if index + 1 < len(argv) else None
            if argument in {"-W", "-X", "--check-hash-based-pycs"}:
                index += 2
                continue
            if argument.startswith("-"):
                index += 1
                continue
            return argument
        return None

    @classmethod
    def _resolve_integrity(
        cls,
        spec: CommandSpec,
        *,
        workspace: Path | None = None,
    ) -> Mapping[str, str | None]:
        search_path = os.pathsep.join(
            (str(Path(sys.executable).resolve().parent), "/usr/bin", "/bin")
        )
        executable_raw = spec.argv[0]
        executable_is_path = (
            os.path.isabs(executable_raw)
            or os.sep in executable_raw
            or (os.altsep is not None and os.altsep in executable_raw)
        )
        try:
            if os.path.isabs(executable_raw):
                executable = Path(executable_raw).resolve(strict=True)
            elif executable_is_path:
                if workspace is None:
                    return {
                        "executable": executable_raw,
                        "executable_digest": None,
                        "script": None,
                        "script_digest": None,
                    }
                relative = Path(spec.cwd) / Path(executable_raw)
                if ".." in relative.parts:
                    raise ContractError(
                        "catalog executable must be canonical and workspace-relative"
                    )
                executable = canonical_path(
                    workspace,
                    relative.as_posix(),
                    must_exist=True,
                ).resolve(strict=True)
            else:
                found = shutil.which(executable_raw, path=search_path)
                if found is None:
                    raise ContractError(
                        f"catalog executable cannot be resolved: {executable_raw}"
                    )
                executable = Path(found).resolve(strict=True)
        except OSError as exc:
            raise ContractError(
                f"catalog executable cannot be resolved: {executable_raw}"
            ) from exc
        if not executable.is_file():
            raise ContractError(f"catalog executable is not a regular file: {executable}")
        if not os.access(executable, os.X_OK):
            raise ContractError(f"catalog executable is not executable: {executable}")
        script: Path | None = None
        script_argument: str | None = None
        if executable.name.lower().startswith(("python", "pypy")):
            script_argument = cls._python_script_argument(spec.argv)
            if script_argument is not None:
                candidate = Path(script_argument)
                if not candidate.is_absolute():
                    if workspace is None:
                        return {
                            "executable": str(executable),
                            "executable_digest": cls._digest_file(executable),
                            "script": script_argument,
                            "script_digest": None,
                        }
                    relative = Path(spec.cwd) / candidate
                    if ".." in relative.parts:
                        raise ContractError(
                            "catalog script must be canonical and workspace-relative"
                        )
                    candidate = canonical_path(
                        workspace,
                        relative.as_posix(),
                        must_exist=True,
                    )
                try:
                    script = candidate.resolve(strict=True)
                except OSError as exc:
                    raise ContractError(
                        f"catalog script cannot be resolved: {candidate}"
                    ) from exc
                if not script.is_file():
                    raise ContractError(f"catalog script is not a regular file: {script}")
        return {
            "executable": str(executable),
            "executable_digest": cls._digest_file(executable),
            "script": str(script) if script is not None else None,
            "script_digest": cls._digest_file(script) if script is not None else None,
        }

    def bind_workspace(self, workspace: Path) -> None:
        root = workspace.resolve(strict=True)
        if not root.is_dir():
            raise ContractError("command catalog workspace must be a directory")
        if self._workspace is not None:
            if self._workspace != root:
                raise ContractError("command catalog is already bound to another workspace")
            # Binding is a review boundary, not a refresh operation.  Keeping
            # the first baseline prevents changed scripts from being blessed by
            # constructing another runner with the same catalog.
            return
        if self._frozen:
            raise ContractError("a frozen command catalog cannot be newly bound")
        self._workspace = root
        self._integrity = {
            command_id: self._resolve_integrity(spec, workspace=root)
            for command_id, spec in self._specs.items()
        }

    def freeze(self, workspace: Path | None = None) -> str:
        if workspace is not None:
            self.bind_workspace(workspace)
        if any(
            value.get("executable_digest") is None
            or (value.get("script") is not None and value.get("script_digest") is None)
            for value in self._integrity.values()
        ):
            raise ContractError("relative command files require a bound workspace")
        self._frozen = True
        return self.digest

    def get(self, command_id: str) -> CommandSpec:
        try:
            return self._specs[command_id]
        except KeyError as exc:
            raise PolicyDenied(f"command is not registered: {command_id}") from exc

    def validate(self, request: CommandRequest) -> CommandSpec:
        if not isinstance(request, CommandRequest):
            raise ContractError("command request must be a CommandRequest")
        spec = self.get(request.command_id)
        if request.argv != spec.argv:
            raise PolicyDenied("command argv differs from its reviewed catalog entry")
        if request.cwd != spec.cwd:
            raise PolicyDenied("command cwd differs from its reviewed catalog entry")
        if request.timeout_seconds != spec.timeout_seconds:
            raise PolicyDenied("command timeout differs from its reviewed catalog entry")
        if request.max_output_bytes != spec.max_output_bytes:
            raise PolicyDenied("command output limit differs from its reviewed catalog entry")
        if request.network not in spec.network_profiles:
            raise PolicyDenied("command network profile is not registered")
        if not isinstance(request.environment, Mapping):
            raise ContractError("command environment must be an object")
        try:
            requested_environment = dict(request.environment)
        except (TypeError, ValueError) as exc:
            raise ContractError("command environment must contain key/value pairs") from exc
        if requested_environment != dict(spec.environment):
            raise PolicyDenied("command environment differs from its reviewed catalog entry")
        expected_integrity = self._integrity[spec.command_id]
        if expected_integrity.get("executable_digest") is None or (
            expected_integrity.get("script") is not None
            and expected_integrity.get("script_digest") is None
        ):
            raise ContractError("relative command files require a bound workspace")
        try:
            current_integrity = self._resolve_integrity(
                spec, workspace=self._workspace
            )
        except (ContractError, OperationConflict, PolicyDenied) as exc:
            raise PolicyDenied(
                "command executable or script changed after review"
            ) from exc
        if current_integrity != expected_integrity:
            raise PolicyDenied("command executable or script digest changed after review")
        return spec

    def entry_digest(self, command_id: str) -> str:
        return value_digest(
            {"spec": asdict(self.get(command_id)), "integrity": self._integrity[command_id]}
        )

    def integrity(self, command_id: str) -> Mapping[str, str | None]:
        self.get(command_id)
        return dict(self._integrity[command_id])

    @property
    def digest(self) -> str:
        return value_digest(
            {
                "catalog_version": self.VERSION,
                "commands": [
                    {"spec": asdict(self._specs[key]), "integrity": self._integrity[key]}
                    for key in sorted(self._specs)
                ],
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


def _decode_bounded(value: bytes, limit: int) -> tuple[str, bool]:
    text = value.decode("utf-8", "replace")
    encoded = text.encode("utf-8")
    if len(encoded) <= limit:
        return text, False
    return encoded[:limit].decode("utf-8", "ignore"), True


def workspace_digest(root: Path, *, excluded: Iterable[Path] = ()) -> str:
    root = root.resolve(strict=True)
    excluded_resolved = (root / ".git", root / ".agent-state", root / ".verifier") + tuple(
        path.resolve() for path in excluded
    )
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
    _BROAD_INTERPRETERS = {"sh", "bash", "zsh", "dash", "ksh", "fish"}
    _INDIRECT_EXECUTORS = {"env", "xcrun", "command", "nohup", "nice", "timeout", "setsid"}

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
        self.catalog_digest = catalog.freeze(self.workspace)
        self.network_wrapper = network_wrapper
        if (
            isinstance(termination_grace_seconds, bool)
            or not isinstance(termination_grace_seconds, (int, float))
            or not math.isfinite(termination_grace_seconds)
            or not 0.01 <= termination_grace_seconds <= 10.0
        ):
            raise ContractError("termination grace must be between 0.01 and 10 seconds")
        self.termination_grace_seconds = float(termination_grace_seconds)
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
        if (
            not isinstance(request, CommandRequest)
            or not request.command_id
            or not request.argv
        ):
            raise ContractError("command ID and argv are required")
        if self.catalog.digest != self.catalog_digest:
            raise ContractError("command catalog changed after runner initialization")
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
        spec = self.catalog.validate(request)
        execution_request = CommandRequest(
            command_id=spec.command_id,
            argv=spec.argv,
            cwd=spec.cwd,
            environment=dict(spec.environment),
            timeout_seconds=spec.timeout_seconds,
            max_output_bytes=spec.max_output_bytes,
            network=request.network,
        )
        cwd = self._cwd(spec.cwd)
        integrity = self.catalog.integrity(request.command_id)
        executable_path = str(integrity["executable"])
        executable = os.path.basename(executable_path)
        if executable in self._BROAD_INTERPRETERS:
            raise PolicyDenied("broad shell commands are outside the check runner")
        if executable == "git":
            raise PolicyDenied("Git commands must use the dedicated Git adapter")
        if executable in self._INDIRECT_EXECUTORS:
            raise PolicyDenied("indirect command launchers are outside the check runner")
        if execution_request.network != "allow" and executable in self._NETWORK_CLIENTS:
            raise PolicyDenied("general network client requires the allow profile")
        argv = [executable_path, *spec.argv[1:]]
        if self.network_wrapper is not None:
            prefix = self.network_wrapper(execution_request)
            if isinstance(prefix, (str, bytes)) or not isinstance(prefix, Sequence) or any(
                not isinstance(item, str) or not item or "\x00" in item for item in prefix
            ):
                raise ContractError("network wrapper must return a NUL-free argv prefix")
            argv = list(prefix) + argv
        before = workspace_digest(self.workspace)
        started = time.monotonic()
        local_cancel = cancel_event or threading.Event()
        with self._lock:
            if request.command_id in self._cancel_events:
                raise ContractError(f"command already running: {request.command_id}")
            self._cancel_events[request.command_id] = local_cancel
        process: subprocess.Popen[bytes] | None = None
        try:
            if local_cancel.is_set():
                return CommandResult(
                    command_id=request.command_id,
                    exit_kind="CANCELLED",
                    exit_code=None,
                    signal=None,
                    stdout="",
                    stderr="",
                    truncated=False,
                    duration_ms=0,
                    cleanup_status="NOT_STARTED",
                    workspace_before=before,
                    workspace_after=before,
                )
            try:
                # Recheck immediately before spawn.  The absolute executable
                # removes PATH lookup from the final execution decision.
                self.catalog.validate(execution_request)
                process = subprocess.Popen(
                    argv,
                    cwd=cwd,
                    env=self._clean_environment(execution_request.environment),
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
            budget = _OutputBudget(spec.max_output_bytes)
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
            deadline = started + spec.timeout_seconds
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
            stdout, stdout_display_truncated = _decode_bounded(
                b"".join(stdout_chunks), spec.max_output_bytes
            )
            remaining_display = max(
                0, spec.max_output_bytes - len(stdout.encode("utf-8"))
            )
            stderr, stderr_display_truncated = _decode_bounded(
                b"".join(stderr_chunks), remaining_display
            )
            return CommandResult(
                command_id=request.command_id,
                exit_kind=exit_kind,
                exit_code=exit_code,
                signal=terminating_signal,
                stdout=stdout,
                stderr=stderr,
                truncated=(
                    budget.truncated
                    or stdout_display_truncated
                    or stderr_display_truncated
                ),
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
        except PermissionError:
            return "PROCESS_GROUP_SURVIVED"
        try:
            process.wait(timeout=self.termination_grace_seconds)
        except subprocess.TimeoutExpired:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            except PermissionError:
                return "PROCESS_GROUP_SURVIVED"
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
            except PermissionError:
                # EPERM still proves that a group with this ID exists.  Do not
                # crash or misreport it as clean merely because the host denied
                # the probe.
                return "PROCESS_GROUP_SURVIVED"
            time.sleep(0.01)
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            return "TERMINATED"
        except PermissionError:
            return "PROCESS_GROUP_SURVIVED"
        return "KILLED"
