#!/usr/bin/env python3
"""Create safe, local Unix observation scenarios.

The lab never requires elevated privileges or external network access. Every
long-running process executes a script inside its scenario directory, allowing
safe identity checks before cleanup.
"""

from __future__ import annotations

import argparse
import ctypes
import errno
import functools
import http.client
import json
import mmap
import os
import shutil
import signal
import socket
import struct
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Callable, NamedTuple

CASE_TITLES = {
    "01-command-resolution": "PATH에서 오래된 실행 파일이 먼저 선택됨",
    "02-dangling-symlink": "current 링크가 존재하지 않는 release를 가리킴",
    "03-waiting-for-input": "reader가 FIFO 입력과 EOF를 기다림",
    "04-deleted-open-file": "삭제된 로그 객체를 writer가 열린 채 유지함",
    "05-working-directory": "상대 설정 경로와 실제 작업 디렉터리가 다름",
    "06-address-family-mismatch": "IPv4 listener에 IPv6 loopback으로 연결함",
    "07-running-not-ready": "프로세스와 listener는 있으나 dependency가 준비되지 않음",
    "08-signal-not-forwarded": "wrapper가 SIGTERM을 child에 전달하지 않음",
    "09-reserved-not-resident": "큰 주소 공간을 예약했지만 일부 page만 상주함",
}

STATE_NAME = ".case.json"
PYTHON = sys.executable
START_TOKEN_TIMEOUT = 4.0
START_TOKEN_PROBE_TIMEOUT = 0.20
START_TOKEN_MAX_ATTEMPTS = 40
PROCESS_PROBE_TIMEOUT = 0.20
PROC_PIDTBSDINFO = 3
PROC_BSDINFO_SIZE = 136
SZOMB = 5
CTL_KERN = 1
KERN_PROCARGS2 = 49
MAX_PROCARGS = 1024 * 1024


class ProcBsdInfo(ctypes.Structure):
    """Darwin sys/proc_info.h struct proc_bsdinfo (MAXCOMLEN=16)."""

    _fields_ = [
        ("pbi_flags", ctypes.c_uint32),
        ("pbi_status", ctypes.c_uint32),
        ("pbi_xstatus", ctypes.c_uint32),
        ("pbi_pid", ctypes.c_uint32),
        ("pbi_ppid", ctypes.c_uint32),
        ("pbi_uid", ctypes.c_uint32),
        ("pbi_gid", ctypes.c_uint32),
        ("pbi_ruid", ctypes.c_uint32),
        ("pbi_rgid", ctypes.c_uint32),
        ("pbi_svuid", ctypes.c_uint32),
        ("pbi_svgid", ctypes.c_uint32),
        ("rfu_1", ctypes.c_uint32),
        ("pbi_comm", ctypes.c_char * 16),
        ("pbi_name", ctypes.c_char * 32),
        ("pbi_nfiles", ctypes.c_uint32),
        ("pbi_pgid", ctypes.c_uint32),
        ("pbi_pjobc", ctypes.c_uint32),
        ("e_tdev", ctypes.c_uint32),
        ("e_tpgid", ctypes.c_uint32),
        ("pbi_nice", ctypes.c_int32),
        ("pbi_start_tvsec", ctypes.c_uint64),
        ("pbi_start_tvusec", ctypes.c_uint64),
    ]


class StartTokenObservation(NamedTuple):
    token: str | None
    alive: bool
    attempts: int
    diagnostic: str


_OWNED_GROUPS: dict[Path, dict[int, subprocess.Popen[bytes]]] = {}
_OWNED_CLEANUP_SIGNALS: dict[tuple[Path, int], int] = {}
_ACTIVE_ROOTS: set[Path] = set()
_SIGNAL_CLEANUP_ACTIVE = False


class LabError(RuntimeError):
    pass


