#!/usr/bin/env python3
"""Execute one command as a process-group leader for reliable cancellation."""

from __future__ import annotations

import os
import signal
import sys


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: run_in_session.py COMMAND [ARG ...]", file=sys.stderr)
        return 2
    # An asynchronous shell job may inherit SIGINT/SIGHUP as ignored. Reset
    # them before exec so the target script can install its own traps.
    for handled in (signal.SIGHUP, signal.SIGINT, signal.SIGTERM):
        signal.signal(handled, signal.SIG_DFL)
    os.setsid()
    os.execvp(sys.argv[1], sys.argv[1:])
    return 127


if __name__ == "__main__":
    raise SystemExit(main())
