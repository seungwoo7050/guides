#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load_checker():
    path = ROOT / "scripts/check_docs.py"
    spec = importlib.util.spec_from_file_location("guide_check_docs", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load checker")
    module = importlib.util.module_from_spec(spec)
    sys.modules["guide_check_docs"] = module
    spec.loader.exec_module(module)
    return module


checker = load_checker()


class ValidatorTests(unittest.TestCase):
    def copy_source(self, target: Path) -> Path:
        copy = target / "repo"
        shutil.copytree(
            ROOT,
            copy,
            symlinks=True,
            ignore=shutil.ignore_patterns(".guide", ".git", "__pycache__", "*.pyc", "*.log", "workspace"),
        )
        return copy

    def test_current_repository_is_valid(self) -> None:
        counts = checker.validate(ROOT)
        self.assertEqual(20, counts["documents"])
        self.assertEqual(6, counts["exercises"])

    def test_broken_link_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory(prefix="embedded-validator-") as temp:
            copy = self.copy_source(Path(temp))
            with (copy / "README.md").open("a", encoding="utf-8") as stream:
                stream.write("\n[broken](docs/does-not-exist.md)\n")
            with self.assertRaises(checker.ValidationError):
                checker.validate(copy)

    def test_missing_required_file_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory(prefix="embedded-validator-") as temp:
            copy = self.copy_source(Path(temp))
            (copy / "docs/00-roadmap.md").unlink()
            with self.assertRaises(checker.ValidationError):
                checker.validate(copy)

    def test_wrong_model_expectation_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory(prefix="embedded-validator-") as temp:
            fixture = Path(temp) / "fixture.json"
            data = json.loads(
                (ROOT / "examples/interrupt-event-model/fixtures/normal.json").read_text(encoding="utf-8")
            )
            data["expected"]["dropped"] = 99
            fixture.write_text(json.dumps(data), encoding="utf-8")
            completed = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "examples/interrupt-event-model/model.py"),
                    str(fixture),
                    "--check",
                ],
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
            )
            self.assertEqual(1, completed.returncode)
            self.assertIn("CHECK FAILED", completed.stdout)


if __name__ == "__main__":
    unittest.main(verbosity=2)
