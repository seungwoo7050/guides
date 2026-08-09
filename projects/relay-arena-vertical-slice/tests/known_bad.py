#!/usr/bin/env python3
"""Behavioral mutants used to prove that public Capstone checks reject regressions."""
from __future__ import annotations

import importlib.util
import os
from pathlib import Path
from typing import Any

REFERENCE = Path(__file__).resolve().parents[1] / "reference" / "relay_arena.py"
spec = importlib.util.spec_from_file_location("relay_arena_reference", REFERENCE)
if spec is None or spec.loader is None:
    raise SystemExit("cannot load reference implementation")
relay = importlib.util.module_from_spec(spec)
spec.loader.exec_module(relay)

mutant = os.environ.get("RELAY_MUTANT")
if mutant == "unbounded_catchup":
    relay.MAX_STEPS_PER_FRAME = 10_000
elif mutant == "accept_non_owner":
    original_apply = relay.apply_command

    def accept_non_owner(state: dict[str, Any], command: dict[str, Any], rules: dict[str, Any]) -> None:
        changed = dict(command)
        if changed.get("player") == "p2":
            changed["player"] = "p1"
        original_apply(state, changed, rules)

    relay.apply_command = accept_non_owner
elif mutant == "presentation_writes_state":
    original_emit = relay.emit_presentation

    def presentation_writes_state(state: dict[str, Any], event_id: str, kind: str, target: str) -> None:
        original_emit(state, event_id, kind, target)
        state["x_milli"] += 1

    relay.emit_presentation = presentation_writes_state
elif mutant == "overwrite_failed_save":
    original_migrate = relay.migrate_save

    def overwrite_failed_save(source: Path, contract: Path, output: Path) -> dict[str, Any]:
        try:
            return original_migrate(source, contract, output)
        except Exception:
            output.write_text("{}\n", encoding="utf-8")
            raise

    relay.migrate_save = overwrite_failed_save
else:
    raise SystemExit(f"unknown RELAY_MUTANT: {mutant!r}")

raise SystemExit(relay.main())
