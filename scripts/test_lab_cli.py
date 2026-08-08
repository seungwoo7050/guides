#!/usr/bin/env python3
"""Exercise every scenario through the public CLI and verify all result channels."""

from __future__ import annotations

import importlib.util
import json
import os
import re
import socket
import subprocess
import sys
import tempfile
import time
from unittest import mock
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LAB = ROOT / "exercises/system-investigation/lab.py"


def check_process_identity_races() -> None:
    spec = importlib.util.spec_from_file_location("unix_lab_identity_test", LAB)
    if spec is None or spec.loader is None:
        raise RuntimeError("lab.py를 test module로 읽지 못했습니다.")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    case_root = Path("/private/tmp/identity-race-case")

    native_token, native_detail = module.probe_process_start_token(os.getpid())
    if sys.platform == "darwin":
        if not native_token.startswith("darwin-start-time:") or native_detail != "libproc ok":
            raise RuntimeError(f"Darwin libproc token probe 실패: {native_token!r} {native_detail}")
        if module.ctypes.sizeof(module.ProcBsdInfo) != 136:
            raise RuntimeError("Darwin proc_bsdinfo ABI size가 136이 아닙니다.")
        command, command_detail = module.darwin_command_line(os.getpid())
        if "scripts/test_lab_cli.py" not in command or command_detail != "sysctl ok":
            raise RuntimeError(f"Darwin native argv probe 실패: {command!r} {command_detail}")
    elif sys.platform.startswith("linux") and not native_token.startswith("linux-start-ticks:"):
        raise RuntimeError(f"Linux /proc start token probe 실패: {native_token!r} {native_detail}")

    zombie = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(0.05)"])
    zombie_token = module.process_start_token(zombie.pid)
    if not zombie_token:
        zombie.kill()
        zombie.wait()
        raise RuntimeError("zombie regression fixture의 시작 token을 기록하지 못했습니다.")
    time.sleep(0.12)
    if module.pid_reachable(zombie.pid):
        zombie.kill()
        zombie.wait()
        raise RuntimeError("native zombie를 reachable로 분류했습니다.")
    identity, _ = module.classify_case_process(zombie.pid, case_root, zombie_token)
    if identity != "gone":
        raise RuntimeError(f"native zombie classify 결과가 gone이 아닙니다: {identity}")

    with mock.patch.object(
        module.subprocess,
        "run",
        side_effect=subprocess.TimeoutExpired(["ps"], 0.01),
    ):
        token, detail = module.fallback_ps_start_token(os.getpid(), 0.01)
    if token or "timeout=" not in detail:
        raise RuntimeError(f"fallback ps timeout 진단 실패: {token!r} {detail}")
    empty_result = subprocess.CompletedProcess(["ps"], 0, stdout="", stderr="")
    with mock.patch.object(module.subprocess, "run", return_value=empty_result):
        token, detail = module.fallback_ps_start_token(os.getpid(), 0.01)
    if token or "empty-output" not in detail:
        raise RuntimeError(f"fallback ps empty 진단 실패: {token!r} {detail}")

    with mock.patch.object(
        module,
        "probe_process_start_token",
        side_effect=[("", "forced timeout"), ("", "forced empty"), ("eventual-token", "ok")],
    ):
        observation = module.wait_for_start_token(
            4242,
            timeout=0.2,
            alive_probe=lambda: True,
            max_attempts=5,
            retry_delay=0,
        )
    if observation.token != "eventual-token" or observation.attempts != 3:
        raise RuntimeError(f"live token eventual success 실패: {observation}")

    def bounded_timeout_run(*_args: object, timeout: float, **_kwargs: object) -> None:
        time.sleep(timeout)
        raise subprocess.TimeoutExpired(["ps"], timeout)

    def unsupported_probe(pid: int, *, fallback_timeout: float) -> tuple[str, str]:
        return module.fallback_ps_start_token(pid, fallback_timeout)

    started = time.monotonic()
    with (
        mock.patch.object(module, "probe_process_start_token", side_effect=unsupported_probe),
        mock.patch.object(module.subprocess, "run", side_effect=bounded_timeout_run),
    ):
        observation = module.wait_for_start_token(
            4242,
            timeout=0.05,
            alive_probe=lambda: True,
            probe_timeout=0.2,
            max_attempts=10,
            retry_delay=0,
        )
    elapsed = time.monotonic() - started
    if observation.token is not None or elapsed > 0.12:
        raise RuntimeError(f"outer token deadline 초과: elapsed={elapsed:.3f} {observation}")

    with (
        mock.patch.object(module, "process_alive", side_effect=[True, False]),
        mock.patch.object(module, "process_start_token", return_value="start-a"),
        mock.patch.object(module, "command_line", return_value=""),
    ):
        identity, _ = module.classify_case_process(
            4242, case_root, "start-a", retries=2, delay=0
        )
    if identity != "gone":
        raise RuntimeError(f"identity disappearance race: {identity}")

    with (
        mock.patch.object(module, "process_alive", return_value=True),
        mock.patch.object(module, "process_start_token", return_value="start-b"),
        mock.patch.object(module, "command_line") as command_probe,
    ):
        identity, _ = module.classify_case_process(
            4242, case_root, "start-a", retries=2, delay=0
        )
    if identity != "reused" or command_probe.called:
        raise RuntimeError(f"identity PID reuse race: {identity}")

    with (
        mock.patch.object(module, "process_alive", return_value=True),
        mock.patch.object(module, "process_start_token", return_value="replacement-start"),
        mock.patch.object(module, "command_line") as mismatch_command,
        mock.patch.object(module.os, "kill") as mismatch_kill,
    ):
        module.terminate_process(4242, case_root, "recorded-start")
    if mismatch_command.called or mismatch_kill.called:
        raise RuntimeError("PID start mismatch에서 command probe 또는 signal이 실행됐습니다.")

    with (
        mock.patch.object(module, "process_alive", return_value=True),
        mock.patch.object(module, "process_start_token", return_value="start-a"),
        mock.patch.object(module, "command_line", return_value=""),
        mock.patch.object(module.os, "kill") as kill,
    ):
        try:
            module.terminate_process(4242, case_root, "start-a")
        except module.LabError:
            pass
        else:
            raise RuntimeError("unavailable identity가 안전 실패하지 않았습니다.")
    if kill.called:
        raise RuntimeError("identity가 비어 있는데 PID를 종료했습니다.")

    with (
        mock.patch.object(module, "process_alive", return_value=True),
        mock.patch.object(module, "process_start_token", return_value=""),
        mock.patch.object(module, "command_line", return_value=f"python {case_root}/worker.py") as command_probe,
        mock.patch.object(module.os, "kill") as empty_token_kill,
    ):
        try:
            module.terminate_process(4242, case_root, "recorded-start")
        except module.LabError:
            pass
        else:
            raise RuntimeError("빈 start token이 matching command만으로 owned가 됐습니다.")
    if command_probe.called or empty_token_kill.called:
        raise RuntimeError("빈 start token 상태에서 command probe 또는 signal이 실행됐습니다.")

    with tempfile.TemporaryDirectory(prefix="unix-lab-immediate-exit-") as directory:
        immediate_root = Path(directory)
        pid_file = immediate_root / "pid.txt"
        script = immediate_root / "immediate_exit.py"
        script.write_text(
            "import os, pathlib, sys\n"
            "pathlib.Path(sys.argv[1]).write_text(str(os.getpid()), encoding='utf-8')\n"
            "print('fixture-ended', file=sys.stderr, flush=True)\n",
            encoding="utf-8",
        )
        with (
            mock.patch.object(module, "probe_process_start_token", return_value=("", "forced empty")),
            mock.patch.object(module.os, "kill") as startup_kill,
            mock.patch.object(module.os, "killpg") as startup_group_kill,
        ):
            try:
                module.start_script(
                    immediate_root,
                    script,
                    str(pid_file),
                    role="forced-immediate-exit",
                )
            except module.LabError as error:
                detail = str(error)
            else:
                raise RuntimeError("즉시 종료한 long-lived fixture가 생성 성공했습니다.")
        if "role=forced-immediate-exit" not in detail or "exit=0" not in detail:
            raise RuntimeError(f"즉시 종료 fixture의 role/exit 진단이 없습니다: {detail}")
        if "fixture-ended" not in detail:
            raise RuntimeError(f"즉시 종료 fixture의 stderr 진단이 없습니다: {detail}")
        if startup_kill.called or startup_group_kill.called:
            raise RuntimeError("이미 종료·회수한 fixture PID에 신호를 보냈습니다.")
        if not pid_file.is_file() or module.process_alive(int(pid_file.read_text())):
            raise RuntimeError("즉시 종료 fixture가 회수되지 않았습니다.")

    with tempfile.TemporaryDirectory(prefix="unix-lab-token-unavailable-") as directory:
        unavailable_root = Path(directory)
        pid_file = unavailable_root / "pid.txt"
        script = unavailable_root / "long_lived.py"
        script.write_text(
            "import os, pathlib, sys, time\n"
            "pathlib.Path(sys.argv[1]).write_text(str(os.getpid()), encoding='utf-8')\n"
            "while True: time.sleep(1)\n",
            encoding="utf-8",
        )
        with mock.patch.object(
            module,
            "probe_process_start_token",
            return_value=("", "forced permanent timeout"),
        ):
            try:
                module.start_script(
                    unavailable_root,
                    script,
                    str(pid_file),
                    role="forced-token-unavailable",
                    token_timeout=0.08,
                )
            except module.LabError as error:
                detail = str(error)
            else:
                raise RuntimeError("token 영구 불가인 live fixture가 생성 성공했습니다.")
        pid_match = re.search(r"PID (\d+)", detail)
        if pid_match is None:
            raise RuntimeError(f"token 영구 불가 진단에 PID가 없습니다: {detail}")
        pid = int(pid_match.group(1))
        if "소유 Popen group" not in detail or "forced permanent timeout" not in detail:
            raise RuntimeError(f"token 영구 불가 진단이 부족합니다: {detail}")
        if module.process_alive(pid) or module._OWNED_GROUPS.get(unavailable_root.resolve()):
            raise RuntimeError("token 영구 불가 fixture가 회수되지 않았습니다.")

    with tempfile.TemporaryDirectory(prefix="unix-lab-wrapper-partial-") as directory:
        partial_root = Path(directory) / "case"
        observed_pids: list[int] = []
        original_wait = module.wait_for_start_token

        def fail_worker_observation(pid: int, *args: object, **kwargs: object):
            observed_pids.append(pid)
            if len(observed_pids) == 2:
                return module.StartTokenObservation(None, True, 1, "forced worker token failure")
            return original_wait(pid, *args, **kwargs)

        with mock.patch.object(module, "wait_for_start_token", side_effect=fail_worker_observation):
            try:
                module.create_case("08-signal-not-forwarded", partial_root)
            except module.LabError as error:
                detail = str(error)
            else:
                raise RuntimeError("worker token 실패 fixture가 생성 성공했습니다.")
        if "forced worker token failure" not in detail or partial_root.exists():
            raise RuntimeError(f"scenario08 partial failure cleanup 진단 실패: {detail}")
        if any(module.process_alive(pid) for pid in observed_pids):
            raise RuntimeError(f"scenario08 partial failure process residue: {observed_pids}")
        if module._OWNED_GROUPS or module._ACTIVE_ROOTS:
            raise RuntimeError("scenario08 partial failure registry/root residue가 남았습니다.")

    with tempfile.TemporaryDirectory(prefix="unix-lab-wrapper-exit-") as directory:
        exit_root = Path(directory) / "case"
        try:
            module.selftest_case(
                "08-signal-not-forwarded",
                exit_root,
                fixed_worker_term_exit=7,
            )
        except module.LabError as error:
            detail = str(error)
        else:
            raise RuntimeError("scenario08 수정 fixture의 non-zero 종료 상태를 놓쳤습니다.")
        if "종료 상태가 0이 아닙니다: 7" not in detail:
            raise RuntimeError(f"scenario08 non-zero 종료 상태 진단이 없습니다: {detail}")
        if exit_root.exists() or module._OWNED_GROUPS or module._ACTIVE_ROOTS:
            raise RuntimeError("scenario08 non-zero 종료 실패 경로에 자원·registry가 남았습니다.")
    print("PASS process identity disappearance/reuse safety")
    print("PASS native birth token and bounded fallback probe safety")
    print("PASS long-lived fixture immediate-exit startup failure safety")
    print("PASS permanent-token-unavailable and scenario08 failure cleanup safety")
    print("PASS scenario08 fixed-worker exit-status contract")


