#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


interrupt = load_module(
    "interrupt_event_model",
    ROOT / "examples/interrupt-event-model/model.py",
)
update = load_module(
    "update_state_model",
    ROOT / "examples/update-state-model/model.py",
)


class InterruptModelTests(unittest.TestCase):
    def test_all_fixtures(self) -> None:
        for path in sorted((ROOT / "examples/interrupt-event-model/fixtures").glob("*.json")):
            with self.subTest(path=path.name):
                data = json.loads(path.read_text(encoding="utf-8"))
                result, _ = interrupt.run_fixture(data)
                self.assertEqual([], interrupt.contains(result, data["expected"]))

    def test_capacity_must_be_positive(self) -> None:
        with self.assertRaises(interrupt.ModelError):
            interrupt.InterruptModel(capacity=0)

    def test_unknown_operation_is_rejected(self) -> None:
        model = interrupt.InterruptModel(capacity=1)
        with self.assertRaises(interrupt.ModelError):
            model.apply({"op": "UNKNOWN"})


class UpdateModelTests(unittest.TestCase):
    def test_all_fixtures(self) -> None:
        for path in sorted((ROOT / "examples/update-state-model/fixtures").glob("*.json")):
            with self.subTest(path=path.name):
                data = json.loads(path.read_text(encoding="utf-8"))
                result, _ = update.run_fixture(data)
                self.assertEqual([], update.contains(result, data["expected"]))

    def test_confirm_outside_trial_is_rejected_semantically(self) -> None:
        model = update.UpdateModel()
        model.apply({"op": "CONFIRM"})
        self.assertIn("confirm_outside_trial", model.errors)
        self.assertEqual("CONFIRMED", model.mode)
        self.assertEqual("A", model.current)

    def test_both_slots_invalid_enter_recovery(self) -> None:
        model = update.UpdateModel()
        model.apply({"op": "CORRUPT", "slot": "A"})
        model.apply({"op": "RESET"})
        self.assertEqual("RECOVERY", model.mode)
        self.assertIsNone(model.current)


class CommandLineTests(unittest.TestCase):
    def test_each_fixture_check_command(self) -> None:
        groups = [
            ROOT / "examples/interrupt-event-model",
            ROOT / "examples/update-state-model",
        ]
        for group in groups:
            model = group / "model.py"
            for fixture in sorted((group / "fixtures").glob("*.json")):
                with self.subTest(group=group.name, fixture=fixture.name):
                    completed = subprocess.run(
                        [sys.executable, str(model), str(fixture), "--check"],
                        text=True,
                        capture_output=True,
                        timeout=10,
                        check=False,
                    )
                    self.assertEqual(0, completed.returncode, completed.stdout + completed.stderr)
                    self.assertIn("CHECK OK", completed.stdout)


if __name__ == "__main__":
    unittest.main(verbosity=2)