def write_text(path: Path, text: str, executable: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    if executable:
        path.chmod(0o755)


def wait_for_path(path: Path, timeout: float = 5.0) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if path.exists():
            return
        time.sleep(0.03)
    raise LabError(f"제한 시간 안에 생성되지 않았습니다: {path}")


def wait_for_exit(pid: int, timeout: float = 3.0, expected_start: str | None = None) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if not process_alive(pid):
            return True
        if expected_start is not None:
            current_start = process_start_token(pid)
            if current_start and current_start != expected_start:
                return True
        time.sleep(0.04)
    if not process_alive(pid):
        return True
    if expected_start is not None:
        current_start = process_start_token(pid)
        return bool(current_start and current_start != expected_start)
    return False


@functools.lru_cache(maxsize=1)
def load_libproc() -> ctypes.CDLL:
    library = ctypes.CDLL("/usr/lib/libproc.dylib", use_errno=True)
    library.proc_pidinfo.argtypes = [
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_uint64,
        ctypes.c_void_p,
        ctypes.c_int,
    ]
    library.proc_pidinfo.restype = ctypes.c_int
    return library


@functools.lru_cache(maxsize=1)
def load_libc() -> ctypes.CDLL:
    library = ctypes.CDLL(None, use_errno=True)
    library.sysctl.argtypes = [
        ctypes.POINTER(ctypes.c_int),
        ctypes.c_uint,
        ctypes.c_void_p,
        ctypes.POINTER(ctypes.c_size_t),
        ctypes.c_void_p,
        ctypes.c_size_t,
    ]
    library.sysctl.restype = ctypes.c_int
    return library


def darwin_bsd_info(pid: int) -> tuple[ProcBsdInfo | None, str]:
    if ctypes.sizeof(ProcBsdInfo) != PROC_BSDINFO_SIZE:
        return None, f"libproc struct-size={ctypes.sizeof(ProcBsdInfo)} expected={PROC_BSDINFO_SIZE}"
    try:
        library = load_libproc()
    except OSError as exc:
        return None, f"libproc load-error={exc}"
    info = ProcBsdInfo()
    ctypes.set_errno(0)
    received = library.proc_pidinfo(
        pid,
        PROC_PIDTBSDINFO,
        0,
        ctypes.byref(info),
        ctypes.sizeof(info),
    )
    error = ctypes.get_errno()
    if received != PROC_BSDINFO_SIZE:
        return None, f"libproc bytes={received}/{PROC_BSDINFO_SIZE} errno={error}"
    if int(info.pbi_pid) != pid:
        return None, f"libproc pid={int(info.pbi_pid)} expected={pid}"
    if int(info.pbi_start_tvsec) == 0 and int(info.pbi_start_tvusec) == 0:
        return None, "libproc start-time=0:0"
    return info, "libproc ok"


def darwin_command_line(pid: int) -> tuple[str, str]:
    """Read same-user argv through KERN_PROCARGS2 without spawning ps."""
    try:
        library = load_libc()
    except OSError as exc:
        return "", f"sysctl load-error={exc}"
    mib = (ctypes.c_int * 3)(CTL_KERN, KERN_PROCARGS2, pid)
    size = ctypes.c_size_t(0)
    ctypes.set_errno(0)
    if library.sysctl(mib, 3, None, ctypes.byref(size), None, 0) != 0:
        return "", f"sysctl size errno={ctypes.get_errno()}"
    if size.value < ctypes.sizeof(ctypes.c_int) or size.value > MAX_PROCARGS:
        return "", f"sysctl size={size.value} outside-safe-range"
    buffer = ctypes.create_string_buffer(size.value)
    ctypes.set_errno(0)
    if library.sysctl(mib, 3, buffer, ctypes.byref(size), None, 0) != 0:
        return "", f"sysctl argv errno={ctypes.get_errno()}"
    raw = buffer.raw[: size.value]
    if len(raw) < ctypes.sizeof(ctypes.c_int):
        return "", f"sysctl argv bytes={len(raw)}"
    argc = struct.unpack_from("=i", raw)[0]
    if argc <= 0 or argc > 4096:
        return "", f"sysctl argc={argc}"
    position = ctypes.sizeof(ctypes.c_int)
    executable_end = raw.find(b"\0", position)
    if executable_end < 0:
        return "", "sysctl executable terminator missing"
    executable = raw[position:executable_end]
    position = executable_end
    while position < len(raw) and raw[position] == 0:
        position += 1
    arguments: list[bytes] = []
    for _ in range(argc):
        end = raw.find(b"\0", position)
        if end < 0:
            break
        arguments.append(raw[position:end])
        position = end + 1
    if len(arguments) != argc:
        return "", f"sysctl argv-count={len(arguments)} expected={argc}"
    decoded = [item.decode("utf-8", "replace") for item in [executable, *arguments]]
    return " ".join(decoded), "sysctl ok"


def process_state(pid: int, timeout: float = PROCESS_PROBE_TIMEOUT) -> str:
    stat_path = Path(f"/proc/{pid}/stat")
    if stat_path.exists():
        try:
            raw = stat_path.read_text(encoding="utf-8", errors="replace")
            closing = raw.rfind(")")
            if closing >= 0:
                fields = raw[closing + 2 :].split()
                if fields:
                    return fields[0]
        except OSError:
            pass
    if sys.platform == "darwin":
        info, _ = darwin_bsd_info(pid)
        if info is not None:
            return "Z" if int(info.pbi_status) == SZOMB else "R"
        return ""
    try:
        result = subprocess.run(
            ["ps", "-p", str(pid), "-o", "state="],
            check=False,
            capture_output=True,
            text=True,
            timeout=max(0.01, timeout),
        )
        return result.stdout.strip()[:1]
    except (OSError, subprocess.SubprocessError):
        return ""


def reap_if_child(pid: int) -> None:
    try:
        os.waitpid(pid, os.WNOHANG)
    except (ChildProcessError, ProcessLookupError):
        pass


def process_alive(pid: int, probe_timeout: float = PROCESS_PROBE_TIMEOUT) -> bool:
    if pid <= 0:
        return False
    try:
        waited, _ = os.waitpid(pid, os.WNOHANG)
        if waited == pid:
            return False
    except (ChildProcessError, ProcessLookupError):
        pass
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        reap_if_child(pid)
        return False
    except PermissionError:
        return True
    if process_state(pid, probe_timeout) == "Z":
        reap_if_child(pid)
        return False
    return True


def pid_reachable(pid: int) -> bool:
    """Fast liveness hint for deadline loops; never spawns another probe."""
    if pid <= 0:
        return False
    try:
        waited, _ = os.waitpid(pid, os.WNOHANG)
        if waited == pid:
            return False
    except (ChildProcessError, ProcessLookupError):
        pass
    stat_path = Path(f"/proc/{pid}/stat")
    if stat_path.exists():
        try:
            raw = stat_path.read_text(encoding="utf-8", errors="replace")
            closing = raw.rfind(")")
            fields = raw[closing + 2 :].split() if closing >= 0 else []
            if fields and fields[0] == "Z":
                reap_if_child(pid)
                return False
        except OSError:
            pass
    elif sys.platform == "darwin":
        info, _ = darwin_bsd_info(pid)
        if info is not None and int(info.pbi_status) == SZOMB:
            reap_if_child(pid)
            return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def command_line(pid: int, timeout: float = PROCESS_PROBE_TIMEOUT) -> str:
    proc_cmdline = Path(f"/proc/{pid}/cmdline")
    if proc_cmdline.exists():
        try:
            return proc_cmdline.read_bytes().replace(b"\0", b" ").decode("utf-8", "replace")
        except OSError:
            pass
    if sys.platform == "darwin":
        command, _ = darwin_command_line(pid)
        return command
    try:
        result = subprocess.run(
            ["ps", "-p", str(pid), "-o", "command="],
            check=False,
            capture_output=True,
            text=True,
            timeout=max(0.01, timeout),
        )
        return result.stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return ""


def fallback_ps_start_token(pid: int, timeout: float) -> tuple[str, str]:
    environment = os.environ.copy()
    environment["LC_ALL"] = "C"
    command = ["ps", "-p", str(pid), "-o", "lstart="]
    try:
        result = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
            timeout=max(0.01, timeout),
            env=environment,
        )
    except subprocess.TimeoutExpired:
        return "", f"fallback-ps timeout={max(0.01, timeout):.3f}s"
    except OSError as exc:
        return "", f"fallback-ps os-error={exc}"
    value = " ".join(result.stdout.split())
    stderr = " ".join(result.stderr.split()) or "<empty>"
    if result.returncode != 0:
        return "", f"fallback-ps exit={result.returncode} stderr={stderr}"
    if not value:
        return "", f"fallback-ps empty-output stderr={stderr}"
    return f"{sys.platform}-lstart:{value}", "fallback-ps ok"


def probe_process_start_token(
    pid: int,
    *,
    fallback_timeout: float = START_TOKEN_PROBE_TIMEOUT,
) -> tuple[str, str]:
    """Return a stable birth token plus bounded-probe diagnostics."""
    stat_path = Path(f"/proc/{pid}/stat")
    if stat_path.exists():
        try:
            raw = stat_path.read_text(encoding="utf-8", errors="replace")
            closing = raw.rfind(")")
            fields = raw[closing + 2 :].split() if closing >= 0 else []
            if len(fields) > 19:
                return f"linux-start-ticks:{fields[19]}", "procfs ok"
            return "", f"procfs fields={len(fields)}"
        except OSError as exc:
            return "", f"procfs os-error={exc}"
    if sys.platform == "darwin":
        info, diagnostic = darwin_bsd_info(pid)
        if info is None:
            return "", diagnostic
        token = f"darwin-start-time:{int(info.pbi_start_tvsec)}:{int(info.pbi_start_tvusec)}"
        return token, diagnostic
    return fallback_ps_start_token(pid, fallback_timeout)


def process_start_token(pid: int, fallback_timeout: float = START_TOKEN_PROBE_TIMEOUT) -> str:
    token, _ = probe_process_start_token(pid, fallback_timeout=fallback_timeout)
    return token


