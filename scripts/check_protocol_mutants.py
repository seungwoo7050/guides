#!/usr/bin/env python3
"""Prove public protocol tests reject representative plausible implementations."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXERCISE = ROOT / "exercises/protocol-inspector"

MUTANTS = (
    (
        "odd-checksum-padding",
        "checksum.py",
        'data += b"\\x00"',
        'data = b"\\x00" + data',
        "test_odd_length_is_padded_on_the_right",
    ),
    (
        "metric-before-prefix",
        "routing.py",
        "return max(candidates, key=lambda item: item[:3])[3]",
        "return max(candidates, key=lambda item: (item[1], item[0], item[2]))[3]",
        "test_longest_prefix_wins_even_with_higher_metric",
    ),
    (
        "listen-reset-closes",
        "tcp_state.py",
        "if self.state in {TCPState.CLOSED, TCPState.LISTEN}:",
        "if self.state in {TCPState.CLOSED}:",
        "test_reset_processing_depends_on_the_current_state",
    ),
)


def main() -> int:
    for name, module, old, new, expected_test in MUTANTS:
        with tempfile.TemporaryDirectory(prefix=f"guide-cn-mutant-{name}-") as temporary:
            implementation = Path(temporary) / "mutant"
            shutil.copytree(EXERCISE / "reference", implementation)
            path = implementation / "protocol_inspector" / module
            text = path.read_text(encoding="utf-8")
            if old not in text:
                raise AssertionError(f"mutant precondition missing: {name}")
            path.write_text(text.replace(old, new, 1), encoding="utf-8")
            environment = os.environ.copy()
            environment["PYTHONPATH"] = str(implementation)
            result = subprocess.run(
                [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"],
                cwd=EXERCISE,
                env=environment,
                capture_output=True,
                text=True,
                timeout=30,
                check=False,
            )
            output = result.stdout + result.stderr
            if result.returncode == 0 or expected_test not in output:
                raise AssertionError(f"protocol mutant was not rejected at {expected_test}: {name}\n{output}")
            print(f"[PASS] protocol mutant rejected: {name} -> {expected_test}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
