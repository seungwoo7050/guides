#!/usr/bin/env python3
"""Importable but intentionally incomplete Relay Arena starter."""
from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any


def apply_command(state: dict[str, Any], command: dict[str, Any], rules: dict[str, Any]) -> None:
    """TODO: validate identity/phase/preconditions and mutate authoritative state once."""
    raise NotImplementedError("TODO apply_command")


def simulate(inputs: Path, schedule: str, scenario: str) -> dict[str, Any]:
    """TODO: implement bounded fixed-step, lifecycle, presentation and authority evidence."""
    raise NotImplementedError("TODO simulate")


def migrate_save(source: Path, contract: Path, output: Path) -> dict[str, Any]:
    """TODO: validate v1 and atomically publish a v2 save without destroying the prior file."""
    raise NotImplementedError("TODO migrate_save")


def profile_report(inputs: Path) -> dict[str, Any]:
    """TODO: preserve invariants while comparing a reproduced bottleneck before/after."""
    raise NotImplementedError("TODO profile_report")


def main() -> int:
    parser = argparse.ArgumentParser(description="Incomplete Relay Arena starter")
    parser.add_argument("command", choices=("simulate", "migrate-save", "profile"))
    parser.parse_known_args()
    parser.error("starter is intentionally incomplete; implement the documented public contract")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
