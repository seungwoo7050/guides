#!/usr/bin/env python3
"""Run one owned process tree with timeout, signal forwarding and zero descendants."""

from __future__ import annotations

import argparse
import os
import signal
import subprocess
import sys
import time


def group_exists(group_id: int) -> bool:
    if os.name != "posix":
        return False
    try:
        os.killpg(group_id, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def stop_owned_tree(process: subprocess.Popen[object], initial_signal: int = signal.SIGTERM) -> None:
    if os.name == "posix":
        try:
            os.killpg(process.pid, initial_signal)
        except ProcessLookupError:
            pass
    elif process.poll() is None:
        process.terminate()

    deadline = time.monotonic() + 2.0
    while process.poll() is None and time.monotonic() < deadline:
        time.sleep(0.02)
    if os.name == "posix" and group_exists(process.pid):
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
    elif process.poll() is None:
        process.kill()
    try:
        process.wait(timeout=2)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait()
    if os.name == "posix":
        deadline = time.monotonic() + 2.0
        while group_exists(process.pid) and time.monotonic() < deadline:
            time.sleep(0.02)


def clear_remaining_descendants(process: subprocess.Popen[object]) -> None:
    if os.name == "posix" and group_exists(process.pid):
        try:
            os.killpg(process.pid, signal.SIGTERM)
        except ProcessLookupError:
            return
        deadline = time.monotonic() + 0.5
        while group_exists(process.pid) and time.monotonic() < deadline:
            time.sleep(0.02)
        if group_exists(process.pid):
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
        deadline = time.monotonic() + 2.0
        while group_exists(process.pid) and time.monotonic() < deadline:
            time.sleep(0.02)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--timeout", type=float, required=True)
    parser.add_argument("command", nargs=argparse.REMAINDER)
    arguments = parser.parse_args()
    command = arguments.command
    if command and command[0] == "--":
        command = command[1:]
    if arguments.timeout <= 0:
        parser.error("--timeout은 양수여야 합니다")
    if not command:
        parser.error("실행할 command가 필요합니다")

    received_signal = 0

    def handle_signal(signum: int, _frame: object) -> None:
        nonlocal received_signal
        if not received_signal:
            received_signal = signum

    previous = {
        signum: signal.signal(signum, handle_signal)
        for signum in (signal.SIGHUP, signal.SIGINT, signal.SIGTERM)
    }
    try:
        process = subprocess.Popen(command, start_new_session=os.name == "posix")
        deadline = time.monotonic() + arguments.timeout
        while True:
            if received_signal:
                stop_owned_tree(process, received_signal)
                clear_remaining_descendants(process)
                print(f"SIGNAL: owned process tree 종료: {received_signal}", file=sys.stderr)
                return 128 + received_signal
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                stop_owned_tree(process)
                clear_remaining_descendants(process)
                print(
                    f"TIMEOUT: {arguments.timeout:g}초를 넘었습니다: {' '.join(command)}",
                    file=sys.stderr,
                )
                return 124
            try:
                status = process.wait(timeout=min(0.05, remaining))
            except subprocess.TimeoutExpired:
                continue
            clear_remaining_descendants(process)
            if received_signal:
                print(f"SIGNAL: owned process tree 종료: {received_signal}", file=sys.stderr)
                return 128 + received_signal
            return status
    finally:
        for signum, handler in previous.items():
            signal.signal(signum, handler)


if __name__ == "__main__":
    raise SystemExit(main())