def run(*arguments: str, timeout: float = 15) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, "-B", str(LAB), *arguments], cwd=ROOT,
                          text=True, capture_output=True, timeout=timeout, check=False)


def assert_result(result: subprocess.CompletedProcess[str], label: str, token: str) -> None:
    if result.returncode != 0 or token not in result.stdout or result.stderr:
        raise RuntimeError(
            f"{label}: status={result.returncode} stdout={result.stdout!r} stderr={result.stderr!r}"
        )


def alive(pid: int) -> bool:
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
                return False
        except OSError:
            pass
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def main() -> int:
    check_process_identity_races()
    listed = run("list")
    assert_result(listed, "list", "09-reserved-not-resident")
    case_ids = [line.split("\t", 1)[0] for line in listed.stdout.splitlines() if line.strip()]
    if len(case_ids) != 9:
        raise RuntimeError(f"list: expected 9 cases, got {case_ids}")
    with tempfile.TemporaryDirectory(prefix="unix-lab-cli-") as directory:
        base = Path(directory)
        for case_id in case_ids:
            destination = base / case_id
            try:
                created = run("create", case_id, str(destination))
                assert_result(created, f"{case_id} create", "created=")
                state = json.loads((destination / ".case.json").read_text(encoding="utf-8"))
                if state.get("schema_version") != 2:
                    raise RuntimeError(f"{case_id}: process identity state schema가 2가 아닙니다.")
                for item in state.get("processes", []):
                    if not item.get("start_token"):
                        raise RuntimeError(f"{case_id}: start_token이 없습니다: {item}")
                pids = [int(item["pid"]) for item in state.get("processes", [])]
                port = state.get("data", {}).get("port")
                symptom = run("symptom", str(destination))
                assert_result(symptom, f"{case_id} symptom", f"case={case_id}")
                status = run("status", str(destination))
                assert_result(status, f"{case_id} status", f"case={case_id}")
                destroyed = run("destroy", str(destination))
                assert_result(destroyed, f"{case_id} destroy", "destroyed=")
                if destination.exists() or any(alive(pid) for pid in pids):
                    raise RuntimeError(f"{case_id}: cleanup 뒤 경로나 프로세스가 남았습니다.")
                if port is not None:
                    try:
                        socket.create_connection(("127.0.0.1", int(port)), timeout=0.2).close()
                    except OSError:
                        pass
                    else:
                        raise RuntimeError(f"{case_id}: cleanup 뒤 listener가 남았습니다: {port}")
            finally:
                if destination.exists():
                    run("destroy", str(destination))
            print(f"PASS CLI result and cleanup: {case_id}")
    print("LAB CLI CONTRACTS: PASS (9)")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, subprocess.SubprocessError, ValueError) as error:
        print(f"FAIL: {error}", file=sys.stderr)
        raise SystemExit(1)
