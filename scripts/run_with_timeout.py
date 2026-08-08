#!/usr/bin/env python3
"""Run one verification command in an isolated process group.

The direct command and every descendant belong to a fresh session. A timeout,
caller interruption, or normal command exit terminates any descendants that
remain, so broken tests cannot leave servers running after verify.sh returns.
"""

from __future__ import annotations

import argparse
import os
import signal
import subprocess
import sys
import time
from collections.abc import Sequence


class ProcessGroupRunner:
    def __init__(self, command: Sequence[str], timeout: float) -> None:
        self.command = list(command)
        self.timeout = timeout
        self.process: subprocess.Popen[bytes] | None = None

    def signal_group(self, signum: int) -> None:
        if self.process is None:
            return
        try:
            os.killpg(self.process.pid, signum)
        except (ProcessLookupError, PermissionError):
            pass

    def stop_group(self, grace: float = 5.0) -> None:
        if self.process is None:
            return
        self.signal_group(signal.SIGTERM)
        if self.process.poll() is None:
            try:
                self.process.wait(timeout=grace)
            except subprocess.TimeoutExpired:
                self.signal_group(signal.SIGKILL)
                self.process.wait()
        # The direct child can exit while a test server remains in its group.
        # Give that descendant a short graceful window, then guarantee removal.
        self.signal_group(signal.SIGTERM)
        time.sleep(0.1)
        self.signal_group(signal.SIGKILL)

    def relay(self, signum: int, _frame) -> None:
        self.stop_group()
        raise SystemExit(128 + signum)

    def run(self) -> int:
        try:
            self.process = subprocess.Popen(self.command, start_new_session=True)
        except FileNotFoundError:
            print(f"COMMAND NOT FOUND: {self.command[0]}", file=sys.stderr)
            return 127
        except OSError as error:
            print(f"COMMAND START FAILED: {error}", file=sys.stderr)
            return 126

        previous = {
            watched: signal.signal(watched, self.relay)
            for watched in (signal.SIGHUP, signal.SIGINT, signal.SIGTERM)
        }
        try:
            try:
                return_code = self.process.wait(timeout=self.timeout)
            except subprocess.TimeoutExpired:
                print(
                    f"TIMEOUT after {self.timeout:g}s: {' '.join(self.command)}",
                    file=sys.stderr,
                )
                self.stop_group()
                return 124

            self.stop_group(grace=0.1)
            if return_code < 0:
                return 128 + (-return_code)
            return return_code
        finally:
            for watched, handler in previous.items():
                signal.signal(watched, handler)


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("timeout", type=float)
    parser.add_argument("command", nargs=argparse.REMAINDER)
    arguments = parser.parse_args()
    if arguments.timeout <= 0:
        parser.error("timeout must be positive")
    if arguments.command and arguments.command[0] == "--":
        arguments.command = arguments.command[1:]
    if not arguments.command:
        parser.error("a command is required after timeout")
    return arguments


def main() -> int:
    arguments = parse_arguments()
    return ProcessGroupRunner(arguments.command, arguments.timeout).run()


if __name__ == "__main__":
    raise SystemExit(main())