def wait_for_start_token(
    pid: int,
    timeout: float = START_TOKEN_TIMEOUT,
    *,
    alive_probe: Callable[[], bool] | None = None,
    probe_timeout: float = START_TOKEN_PROBE_TIMEOUT,
    max_attempts: int = START_TOKEN_MAX_ATTEMPTS,
    retry_delay: float = 0.03,
) -> StartTokenObservation:
    """Observe a birth token without treating an already-gone PID as alive.

    Startup callers decide whether disappearance is expected for the process
    role.  Direct children must pass a Popen-based probe so this observation
    never reaps the child behind Popen's back.
    """
    is_alive = alive_probe or (lambda: pid_reachable(pid))
    deadline = time.monotonic() + timeout
    attempts = 0
    diagnostics: list[str] = []
    while attempts < max_attempts:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            break
        if not is_alive():
            return StartTokenObservation(None, False, attempts, "; ".join(diagnostics[-4:]))
        attempts += 1
        token, diagnostic = probe_process_start_token(
            pid,
            fallback_timeout=min(probe_timeout, remaining),
        )
        if token:
            if not is_alive():
                return StartTokenObservation(None, False, attempts, diagnostic)
            return StartTokenObservation(token, True, attempts, diagnostic)
        diagnostics.append(f"attempt={attempts} {diagnostic}")
        if not is_alive():
            return StartTokenObservation(None, False, attempts, "; ".join(diagnostics[-4:]))
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            break
        time.sleep(min(retry_delay, remaining))
    alive = is_alive()
    diagnostic = "; ".join(diagnostics[-4:]) or "no probe completed"
    return StartTokenObservation(None, alive, attempts, diagnostic)


def command_belongs_to_case(command: str, root: Path) -> bool:
    canonical = str(root.resolve())
    candidates = {canonical}
    # macOS exposes /tmp and /var as symlinks into /private while `ps` keeps
    # the spelling used at exec time.  Treat only that exact platform alias
    # as the same case root.
    if canonical.startswith(("/private/tmp/", "/private/var/")):
        candidates.add(canonical.removeprefix("/private"))
    return any(candidate in command for candidate in candidates)


def classify_case_process(
    pid: int,
    root: Path,
    expected_start: str | None = None,
    *,
    retries: int = 40,
    delay: float = 0.05,
    timeout: float = 2.0,
) -> tuple[str, str]:
    """Classify a recorded PID without confusing disappearance or reuse."""
    deadline = time.monotonic() + timeout
    last_detail = ""
    for attempt in range(retries):
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            break
        probe_budget = min(PROCESS_PROBE_TIMEOUT, remaining)
        if not process_alive(pid, probe_budget):
            return "gone", last_detail
        current_start = process_start_token(pid, probe_budget)
        if expected_start is not None:
            if not current_start:
                last_detail = "<start token unavailable>"
                remaining = deadline - time.monotonic()
                if attempt + 1 < retries and remaining > 0:
                    time.sleep(min(delay, remaining))
                continue
            if current_start != expected_start:
                return "reused", last_detail
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            break
        command = command_line(pid, min(PROCESS_PROBE_TIMEOUT, remaining))
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            last_detail = command or "<command probe deadline>"
            break
        current_start = process_start_token(pid, min(PROCESS_PROBE_TIMEOUT, remaining))
        if expected_start is not None:
            if not current_start:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    last_detail = "<start token unavailable after command probe>"
                    break
                if not process_alive(pid, min(PROCESS_PROBE_TIMEOUT, remaining)):
                    return "gone", command
                last_detail = "<start token unavailable after command probe>"
                continue
            if current_start != expected_start:
                return "reused", command
        if command:
            identity = "owned" if command_belongs_to_case(command, root) else "foreign"
            return identity, command
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            last_detail = "<command probe deadline>"
            break
        if not process_alive(pid, min(PROCESS_PROBE_TIMEOUT, remaining)):
            return "gone", command
        last_detail = "<command unavailable>"
        if attempt + 1 < retries:
            remaining = deadline - time.monotonic()
            if remaining > 0:
                time.sleep(min(delay, remaining))
    return "unknown", last_detail


def terminate_process(pid: int, root: Path, expected_start: str | None = None) -> None:
    if not expected_start:
        raise LabError(f"PID {pid}의 기록된 시작 identity가 없어 종료하지 않았습니다.")
    identity, command = classify_case_process(pid, root, expected_start)
    if identity in {"gone", "reused"}:
        return
    if identity != "owned":
        detail = command or "<unavailable after retry>"
        raise LabError(f"PID {pid}의 identity를 안전하게 확인하지 못해 종료하지 않았습니다: {detail}")
    current_start, token_detail = probe_process_start_token(pid)
    if not current_start:
        raise LabError(
            f"PID {pid}의 시작 identity를 신호 직전에 확인하지 못해 종료하지 않았습니다: "
            f"{token_detail}"
        )
    if current_start != expected_start:
        return
    try:
        os.kill(pid, signal.SIGTERM)
    except ProcessLookupError:
        return
    if wait_for_exit(pid, 1.5, expected_start):
        return
    identity, command = classify_case_process(pid, root, expected_start)
    if identity in {"gone", "reused"}:
        return
    if identity != "owned":
        detail = command or "<unavailable after retry>"
        raise LabError(f"PID {pid}의 identity를 재확인하지 못해 강제 종료하지 않았습니다: {detail}")
    try:
        os.kill(pid, signal.SIGKILL)
    except ProcessLookupError:
        return
    if not wait_for_exit(pid, 1.5, expected_start):
        raise LabError(f"PID {pid}를 종료하지 못했습니다.")


def register_owned_group(
    root: Path,
    proc: subprocess.Popen[bytes],
    cleanup_signal: int = signal.SIGTERM,
) -> None:
    canonical = root.resolve()
    _OWNED_GROUPS.setdefault(canonical, {})[proc.pid] = proc
    _OWNED_CLEANUP_SIGNALS[(canonical, proc.pid)] = cleanup_signal


def unregister_owned_group(root: Path, pid: int) -> None:
    canonical = root.resolve()
    groups = _OWNED_GROUPS.get(canonical)
    if groups is None:
        return
    groups.pop(pid, None)
    _OWNED_CLEANUP_SIGNALS.pop((canonical, pid), None)
    if not groups:
        _OWNED_GROUPS.pop(canonical, None)


