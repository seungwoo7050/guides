#!/usr/bin/env python3
"""Run one owned process group with timeout and signal-safe cleanup."""

from __future__ import annotations

import argparse
import os
import signal
import subprocess
import sys
import time

process: subprocess.Popen[bytes] | None = None


def group_exists() -> bool:
    if process is None:
        return False
    try:
        os.killpg(process.pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def wait_group_gone(seconds: float) -> bool:
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        if not group_exists():
            return True
        time.sleep(0.02)
    return not group_exists()


def terminate_owned_group() -> None:
    global process
    if process is None or not group_exists():
        return
    try:
        os.killpg(process.pid, signal.SIGTERM)
    except ProcessLookupError:
        return
    if process.poll() is None:
        try:
            process.wait(timeout=2)
        except subprocess.TimeoutExpired:
            pass
    if wait_group_gone(2):
        return
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    if process.poll() is None:
        process.wait()
    if not wait_group_gone(2):
        raise RuntimeError("종료한 owned process group이 남았습니다")


def handle_signal(signum: int, _frame: object) -> None:
    terminate_owned_group()
    raise SystemExit(128 + signum)


def main() -> int:
    global process
    parser = argparse.ArgumentParser()
    parser.add_argument("seconds", type=float)
    parser.add_argument("command", nargs=argparse.REMAINDER)
    arguments = parser.parse_args()
    command = arguments.command[1:] if arguments.command[:1] == ["--"] else arguments.command
    if arguments.seconds <= 0 or not command:
        parser.error("positive timeout and command are required")

    for signum in (signal.SIGHUP, signal.SIGINT, signal.SIGTERM):
        signal.signal(signum, handle_signal)
    process = subprocess.Popen(command, start_new_session=True)
    try:
        returncode = process.wait(timeout=arguments.seconds)
        terminate_owned_group()
        return returncode
    except subprocess.TimeoutExpired:
        print(
            f"시간 제한 {arguments.seconds:g}초를 초과했습니다: {' '.join(command)}",
            file=sys.stderr,
        )
        terminate_owned_group()
        return 124


if __name__ == "__main__":
    raise SystemExit(main())
