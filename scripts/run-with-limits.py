#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import resource
import signal
import subprocess
import sys


def cpu_limit(seconds: int) -> None:
    resource.setrlimit(resource.RLIMIT_CPU, (seconds, seconds + 1))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seconds", type=int, default=30)
    parser.add_argument("--cpu-seconds", type=int, default=20)
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    command = args.command[1:] if args.command[:1] == ["--"] else args.command
    if args.seconds < 1 or args.cpu_seconds < 1 or not command:
        parser.error("positive wall/CPU limits and a command are required")

    environment = os.environ.copy()
    environment.setdefault("PYTHONDONTWRITEBYTECODE", "1")
    process = subprocess.Popen(
        command,
        env=environment,
        start_new_session=True,
        preexec_fn=lambda: cpu_limit(args.cpu_seconds),
    )
    try:
        return process.wait(timeout=args.seconds)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(process.pid, signal.SIGTERM)
            process.wait(timeout=2)
        except (ProcessLookupError, subprocess.TimeoutExpired):
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            process.wait()
        print(
            f"TIMEOUT wall_seconds={args.seconds} cpu_seconds={args.cpu_seconds} command={command!r}",
            file=sys.stderr,
        )
        return 124


if __name__ == "__main__":
    raise SystemExit(main())