def process_group_alive(pgid: int) -> bool:
    try:
        os.killpg(pgid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def stop_owned_process_group(root: Path, proc: subprocess.Popen[bytes]) -> None:
    """Stop a new-session group while its Popen leader prevents PID reuse."""
    pgid = proc.pid
    errors: list[str] = []
    permission_details: list[str] = []
    cleanup_signal = _OWNED_CLEANUP_SIGNALS.get((root.resolve(), pgid), signal.SIGTERM)
    try:
        if cleanup_signal != signal.SIGTERM and process_group_alive(pgid):
            try:
                proc.send_signal(cleanup_signal)
            except ProcessLookupError:
                pass
            except (OSError, subprocess.SubprocessError) as exc:
                errors.append(f"소유 Popen {pgid} cleanup signal 실패: {exc}")
            deadline = time.monotonic() + 1.5
            while process_group_alive(pgid) and time.monotonic() < deadline:
                proc.poll()
                time.sleep(0.03)
        if process_group_alive(pgid):
            try:
                os.killpg(pgid, signal.SIGTERM)
            except ProcessLookupError:
                pass
            except PermissionError as exc:
                permission_details.append(f"TERM 권한 오류: {exc}")
                try:
                    proc.terminate()
                except (OSError, subprocess.SubprocessError) as fallback_exc:
                    errors.append(f"소유 Popen {pgid} TERM 실패: {fallback_exc}")
            deadline = time.monotonic() + 1.5
            while process_group_alive(pgid) and time.monotonic() < deadline:
                proc.poll()
                time.sleep(0.03)
            if process_group_alive(pgid):
                try:
                    os.killpg(pgid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                except PermissionError as exc:
                    permission_details.append(f"KILL 권한 오류: {exc}")
                    try:
                        proc.kill()
                    except (OSError, subprocess.SubprocessError) as fallback_exc:
                        errors.append(f"소유 Popen {pgid} KILL 실패: {fallback_exc}")
                deadline = time.monotonic() + 1.5
                while process_group_alive(pgid) and time.monotonic() < deadline:
                    proc.poll()
                    time.sleep(0.03)
    finally:
        try:
            proc.wait(timeout=0.5)
        except subprocess.TimeoutExpired:
            try:
                proc.kill()
                proc.wait(timeout=0.5)
            except (OSError, subprocess.SubprocessError) as exc:
                errors.append(f"소유 Popen {pgid} 회수 실패: {exc}")
    try:
        group_remains = process_group_alive(pgid)
    except OSError as exc:
        errors.append(f"소유 process group {pgid} 잔여 확인 실패: {exc}")
        group_remains = True
    if group_remains:
        errors.extend(f"소유 process group {pgid} {detail}" for detail in permission_details)
        errors.append(f"소유 process group {pgid}가 정리 뒤에도 남았습니다.")
    else:
        unregister_owned_group(root, pgid)
    if errors:
        raise LabError("; ".join(errors))


def cleanup_active_root(root: Path, *, remove: bool = True) -> list[str]:
    canonical = root.resolve()
    errors: list[str] = []
    for proc in list(_OWNED_GROUPS.get(canonical, {}).values()):
        try:
            stop_owned_process_group(canonical, proc)
        except (LabError, OSError, subprocess.SubprocessError) as exc:
            errors.append(str(exc))
    if not errors and remove and canonical.exists():
        try:
            shutil.rmtree(canonical)
        except OSError as exc:
            errors.append(f"active root 제거 실패: {canonical}: {exc}")
    if not errors:
        _ACTIVE_ROOTS.discard(canonical)
    return errors


def handle_lab_signal(signum: int, _frame: Any) -> None:
    global _SIGNAL_CLEANUP_ACTIVE
    if _SIGNAL_CLEANUP_ACTIVE:
        raise SystemExit(128 + signum)
    _SIGNAL_CLEANUP_ACTIVE = True
    for handled in (signal.SIGHUP, signal.SIGINT, signal.SIGTERM):
        signal.signal(handled, signal.SIG_IGN)
    errors: list[str] = []
    for root in list(_ACTIVE_ROOTS | set(_OWNED_GROUPS)):
        errors.extend(cleanup_active_root(root))
    for error in errors:
        print(f"SIGNAL CLEANUP ERROR: {error}", file=sys.stderr, flush=True)
    raise SystemExit(128 + signum)


def install_lab_signal_handlers() -> None:
    for handled in (signal.SIGHUP, signal.SIGINT, signal.SIGTERM):
        signal.signal(handled, handle_lab_signal)


def log_tail(path: Path, limit: int = 2048) -> str:
    try:
        data = path.read_bytes()[-limit:]
    except OSError:
        return "<unavailable>"
    text = data.decode("utf-8", "replace").strip()
    return text or "<empty>"


def start_script(
    root: Path,
    script: Path,
    *args: str,
    role: str,
    token_timeout: float = START_TOKEN_TIMEOUT,
) -> dict[str, Any]:
    stdout_path = root / f"{role}.stdout.log"
    stderr_path = root / f"{role}.stderr.log"
    out = stdout_path.open("ab", buffering=0)
    err = stderr_path.open("ab", buffering=0)
    try:
        proc = subprocess.Popen(
            [PYTHON, str(script), *args],
            cwd=root,
            stdin=subprocess.DEVNULL,
            stdout=out,
            stderr=err,
            start_new_session=True,
            close_fds=True,
        )
        cleanup_signal = signal.SIGUSR1 if role == "wrapper" else signal.SIGTERM
        register_owned_group(root, proc, cleanup_signal)
    finally:
        out.close()
        err.close()
    observation = wait_for_start_token(
        proc.pid,
        timeout=token_timeout,
        alive_probe=lambda: proc.poll() is None,
    )
    if observation.token is None:
        exit_code = proc.poll()
        stderr = log_tail(stderr_path)
        if exit_code is not None:
            proc.wait()
            unregister_owned_group(root, proc.pid)
            raise LabError(
                f"role={role} PID {proc.pid}가 시작 identity 기록 전에 종료했습니다: "
                f"exit={exit_code} attempts={observation.attempts} "
                f"probe={observation.diagnostic} stderr={stderr}"
            )
        stop_owned_process_group(root, proc)
        raise LabError(
            f"role={role} PID {proc.pid}가 실행 중이지만 시작 identity를 기록하지 "
            f"못해 소유 Popen group으로 정리했습니다: attempts={observation.attempts} "
            f"probe={observation.diagnostic} stderr={stderr}"
        )
    return {
        "role": role,
        "pid": proc.pid,
        "script": str(script.resolve()),
        "start_token": observation.token,
    }


def save_state(root: Path, state: dict[str, Any]) -> None:
    (root / STATE_NAME).write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def load_state(root: Path) -> dict[str, Any]:
    path = root / STATE_NAME
    try:
        state = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise LabError(f"사례 상태 파일이 없습니다: {path}") from None
    except json.JSONDecodeError as exc:
        raise LabError(f"사례 상태 JSON이 손상되었습니다: {exc}") from None
    if state.get("root") != str(root.resolve()):
        raise LabError("사례 디렉터리를 생성 뒤 이동했습니다. 안전한 정리를 위해 원래 위치에서 사용하십시오.")
    if state.get("schema_version") != 2:
        raise LabError("지원하지 않는 사례 상태 schema입니다.")
    if state.get("case_id") not in CASE_TITLES:
        raise LabError("알 수 없는 사례 상태입니다.")
    processes = state.get("processes")
    if not isinstance(processes, list):
        raise LabError("사례 process 목록이 올바르지 않습니다.")
    for item in processes:
        if not isinstance(item, dict):
            raise LabError("사례 process record가 올바르지 않습니다.")
        if not isinstance(item.get("pid"), int) or int(item["pid"]) <= 0:
            raise LabError("사례 process PID가 올바르지 않습니다.")
        if not isinstance(item.get("role"), str) or not item["role"]:
            raise LabError("사례 process role이 없습니다.")
        if not isinstance(item.get("start_token"), str) or not item["start_token"]:
            raise LabError(f"사례 process 시작 identity가 없습니다: role={item.get('role')}")
    return state


def new_state(case_id: str, root: Path) -> dict[str, Any]:
    return {
        "schema_version": 2,
        "case_id": case_id,
        "root": str(root.resolve()),
        "created_at": time.time(),
        "processes": [],
        "data": {},
    }


def ensure_new_destination(root: Path) -> None:
    if root.exists():
        raise LabError(f"대상 경로가 이미 존재합니다: {root}")
    root.mkdir(parents=True)


def create_command_resolution(root: Path, state: dict[str, Any]) -> None:
    stale = root / "stale-bin" / "unix-guide-tool"
    trusted = root / "trusted-bin" / "unix-guide-tool"
    write_text(stale, "#!/bin/sh\nprintf '%s\\n' 'stale tool selected' >&2\nexit 42\n", True)
    write_text(trusted, "#!/bin/sh\nprintf '%s\\n' 'ready'\nexit 0\n", True)
    state["data"] = {
        "stale_bin": str(stale.parent),
        "trusted_bin": str(trusted.parent),
        "tool": "unix-guide-tool",
    }
    write_text(
        root / "scenario.env",
        f"PATH={stale.parent}:{trusted.parent}:/usr/bin:/bin\n",
    )


def create_dangling_symlink(root: Path, state: dict[str, Any]) -> None:
    release = root / "releases" / "v1"
    release.mkdir(parents=True)
    write_text(release / "config.ini", "version=v1\nstatus=ready\n")
    os.symlink("releases/missing", root / "current")
    state["data"] = {"link": "current", "valid_target": "releases/v1"}


def create_waiting_for_input(root: Path, state: dict[str, Any]) -> None:
    fifo = root / "input.fifo"
    os.mkfifo(fifo, 0o600)
    holder_script = root / "fifo_holder.py"
    reader_script = root / "fifo_reader.py"
    write_text(
        holder_script,
        """#!/usr/bin/env python3
import os, pathlib, sys, time
fifo = sys.argv[1]
ready = pathlib.Path(sys.argv[2])
fd = os.open(fifo, os.O_RDWR)
ready.write_text('ready\\n', encoding='utf-8')
try:
    while True:
        time.sleep(1)
finally:
    os.close(fd)
""",
        True,
    )
    write_text(
        reader_script,
        """#!/usr/bin/env python3
import pathlib, sys
fifo = sys.argv[1]
ready = pathlib.Path(sys.argv[2])
out = pathlib.Path(sys.argv[3])
with open(fifo, 'r', encoding='utf-8') as stream:
    ready.write_text('ready\\n', encoding='utf-8')
    line = stream.readline()
out.write_text('received=' + line, encoding='utf-8')
""",
        True,
    )
    holder_ready = root / "holder.ready"
    reader_ready = root / "reader.ready"
    output = root / "reader-output.txt"
    holder = start_script(root, holder_script, str(fifo), str(holder_ready), role="fifo-holder")
    state["processes"].append(holder)
    wait_for_path(holder_ready)
    reader = start_script(root, reader_script, str(fifo), str(reader_ready), str(output), role="fifo-reader")
    state["processes"].append(reader)
    wait_for_path(reader_ready)
    state["data"] = {
        "fifo": str(fifo),
        "reader_pid": reader["pid"],
        "holder_pid": holder["pid"],
        "output": str(output),
    }


def create_deleted_open_file(root: Path, state: dict[str, Any]) -> None:
    script = root / "deleted_writer.py"
    log_path = root / "live.log"
    ready = root / "writer.ready"
    write_text(
        script,
        """#!/usr/bin/env python3
import os, pathlib, sys, time
path = pathlib.Path(sys.argv[1])
ready = pathlib.Path(sys.argv[2])
with path.open('w', encoding='utf-8', buffering=1) as stream:
    stream.write('writer-start\\n')
    stream.flush()
    os.unlink(path)
    ready.write_text('ready\\n', encoding='utf-8')
    index = 0
    while True:
        stream.write(f'tick={index}\\n')
        stream.flush()
        index += 1
        time.sleep(0.2)
""",
        True,
    )
    writer = start_script(root, script, str(log_path), str(ready), role="deleted-writer")
    state["processes"].append(writer)
    wait_for_path(ready)
    state["data"] = {"writer_pid": writer["pid"], "deleted_path": str(log_path)}


def create_working_directory(root: Path, state: dict[str, Any]) -> None:
    app = root / "app"
    wrong = root / "wrong-run-dir"
    (app / "config").mkdir(parents=True)
    wrong.mkdir()
    write_text(app / "config" / "service.json", '{"service":"ready"}\n')
    script = app / "service.py"
    write_text(
        script,
        """#!/usr/bin/env python3
import json, pathlib, sys
path = pathlib.Path('config/service.json')
try:
    data = json.loads(path.read_text(encoding='utf-8'))
except Exception as exc:
    print(f'config_error cwd={pathlib.Path.cwd()} path={path}: {exc}', file=sys.stderr)
    raise SystemExit(2)
print('service=' + str(data['service']))
""",
        True,
    )
    state["data"] = {"app_dir": str(app), "wrong_dir": str(wrong), "script": str(script)}


def create_ipv4_listener(root: Path, state: dict[str, Any]) -> None:
    script = root / "ipv4_server.py"
    port_file = root / "port.txt"
    write_text(
        script,
        """#!/usr/bin/env python3
import pathlib, socket, sys
port_file = pathlib.Path(sys.argv[1])
with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(('127.0.0.1', 0))
    server.listen()
    port_file.write_text(str(server.getsockname()[1]) + '\\n', encoding='utf-8')
    while True:
        conn, _ = server.accept()
        with conn:
            conn.sendall(b'ready\\n')
""",
        True,
    )
    server = start_script(root, script, str(port_file), role="ipv4-server")
    state["processes"].append(server)
    wait_for_path(port_file)
    port = int(port_file.read_text(encoding="utf-8").strip())
    state["data"] = {"server_pid": server["pid"], "port": port, "bind": "127.0.0.1"}


def create_readiness_server(root: Path, state: dict[str, Any]) -> None:
    script = root / "readiness_server.py"
    port_file = root / "port.txt"
    dependency = root / "dependency.ready"
    write_text(
        script,
        """#!/usr/bin/env python3
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import pathlib, sys
port_file = pathlib.Path(sys.argv[1])
dependency = pathlib.Path(sys.argv[2])
class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/health':
            ready = dependency.exists()
            body = b'ready\\n' if ready else b'dependency-not-ready\\n'
            self.send_response(200 if ready else 503)
        else:
            body = b'running\\n'
            self.send_response(200)
        self.send_header('Content-Type', 'text/plain')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)
    def log_message(self, fmt, *args):
        print(fmt % args, file=sys.stderr, flush=True)
server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
port_file.write_text(str(server.server_address[1]) + '\\n', encoding='utf-8')
server.serve_forever()
""",
        True,
    )
    server = start_script(root, script, str(port_file), str(dependency), role="readiness-server")
    state["processes"].append(server)
    wait_for_path(port_file)
    port = int(port_file.read_text(encoding="utf-8").strip())
    state["data"] = {
        "server_pid": server["pid"],
        "port": port,
        "dependency": str(dependency),
    }


def create_signal_wrapper(root: Path, state: dict[str, Any]) -> None:
    worker_script = root / "worker.py"
    wrapper_script = root / "wrapper.py"
    exec_wrapper_script = root / "exec_wrapper.py"
    child_file = root / "worker.pid"
    wrapper_ready = root / "wrapper.ready"
    events = root / "wrapper-events.log"
    write_text(
        worker_script,
        """#!/usr/bin/env python3
import pathlib, signal, sys, time
ready = pathlib.Path(sys.argv[1])
term_exit = int(sys.argv[2]) if len(sys.argv) > 2 else 0
ready.write_text('ready\\n', encoding='utf-8')
def stop(signum, frame):
    raise SystemExit(term_exit)
signal.signal(signal.SIGTERM, stop)
while True:
    time.sleep(1)
""",
        True,
    )
    write_text(
        exec_wrapper_script,
        """#!/usr/bin/env python3
import os, sys
os.execv(sys.executable, [sys.executable, *sys.argv[1:]])
""",
        True,
    )
    write_text(
        wrapper_script,
        """#!/usr/bin/env python3
import pathlib, signal, subprocess, sys, time
worker_script = sys.argv[1]
child_file = pathlib.Path(sys.argv[2])
wrapper_ready = pathlib.Path(sys.argv[3])
events = pathlib.Path(sys.argv[4])
worker_ready = pathlib.Path(sys.argv[5])
child = None
def cleanup(signum, frame):
    if child is not None and child.poll() is None:
        child.terminate()
        try:
            child.wait(timeout=1)
        except subprocess.TimeoutExpired:
            child.kill()
            child.wait(timeout=1)
    raise SystemExit(0)
signal.signal(signal.SIGUSR1, cleanup)
child = subprocess.Popen([sys.executable, worker_script, str(worker_ready)], close_fds=True)
child_file.write_text(str(child.pid) + '\\n', encoding='utf-8')
wrapper_ready.write_text('ready\\n', encoding='utf-8')
def term(signum, frame):
    with events.open('a', encoding='utf-8') as stream:
        stream.write('wrapper received SIGTERM but did not forward it\\n')
    raise SystemExit(0)
signal.signal(signal.SIGTERM, term)
while True:
    code = child.poll()
    if code is not None:
        raise SystemExit(code)
    time.sleep(0.1)
""",
        True,
    )
    worker_ready = root / "worker.ready"
    wrapper = start_script(
        root,
        wrapper_script,
        str(worker_script),
        str(child_file),
        str(wrapper_ready),
        str(events),
        str(worker_ready),
        role="wrapper",
    )
    state["processes"].append(wrapper)
    wait_for_path(wrapper_ready)
    wait_for_path(child_file)
    wait_for_path(worker_ready)
    child_pid = int(child_file.read_text(encoding="utf-8").strip())
    worker = {
        "role": "worker",
        "pid": child_pid,
        "script": str(worker_script.resolve()),
    }
    worker_observation = wait_for_start_token(child_pid)
    if worker_observation.token is None:
        stderr = log_tail(root / "wrapper.stderr.log")
        state_name = "실행 중" if worker_observation.alive else "이미 종료"
        raise LabError(
            f"role=worker PID {child_pid}가 {state_name} 상태에서 시작 identity를 "
            f"기록하지 못했습니다: attempts={worker_observation.attempts} "
            f"probe={worker_observation.diagnostic} stderr={stderr}"
        )
    worker["start_token"] = worker_observation.token
    state["processes"].append(worker)
    state["data"] = {
        "wrapper_pid": wrapper["pid"],
        "worker_pid": child_pid,
        "worker_script": str(worker_script),
        "exec_wrapper_script": str(exec_wrapper_script),
        "events": str(events),
    }


def create_memory_reservation(root: Path, state: dict[str, Any]) -> None:
    script = root / "memory_reserver.py"
    ready = root / "memory.ready"
    size = 128 * 1024 * 1024
    write_text(
        script,
        """#!/usr/bin/env python3
import mmap, pathlib, sys, time
size = int(sys.argv[1])
ready = pathlib.Path(sys.argv[2])
region = mmap.mmap(-1, size)
region[0] = 1
ready.write_text(str(size) + '\\n', encoding='utf-8')
while True:
    time.sleep(1)
""",
        True,
    )
    proc = start_script(root, script, str(size), str(ready), role="memory-reserver")
    state["processes"].append(proc)
    wait_for_path(ready)
    state["data"] = {"memory_pid": proc["pid"], "reserved_bytes": size}


CREATE_FUNCTIONS: dict[str, Callable[[Path, dict[str, Any]], None]] = {
    "01-command-resolution": create_command_resolution,
    "02-dangling-symlink": create_dangling_symlink,
    "03-waiting-for-input": create_waiting_for_input,
    "04-deleted-open-file": create_deleted_open_file,
    "05-working-directory": create_working_directory,
    "06-address-family-mismatch": create_ipv4_listener,
    "07-running-not-ready": create_readiness_server,
    "08-signal-not-forwarded": create_signal_wrapper,
    "09-reserved-not-resident": create_memory_reservation,
}


def create_case(case_id: str, root: Path, *, keep_active: bool = False) -> None:
    if case_id not in CASE_TITLES:
        raise LabError(f"알 수 없는 사례: {case_id}")
    ensure_new_destination(root)
    root = root.resolve()
    _ACTIVE_ROOTS.add(root)
    state = new_state(case_id, root)
    try:
        CREATE_FUNCTIONS[case_id](root, state)
        save_state(root, state)
        write_text(
            root / "SCENARIO.txt",
            f"case={case_id}\ntitle={CASE_TITLES[case_id]}\n"
            f"symptom=python3 {Path(__file__).resolve()} symptom {root.resolve()}\n",
        )
        if not keep_active:
            _ACTIVE_ROOTS.discard(root)
    except Exception as creation_error:
        cleanup_errors = cleanup_active_root(root)
        if cleanup_errors:
            try:
                save_state(root, state)
                write_text(root / "CLEANUP-ERROR.txt", "\n".join(cleanup_errors) + "\n")
            except OSError:
                pass
            raise LabError(
                f"사례 생성 실패 뒤 소유 process를 모두 정리하지 못했습니다: "
                f"creation={creation_error}; cleanup={' | '.join(cleanup_errors)}"
            ) from creation_error
        raise


def env_for_command_case(state: dict[str, Any], trusted_first: bool = False) -> dict[str, str]:
    data = state["data"]
    bins = [data["trusted_bin"], data["stale_bin"]] if trusted_first else [data["stale_bin"], data["trusted_bin"]]
    env = os.environ.copy()
    env["PATH"] = os.pathsep.join([*bins, "/usr/bin", "/bin"])
    return env


def http_health(port: int) -> tuple[int, str]:
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=2)
    try:
        conn.request("GET", "/health")
        response = conn.getresponse()
        body = response.read().decode("utf-8", "replace").strip()
        return response.status, body
    finally:
        conn.close()


def ipv4_connect(port: int) -> bytes:
    with socket.create_connection(("127.0.0.1", port), timeout=2) as sock:
        return sock.recv(64)


def ipv6_connect(port: int) -> None:
    with socket.socket(socket.AF_INET6, socket.SOCK_STREAM) as sock:
        sock.settimeout(1)
        sock.connect(("::1", port))


def memory_stats(pid: int) -> tuple[int, int]:
    status_path = Path(f"/proc/{pid}/status")
    if status_path.exists():
        try:
            values: dict[str, int] = {}
            for line in status_path.read_text(encoding="utf-8", errors="replace").splitlines():
                key, separator, remainder = line.partition(":")
                if separator and key in {"VmSize", "VmRSS"}:
                    values[key] = int(remainder.split()[0])
            if set(values) == {"VmSize", "VmRSS"}:
                return values["VmSize"], values["VmRSS"]
        except (OSError, ValueError, IndexError):
            pass
    result = subprocess.run(
        ["ps", "-p", str(pid), "-o", "vsz=,rss="],
        check=False,
        capture_output=True,
        text=True,
        timeout=3,
    )
    if result.returncode != 0 or not result.stdout.strip():
        raise LabError(f"PID {pid}의 VSZ/RSS를 읽지 못했습니다: {result.stderr.strip()}")
    fields = result.stdout.split()
    if len(fields) < 2:
        raise LabError(f"예상하지 못한 ps 출력: {result.stdout!r}")
    return int(fields[0]), int(fields[1])


def symptom(root: Path) -> None:
    state = load_state(root)
    case_id = state["case_id"]
    data = state["data"]
    print(f"case={case_id}")
    if case_id == "01-command-resolution":
        result = subprocess.run(
            [data["tool"]],
            env=env_for_command_case(state),
            capture_output=True,
            text=True,
            check=False,
        )
        print(f"stdout={result.stdout.strip()!r}")
        print(f"stderr={result.stderr.strip()!r}")
        print(f"exit_status={result.returncode}")
    elif case_id == "02-dangling-symlink":
        target = root / "current" / "config.ini"
        try:
            print(target.read_text(encoding="utf-8"))
            print("exit_status=0")
        except OSError as exc:
            print(f"stderr={exc.__class__.__name__}: {exc}")
            print("exit_status=1")
    elif case_id == "03-waiting-for-input":
        reader = int(data["reader_pid"])
        output = Path(data["output"])
        print(f"reader_pid={reader}")
        print(f"reader_alive={process_alive(reader)}")
        print(f"output_exists={output.exists()}")
        print("elapsed_without_output=true")
    elif case_id == "04-deleted-open-file":
        pid = int(data["writer_pid"])
        path = Path(data["deleted_path"])
        print(f"writer_pid={pid}")
        print(f"writer_alive={process_alive(pid)}")
        print(f"path_exists={path.exists()}")
    elif case_id == "05-working-directory":
        result = subprocess.run(
            [PYTHON, data["script"]],
            cwd=data["wrong_dir"],
            capture_output=True,
            text=True,
            check=False,
        )
        print(f"cwd={data['wrong_dir']}")
        print(f"stdout={result.stdout.strip()!r}")
        print(f"stderr={result.stderr.strip()!r}")
        print(f"exit_status={result.returncode}")
    elif case_id == "06-address-family-mismatch":
        try:
            ipv6_connect(int(data["port"]))
        except OSError as exc:
            print(f"target=[::1]:{data['port']}")
            print(f"connect_error={exc.__class__.__name__}: {exc}")
            print("exit_status=1")
        else:
            print("unexpected_ipv6_success=true")
            print("exit_status=0")
    elif case_id == "07-running-not-ready":
        status_code, body = http_health(int(data["port"]))
        print(f"service_pid={data['server_pid']}")
        print(f"process_alive={process_alive(int(data['server_pid']))}")
        print(f"health_status={status_code}")
        print(f"health_body={body!r}")
    elif case_id == "08-signal-not-forwarded":
        wrapper = int(data["wrapper_pid"])
        worker = int(data["worker_pid"])
        if process_alive(wrapper):
            os.kill(wrapper, signal.SIGTERM)
            wait_for_exit(wrapper, 2)
        print(f"wrapper_alive={process_alive(wrapper)}")
        print(f"worker_alive={process_alive(worker)}")
        print(f"events={data['events']}")
    elif case_id == "09-reserved-not-resident":
        pid = int(data["memory_pid"])
        vsz, rss = memory_stats(pid)
        print(f"memory_pid={pid}")
        print(f"reserved_bytes={data['reserved_bytes']}")
        print(f"vsz_kib={vsz}")
        print(f"rss_kib={rss}")
    else:
        raise LabError(f"지원하지 않는 사례: {case_id}")


def status(root: Path) -> None:
    state = load_state(root)
    print(f"case={state['case_id']}")
    print(f"title={CASE_TITLES[state['case_id']]}")
    print(f"root={state['root']}")
    for item in state["processes"]:
        pid = int(item["pid"])
        print(f"process role={item['role']} pid={pid} alive={process_alive(pid)}")
    data = state["data"]
    for key in sorted(data):
        if key.endswith("_pid") or key in {"port", "fifo", "deleted_path", "dependency", "wrong_dir", "app_dir"}:
            print(f"{key}={data[key]}")


def destroy_case(root: Path, remove: bool = True) -> None:
    state = load_state(root)
    errors: list[str] = []
    canonical = root.resolve()
    owned = list(_OWNED_GROUPS.get(canonical, {}).values())
    if owned:
        for proc in owned:
            try:
                stop_owned_process_group(canonical, proc)
            except LabError as exc:
                errors.append(str(exc))
    else:
        for item in reversed(state.get("processes", [])):
            try:
                terminate_process(int(item["pid"]), root, item.get("start_token"))
            except LabError as exc:
                errors.append(str(exc))
    if errors:
        raise LabError("\n".join(errors))
    if remove:
        shutil.rmtree(root)
    _ACTIVE_ROOTS.discard(canonical)
    if _OWNED_GROUPS.get(canonical):
        raise LabError(f"cleanup 뒤 소유 process registry가 남았습니다: {canonical}")


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        raise LabError(message)


def hold_for_top_level_signal_fixture(case_id: str, root: Path, state: dict[str, Any]) -> None:
    requested = os.environ.get("GUIDE_LAB_SIGNAL_CASE", "")
    if requested != case_id:
        return
    evidence_value = os.environ.get("GUIDE_LAB_SIGNAL_EVIDENCE", "")
    evidence = Path(evidence_value)
    if not evidence.is_absolute() or evidence.exists() or evidence.is_symlink():
        raise LabError("signal fixture evidence는 존재하지 않는 절대 경로여야 합니다.")
    payload = {
        "root": str(root.resolve()),
        "processes": [
            {
                "pid": int(item["pid"]),
                "role": item["role"],
                "start_token": item["start_token"],
            }
            for item in state["processes"]
        ],
        "port": state.get("data", {}).get("port"),
    }
    temporary = evidence.with_name(f".{evidence.name}.{os.getpid()}.tmp")
    temporary.write_text(json.dumps(payload, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(temporary, evidence)
    while True:
        time.sleep(1)


def selftest_case(case_id: str, root: Path, *, fixed_worker_term_exit: int = 0) -> None:
    create_case(case_id, root, keep_active=True)
    state = load_state(root)
    data = state["data"]
    try:
        hold_for_top_level_signal_fixture(case_id, root, state)
        if case_id == "01-command-resolution":
            bad = subprocess.run([data["tool"]], env=env_for_command_case(state), capture_output=True, text=True, check=False)
            assert_true(bad.returncode == 42 and "stale" in bad.stderr, "PATH 우선순위 증상이 재현되지 않았습니다.")
            good = subprocess.run([data["tool"]], env=env_for_command_case(state, trusted_first=True), capture_output=True, text=True, check=False)
            assert_true(good.returncode == 0 and good.stdout.strip() == "ready", "신뢰한 실행 파일 선택으로 복구되지 않았습니다.")
        elif case_id == "02-dangling-symlink":
            current = root / "current"
            assert_true(current.is_symlink() and not current.exists(), "끊어진 symlink 상태가 아닙니다.")
            replacement = root / "current.next"
            os.symlink(data["valid_target"], replacement)
            os.replace(replacement, current)
            text = (current / "config.ini").read_text(encoding="utf-8")
            assert_true("status=ready" in text, "symlink 교체 뒤 대상을 읽지 못했습니다.")
        elif case_id == "03-waiting-for-input":
            reader = int(data["reader_pid"])
            assert_true(process_alive(reader) and not Path(data["output"]).exists(), "입력 대기 상태가 아닙니다.")
            with Path(data["fifo"]).open("w", encoding="utf-8") as stream:
                stream.write("resume\n")
            assert_true(wait_for_exit(reader, 2), "입력 제공 뒤 reader가 종료하지 않았습니다.")
            assert_true("received=resume" in Path(data["output"]).read_text(encoding="utf-8"), "reader 결과가 올바르지 않습니다.")
        elif case_id == "04-deleted-open-file":
            pid = int(data["writer_pid"])
            assert_true(process_alive(pid) and not Path(data["deleted_path"]).exists(), "삭제됐지만 열린 파일 상태가 아닙니다.")
            record = next(item for item in state["processes"] if int(item["pid"]) == pid)
            terminate_process(pid, root, record.get("start_token"))
            assert_true(not process_alive(pid), "writer 종료 뒤 FD가 정리되지 않았습니다.")
        elif case_id == "05-working-directory":
            bad = subprocess.run([PYTHON, data["script"]], cwd=data["wrong_dir"], capture_output=True, text=True, check=False)
            assert_true(bad.returncode == 2 and "config_error" in bad.stderr, "잘못된 cwd 증상이 재현되지 않았습니다.")
            good = subprocess.run([PYTHON, data["script"]], cwd=data["app_dir"], capture_output=True, text=True, check=False)
            assert_true(good.returncode == 0 and good.stdout.strip() == "service=ready", "올바른 cwd에서 복구되지 않았습니다.")
        elif case_id == "06-address-family-mismatch":
            failed = False
            try:
                ipv6_connect(int(data["port"]))
            except OSError:
                failed = True
            assert_true(failed, "IPv6 연결 실패가 재현되지 않았습니다.")
            assert_true(ipv4_connect(int(data["port"])).strip() == b"ready", "IPv4 연결은 성공해야 합니다.")
        elif case_id == "07-running-not-ready":
            status_code, _ = http_health(int(data["port"]))
            assert_true(status_code == 503, "dependency 부재 시 health 503이 아닙니다.")
            Path(data["dependency"]).write_text("ready\n", encoding="utf-8")
            status_code, body = http_health(int(data["port"]))
            assert_true(status_code == 200 and body == "ready", "dependency 준비 뒤 health가 복구되지 않았습니다.")
            Path(data["dependency"]).unlink()
            status_code, _ = http_health(int(data["port"]))
            assert_true(status_code == 503, "dependency 제거 뒤 health 실패 계약이 유지되지 않습니다.")
        elif case_id == "08-signal-not-forwarded":
            wrapper = int(data["wrapper_pid"])
            worker = int(data["worker_pid"])
            os.kill(wrapper, signal.SIGTERM)
            assert_true(wait_for_exit(wrapper, 2), "wrapper가 SIGTERM 뒤 종료하지 않았습니다.")
            assert_true(process_alive(worker), "오류 fixture의 worker가 함께 종료되어 증상이 재현되지 않았습니다.")
            events = Path(data["events"]).read_text(encoding="utf-8")
            assert_true("did not forward" in events, "wrapper 사건 기록이 없습니다.")
            record = next(item for item in state["processes"] if int(item["pid"]) == worker)
            terminate_process(worker, root, record.get("start_token"))
            fixed_ready = root / "fixed-worker.ready"
            fixed = start_script(
                root,
                Path(data["exec_wrapper_script"]),
                data["worker_script"],
                str(fixed_ready),
                str(fixed_worker_term_exit),
                role="fixed-exec-wrapper",
            )
            state["processes"].append(fixed)
            wait_for_path(fixed_ready)
            fixed_pid = int(fixed["pid"])
            fixed_proc = _OWNED_GROUPS[root.resolve()][fixed_pid]
            os.kill(fixed_pid, signal.SIGTERM)
            try:
                fixed_exit = fixed_proc.wait(timeout=2)
            except subprocess.TimeoutExpired as exc:
                raise LabError("exec 수정 뒤 TERM으로 worker가 종료하지 않았습니다.") from exc
            assert_true(fixed_exit == 0, f"exec 수정 뒤 worker 종료 상태가 0이 아닙니다: {fixed_exit}")
            assert_true(
                not process_group_alive(fixed_pid),
                "exec 수정 뒤 남은 child process group이 있습니다.",
            )
            unregister_owned_group(root, fixed_pid)
        elif case_id == "09-reserved-not-resident":
            pid = int(data["memory_pid"])
            vsz, rss = memory_stats(pid)
            assert_true(process_alive(pid), "memory process가 실행 중이 아닙니다.")
            assert_true(vsz > rss, f"VSZ가 RSS보다 커야 합니다: vsz={vsz} rss={rss}")
            assert_true(vsz - rss >= 16 * 1024, f"예약과 상주량 차이가 충분하지 않습니다: vsz={vsz} rss={rss}")
        else:
            raise LabError(f"selftest 미구현 사례: {case_id}")
    finally:
        if root.exists():
            destroy_case(root)
        for item in state["processes"]:
            assert_true(
                not process_alive(int(item["pid"])),
                f"cleanup 뒤 프로세스가 남았습니다: {item['role']} pid={item['pid']}",
            )
        if "port" in data:
            try:
                socket.create_connection(("127.0.0.1", int(data["port"])), timeout=0.2).close()
            except OSError:
                pass
            else:
                raise LabError(f"cleanup 뒤 listener가 남았습니다: 127.0.0.1:{data['port']}")


def selftest() -> None:
    with tempfile.TemporaryDirectory(prefix="unix-system-investigation-") as temporary:
        base = Path(temporary)
        for case_id in CASE_TITLES:
            root = base / case_id
            selftest_case(case_id, root)
            if _OWNED_GROUPS or _ACTIVE_ROOTS:
                raise LabError(
                    f"selftest 사례 뒤 소유 registry가 비어 있지 않습니다: "
                    f"groups={list(_OWNED_GROUPS)} roots={list(_ACTIVE_ROOTS)}"
                )
            print(f"PASS scenario {case_id}")
    print(f"PASS {len(CASE_TITLES)} scenarios")


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("list", help="사례 목록을 표시합니다.")
    create = sub.add_parser("create", help="사례를 새 디렉터리에 만듭니다.")
    create.add_argument("case_id", choices=CASE_TITLES)
    create.add_argument("destination", type=Path)
    for name in ("symptom", "status", "destroy"):
        item = sub.add_parser(name)
        item.add_argument("destination", type=Path)
    sub.add_parser("selftest", help="모든 사례의 증상과 최소 복구를 검사합니다.")
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    install_lab_signal_handlers()
    args = parse_args(argv)
    try:
        if args.command == "list":
            for case_id, title in CASE_TITLES.items():
                print(f"{case_id}\t{title}")
        elif args.command == "create":
            create_case(args.case_id, args.destination.resolve())
            print(f"created={args.destination.resolve()}")
            print(f"next={PYTHON} {Path(__file__).resolve()} symptom {args.destination.resolve()}")
        elif args.command == "symptom":
            symptom(args.destination.resolve())
        elif args.command == "status":
            status(args.destination.resolve())
        elif args.command == "destroy":
            destination = args.destination.resolve()
            destroy_case(destination)
            print(f"destroyed={destination}")
        elif args.command == "selftest":
            selftest()
        else:
            raise AssertionError(args.command)
    except (LabError, OSError, subprocess.SubprocessError, ValueError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
