#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import signal
import subprocess
import sys
import time
from collections.abc import Sequence


def terminate_group(process: subprocess.Popen[bytes], grace: float = 1.0) -> None:
    if process.poll() is not None:
        return
    try:
        os.killpg(process.pid, signal.SIGTERM)
    except ProcessLookupError:
        return
    deadline = time.monotonic() + grace
    while process.poll() is None and time.monotonic() < deadline:
        time.sleep(0.02)
    if process.poll() is None:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass


def run(seconds: float, command: Sequence[str]) -> int:
    process = subprocess.Popen(command, start_new_session=True)

    def forward(signum: int, _frame: object) -> None:
        terminate_group(process)
        raise SystemExit(128 + signum)

    previous = {sig: signal.signal(sig, forward) for sig in (signal.SIGHUP, signal.SIGINT, signal.SIGTERM)}
    try:
        try:
            return process.wait(timeout=seconds)
        except subprocess.TimeoutExpired:
            print(f"TIMEOUT after {seconds:g}s: {' '.join(command)}", file=sys.stderr)
            terminate_group(process)
            process.wait()
            return 124
    finally:
        for sig, handler in previous.items():
            signal.signal(sig, handler)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("seconds", type=float)
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    command = args.command[1:] if args.command[:1] == ["--"] else args.command
    if args.seconds <= 0 or not command:
        parser.error("positive timeout and command are required")
    return run(args.seconds, command)


if __name__ == "__main__":
    raise SystemExit(main())
