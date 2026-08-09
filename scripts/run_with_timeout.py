#!/usr/bin/env python3
"""Run one verifier command with a deadline and process-group cleanup."""

from __future__ import annotations

import argparse
import os
import signal
import subprocess
import sys


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--timeout", required=True, type=float)
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    command = args.command[1:] if args.command[:1] == ["--"] else args.command
    if args.timeout <= 0 or not command:
        parser.error("positive --timeout and a command are required")
    process = subprocess.Popen(command, start_new_session=True)
    try:
        return process.wait(timeout=args.timeout)
    except subprocess.TimeoutExpired:
        print(f"TIMEOUT after {args.timeout:g}s: {' '.join(command)}", file=sys.stderr)
        os.killpg(process.pid, signal.SIGTERM)
        try:
            process.wait(timeout=2)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGKILL)
            process.wait()
        return 124
    except KeyboardInterrupt:
        os.killpg(process.pid, signal.SIGINT)
        process.wait()
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
