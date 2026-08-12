#!/usr/bin/env python3
"""Prove the timeout runner kills only its owned leader and descendant."""

from __future__ import annotations

import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "scripts/run_with_timeout.py"
CHILD = """
import os
from pathlib import Path
import subprocess
import sys
leader_file = Path(sys.argv[1])
descendant = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(30)"])
leader_file.write_text(f"{os.getpid()} {descendant.pid}\\n", encoding="utf-8")
descendant.wait()
"""
STUBBORN_CHILD = """
import os
from pathlib import Path
import subprocess
import sys
import time
leader_file = Path(sys.argv[1])
ready_file = Path(sys.argv[2])
descendant_source = "import os, signal, sys, time; from pathlib import Path; signal.signal(signal.SIGTERM, signal.SIG_IGN); Path(sys.argv[1]).write_text(str(os.getpid()), encoding='utf-8'); time.sleep(30)"
descendant = subprocess.Popen([sys.executable, "-c", descendant_source, str(ready_file)])
deadline = time.monotonic() + 5
while not ready_file.is_file() and descendant.poll() is None and time.monotonic() < deadline:
    time.sleep(0.02)
leader_file.write_text(f"{os.getpid()} {descendant.pid}\\n", encoding="utf-8")
time.sleep(30)
"""


def exists(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def wait_gone(pids: list[int]) -> None:
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        if all(not exists(pid) for pid in pids):
            return
        time.sleep(0.05)
    raise AssertionError(f"owned process가 종료 뒤 남았습니다: {[pid for pid in pids if exists(pid)]}")


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="guide-runner-signal-") as temporary:
        pid_file = Path(temporary) / "pids"
        wrapper = subprocess.Popen(
            [sys.executable, str(RUNNER), "30", "--", sys.executable, "-c", CHILD, str(pid_file)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        deadline = time.monotonic() + 5
        while not pid_file.is_file() and wrapper.poll() is None and time.monotonic() < deadline:
            time.sleep(0.02)
        if not pid_file.is_file():
            wrapper.kill()
            raise AssertionError("owned process fixture PID를 관찰하지 못했습니다")
        pids = [int(value) for value in pid_file.read_text(encoding="utf-8").split()]
        wrapper.send_signal(signal.SIGTERM)
        stdout, stderr = wrapper.communicate(timeout=8)
        if wrapper.returncode != 143:
            raise AssertionError(f"signal runner exit={wrapper.returncode}\\n{stdout}\\n{stderr}")
        wait_gone(pids)

    with tempfile.TemporaryDirectory(prefix="guide-runner-timeout-") as temporary:
        pid_file = Path(temporary) / "pids"
        timed = subprocess.run(
            [sys.executable, str(RUNNER), "0.2", "--", sys.executable, "-c", CHILD, str(pid_file)],
            capture_output=True,
            text=True,
            check=False,
            timeout=8,
        )
        if timed.returncode != 124 or not pid_file.is_file():
            raise AssertionError(f"timeout runner contract 실패: {timed.returncode}\\n{timed.stdout}\\n{timed.stderr}")
        wait_gone([int(value) for value in pid_file.read_text(encoding="utf-8").split()])

    with tempfile.TemporaryDirectory(prefix="guide-runner-stubborn-") as temporary:
        pid_file = Path(temporary) / "pids"
        ready_file = Path(temporary) / "ready"
        stubborn = subprocess.run(
            [
                sys.executable,
                str(RUNNER),
                "0.3",
                "--",
                sys.executable,
                "-c",
                STUBBORN_CHILD,
                str(pid_file),
                str(ready_file),
            ],
            capture_output=True,
            text=True,
            check=False,
            timeout=10,
        )
        if stubborn.returncode != 124 or not pid_file.is_file() or not ready_file.is_file():
            raise AssertionError(
                f"SIGTERM 무시 descendant fixture 실패: {stubborn.returncode}\n"
                f"{stubborn.stdout}\n{stubborn.stderr}"
            )
        wait_gone([int(value) for value in pid_file.read_text(encoding="utf-8").split()])

    print("[PASS] owned process-group signal/timeout/stubborn-descendant cleanup; residual=0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
