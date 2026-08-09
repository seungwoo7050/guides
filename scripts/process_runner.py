#!/usr/bin/env python3
from __future__ import annotations

import os
import signal
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Sequence

DEADLINE_ENV = "MOBILE_APP_GUIDE_DEADLINE_MONOTONIC"


class CommandSpawnError(RuntimeError):
    def __init__(self, command: Sequence[str], error: OSError):
        self.command = tuple(command)
        self.error = error
        super().__init__(f"command spawn failed: {' '.join(command)}: {error}")


class ProcessInterrupted(KeyboardInterrupt):
    def __init__(self, signum: int):
        self.signum = signum
        super().__init__(signal.Signals(signum).name)


@dataclass(frozen=True)
class ProcessResult:
    command: tuple[str, ...]
    returncode: int | None
    stdout: str
    stderr: str
    duration_seconds: float
    timed_out: bool
    deadline_monotonic: float


def inherited_deadline() -> float | None:
    raw = os.environ.get(DEADLINE_ENV)
    if not raw:
        return None
    try:
        value = float(raw)
    except ValueError:
        return None
    return value if value > 0 else None


def deadline_after(timeout_seconds: float, parent_deadline: float | None = None) -> float:
    own = time.monotonic() + timeout_seconds
    inherited = inherited_deadline() if parent_deadline is None else parent_deadline
    return min(own, inherited) if inherited is not None else own


def _send_tree_signal(process: subprocess.Popen[str], signum: int) -> None:
    try:
        if os.name == "posix":
            os.killpg(process.pid, signum)
        elif signum == signal.SIGTERM:
            process.terminate()
        else:
            process.kill()
    except (ProcessLookupError, OSError):
        pass


def _stop_and_collect(
    process: subprocess.Popen[str], *, capture_output: bool, grace_seconds: float
) -> tuple[str, str]:
    _send_tree_signal(process, signal.SIGTERM)
    try:
        stdout, stderr = process.communicate(timeout=grace_seconds)
    except subprocess.TimeoutExpired:
        _send_tree_signal(process, signal.SIGKILL)
        try:
            stdout, stderr = process.communicate(timeout=max(1.0, grace_seconds))
        except subprocess.TimeoutExpired:
            # A descendant outside the process group may still own a pipe. Close
            # our handles and reap the direct child without waiting forever.
            for handle in (process.stdout, process.stderr):
                if handle is not None:
                    handle.close()
            process.wait(timeout=max(1.0, grace_seconds))
            return "", ""
    if not capture_output:
        return "", ""
    return stdout or "", stderr or ""


def _install_default_term_handler():
    if signal.getsignal(signal.SIGTERM) != signal.SIG_DFL:
        return None

    def interrupt(signum: int, _frame: object) -> None:
        raise ProcessInterrupted(signum)

    signal.signal(signal.SIGTERM, interrupt)
    return signal.SIG_DFL


def run_process(
    command: Sequence[str],
    *,
    cwd: Path,
    timeout_seconds: float,
    env: Mapping[str, str] | None = None,
    capture_output: bool = True,
    combine_output: bool = False,
    grace_seconds: float = 3.0,
    deadline: float | None = None,
) -> ProcessResult:
    started = time.monotonic()
    effective_deadline = deadline_after(timeout_seconds) if deadline is None else min(
        deadline, deadline_after(timeout_seconds)
    )
    remaining = effective_deadline - started
    if remaining <= 0:
        return ProcessResult(tuple(command), None, "", "", 0.0, True, effective_deadline)

    child_env = dict(os.environ if env is None else env)
    child_env[DEADLINE_ENV] = repr(effective_deadline)
    popen_arguments: dict[str, object] = {}
    if os.name == "posix":
        popen_arguments["start_new_session"] = True
    elif hasattr(subprocess, "CREATE_NEW_PROCESS_GROUP"):
        popen_arguments["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP

    try:
        process = subprocess.Popen(
            list(command),
            cwd=cwd,
            env=child_env,
            text=True,
            encoding="utf-8",
            errors="replace",
            stdout=subprocess.PIPE if capture_output else None,
            stderr=(
                subprocess.STDOUT
                if capture_output and combine_output
                else subprocess.PIPE if capture_output else None
            ),
            **popen_arguments,
        )
    except OSError as error:
        raise CommandSpawnError(command, error) from error

    previous_term = None
    try:
        previous_term = _install_default_term_handler()
        try:
            stdout, stderr = process.communicate(timeout=max(0.001, effective_deadline - time.monotonic()))
            return ProcessResult(
                tuple(command),
                process.returncode,
                (stdout or "") if capture_output else "",
                (stderr or "") if capture_output and not combine_output else "",
                round(time.monotonic() - started, 3),
                False,
                effective_deadline,
            )
        except subprocess.TimeoutExpired:
            stdout, stderr = _stop_and_collect(
                process, capture_output=capture_output, grace_seconds=grace_seconds
            )
            return ProcessResult(
                tuple(command),
                process.returncode,
                stdout,
                stderr,
                round(time.monotonic() - started, 3),
                True,
                effective_deadline,
            )
        except BaseException:
            _stop_and_collect(process, capture_output=capture_output, grace_seconds=grace_seconds)
            raise
    finally:
        if previous_term is not None:
            signal.signal(signal.SIGTERM, previous_term)
