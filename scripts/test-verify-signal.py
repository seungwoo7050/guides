#!/usr/bin/env python3
"""Interrupt only top-level verify and prove zero owned process/temp residue."""

from __future__ import annotations

import json
import os
from pathlib import Path
import re
import shutil
import signal
import stat
import subprocess
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]


def run(command: list[str], cwd: Path, environment: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    values = os.environ.copy()
    values.update(
        {
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_TERMINAL_PROMPT": "0",
            "GIT_OPTIONAL_LOCKS": "0",
        }
    )
    if environment:
        values.update(environment)
    return subprocess.run(
        command,
        cwd=cwd,
        env=values,
        text=True,
        capture_output=True,
        timeout=60,
        check=False,
    )


def require(condition: bool, message: str, output: str = "") -> None:
    if not condition:
        raise AssertionError(message + (f"\n{output}" if output else ""))


def process_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def group_alive(group: int) -> bool:
    if os.name != "posix" or group <= 0:
        return False
    try:
        os.killpg(group, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def wait_gone(pids: tuple[int, ...], group: int, timeout: float = 6.0) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if not any(process_alive(pid) for pid in pids) and not group_alive(group):
            return True
        time.sleep(0.05)
    return not any(process_alive(pid) for pid in pids) and not group_alive(group)


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="guide-os-top-signal-") as temporary:
        fixture = Path(temporary).resolve()
        repository = fixture / "repository"
        shutil.copytree(
            ROOT,
            repository,
            symlinks=True,
            ignore=shutil.ignore_patterns(
                ".git",
                ".guide",
                ".pytest_cache",
                ".venv",
                "__pycache__",
                "build",
                "build-sanitize",
                "workspace",
                ".checker-mutant.*",
                ".workspace-copy.*",
                ".workspace-create.lock*",
                "*.pyc",
                "*.pyo",
            ),
        )
        for command in (["git", "init", "-q"],):
            result = run(list(command), repository)
            require(result.returncode == 0, "signal fixture git init 실패", result.stdout + result.stderr)
        manifest = (repository / "scripts/layout-manifest.txt").read_text(encoding="utf-8").splitlines()
        result = run(["git", "add", "--", *manifest], repository)
        require(result.returncode == 0, "signal fixture exact staging 실패", result.stdout + result.stderr)
        result = run(
            [
                "git",
                "-c",
                "user.name=Guide Audit",
                "-c",
                "user.email=guide-audit@example.invalid",
                "commit",
                "-q",
                "-m",
                "signal fixture",
            ],
            repository,
        )
        require(result.returncode == 0, "signal fixture commit 실패", result.stdout + result.stderr)

        runtime = fixture / "runtime"
        runtime.mkdir()
        prepare = run(["bash", "prepare.sh"], repository, {"TMPDIR": str(runtime)})
        require(
            prepare.returncode == 0 and prepare.stdout.count("PREPARE RESULT: PASS") == 1,
            "signal fixture prepare 실패",
            prepare.stdout + prepare.stderr,
        )

        marker = repository / ".guide/operating-systems/prepared.json"
        marker_bytes = marker.read_bytes()
        marker_mode = stat.S_IMODE(marker.stat().st_mode)
        marker_payload = json.loads(marker_bytes)
        version_mutants = (
            ("python_version", "Python version"),
            ("git_version", "Git version"),
            ("make_version", "make version"),
            ("rsync_version", "rsync version"),
            ("bash_version", "Bash version"),
            ("cc_path", "C compiler 경로"),
            ("cc_version", "C compiler version"),
            ("platform_system", "platform"),
        )
        for field, expected in version_mutants:
            mutant = dict(marker_payload)
            mutant[field] = str(mutant[field]) + "-mutant"
            marker.write_text(
                json.dumps(mutant, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
            marker.chmod(marker_mode)
            marker_log = fixture / f"marker-{field}.log"
            rejected = run(
                ["bash", "verify.sh"],
                repository,
                {"TMPDIR": str(runtime), "VERIFY_LOG": str(marker_log)},
            )
            rejected_output = rejected.stdout + rejected.stderr
            require(
                rejected.returncode == 2
                and expected in rejected_output
                and len(re.findall(r"^passed=\d+ failed=1 skipped=\d+$", rejected_output, flags=re.MULTILINE)) == 1
                and rejected_output.count("VERIFY LOG:") == 1
                and rejected_output.count("RESULT: FAIL") == 1
                and rejected_output.count("[verify] ERROR:") == 1,
                f"marker tool-version mutant를 거부하지 못했습니다: {field}",
                rejected_output,
            )
            marker.write_bytes(marker_bytes)
            marker.chmod(marker_mode)
        require(marker.read_bytes() == marker_bytes and stat.S_IMODE(marker.stat().st_mode) == marker_mode, "marker 복원 실패")

        info = fixture / "owned-processes.json"
        log = fixture / "verify-signal.log"
        environment = os.environ.copy()
        environment.update(
            {
                "TMPDIR": str(runtime),
                "VERIFY_LOG": str(log),
                "GUIDE_VERIFY_SIGNAL_PROBE": str(info),
                "GIT_OPTIONAL_LOCKS": "0",
            }
        )
        verify = subprocess.Popen(
            ["bash", "verify.sh"],
            cwd=repository,
            env=environment,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        deadline = time.monotonic() + 15
        while not info.exists() and verify.poll() is None and time.monotonic() < deadline:
            time.sleep(0.02)
        require(info.is_file(), "top-level verify owned process tree를 관찰하지 못했습니다")
        data = json.loads(info.read_text(encoding="utf-8"))
        pids = (int(data["probe_pid"]), int(data["grandchild_pid"]))
        group = int(data["process_group"])
        work_directories = list(runtime.glob("guide-os-verify.*"))
        require(len(work_directories) == 1, f"verify owned work directory 수가 다릅니다: {work_directories}")

        os.kill(verify.pid, signal.SIGTERM)
        stdout, stderr = verify.communicate(timeout=12)
        output = stdout + stderr
        require(verify.returncode == 143, f"top-level SIGTERM 반환값 오류: {verify.returncode}", output)
        require(wait_gone(pids, group), f"top-level 종료 뒤 owned process/group이 남았습니다: pids={pids} pgid={group}")
        require(not list(runtime.glob("guide-os-verify.*")), "top-level 종료 뒤 owned work directory가 남았습니다")
        summaries = re.findall(r"^passed=\d+ failed=1 skipped=\d+$", output, flags=re.MULTILINE)
        require(len(summaries) == 1, "signal 실패 summary가 정확히 한 번이 아닙니다", output)
        require(output.count("VERIFY LOG:") == 1, "signal VERIFY LOG가 정확히 한 번이 아닙니다", output)
        require(output.count("RESULT: FAIL") == 1, "signal RESULT가 정확히 한 번이 아닙니다", output)
        require(output.count("top-level signal=15") == 1, "signal 실패 기록이 정확히 한 번이 아닙니다", output)

    print(
        "[PASS] marker tool-version mutants=8 + top-level verify SIGTERM: "
        "child/grandchild/group/workdir residue 0 + exact summary"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
