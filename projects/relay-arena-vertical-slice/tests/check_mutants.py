#!/usr/bin/env python3
"""Run reference, starter, and known-bad implementations through one contract."""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parent
CHECKER = HERE / "check_contract.py"
REFERENCE = PROJECT / "reference" / "relay_arena.py"
STARTER = PROJECT / "starter" / "relay_arena.py"
KNOWN_BAD = HERE / "known_bad.py"
MUTANTS = ("unbounded_catchup", "accept_non_owner", "presentation_writes_state", "overwrite_failed_save")


def run(implementation: Path, expect: str, *, mutant: str | None = None) -> None:
    environment = os.environ.copy()
    if mutant:
        environment["RELAY_MUTANT"] = mutant
    result = subprocess.run(
        [sys.executable, str(CHECKER), "--implementation", str(implementation), "--expect", expect],
        text=True,
        capture_output=True,
        check=False,
        env=environment,
    )
    if result.returncode != 0:
        raise RuntimeError(f"contract matrix failed for {mutant or implementation.name}:\n{result.stdout}\n{result.stderr}")


def main() -> int:
    try:
        run(REFERENCE, "pass")
        run(STARTER, "incomplete")
        for mutant in MUTANTS:
            run(KNOWN_BAD, "incomplete", mutant=mutant)
    except RuntimeError as exc:
        print(f"CAPSTONE_META_ERROR {exc}", file=sys.stderr)
        return 1
    print(f"CAPSTONE_META_OK reference=1 starter_rejected=1 mutants_rejected={len(MUTANTS)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
