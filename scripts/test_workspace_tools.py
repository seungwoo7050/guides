#!/usr/bin/env python3
"""Negative and preservation tests for scripts/new-workspace.sh."""

from __future__ import annotations

import os
import subprocess
import tempfile
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/new-workspace.sh"
UNIT = ROOT / "exercises/01-image-and-memory-audit"


def run_tool(source: str | Path, destination: Path) -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy()
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    return subprocess.run(
        [str(SCRIPT), str(source), str(destination)],
        cwd=ROOT,
        env=environment,
        capture_output=True,
        text=True,
        timeout=15,
        check=False,
    )


class WorkspaceToolTests(unittest.TestCase):
    def test_starter_is_copied_and_scaffold_is_added(self) -> None:
        with tempfile.TemporaryDirectory(prefix="embedded-workspace-") as temporary:
            destination = Path(temporary).resolve() / "learner"
            completed = run_tool("exercises/01-image-and-memory-audit", destination)
            self.assertEqual(0, completed.returncode, completed.stdout + completed.stderr)
            self.assertEqual(
                (UNIT / "starter/submission.json").read_bytes(),
                (destination / "submission.json").read_bytes(),
            )
            for relative in ("README.md", "design.md", "report.md"):
                self.assertTrue((destination / relative).is_file(), relative)
            self.assertTrue((destination / "evidence").is_dir())
            self.assertIn("CREATED", completed.stdout)

    def test_existing_destination_is_rejected_without_truncation(self) -> None:
        with tempfile.TemporaryDirectory(prefix="embedded-workspace-") as temporary:
            destination = Path(temporary).resolve() / "learner"
            destination.mkdir()
            sentinel = destination / "sentinel.txt"
            sentinel.write_text("keep-me", encoding="utf-8")
            completed = run_tool(UNIT, destination)
            self.assertNotEqual(0, completed.returncode)
            self.assertIn("destination already exists", completed.stderr)
            self.assertEqual("keep-me", sentinel.read_text(encoding="utf-8"))

    def test_source_outside_root_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory(prefix="embedded-workspace-") as temporary:
            parent = Path(temporary).resolve()
            outside = parent / "outside"
            (outside / "starter").mkdir(parents=True)
            (outside / "README.md").write_text("# outside\n", encoding="utf-8")
            (outside / "starter/input.txt").write_text("input", encoding="utf-8")
            completed = run_tool(outside, parent / "learner")
            self.assertNotEqual(0, completed.returncode)
            self.assertIn("source must stay under the guide root", completed.stderr)

    def test_symlink_source_alias_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory(prefix="embedded-workspace-") as temporary:
            parent = Path(temporary).resolve()
            alias = parent / "source-alias"
            alias.symlink_to(UNIT, target_is_directory=True)
            completed = run_tool(alias, parent / "learner")
            self.assertNotEqual(0, completed.returncode)
            self.assertIn("source path must not traverse symlink aliases", completed.stderr)

    def test_symlink_destination_parent_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory(prefix="embedded-workspace-") as temporary:
            parent = Path(temporary).resolve()
            real_parent = parent / "real"
            real_parent.mkdir()
            alias = parent / "alias"
            alias.symlink_to(real_parent, target_is_directory=True)
            completed = run_tool(UNIT, alias / "learner")
            self.assertNotEqual(0, completed.returncode)
            self.assertIn("destination parent must not traverse symlinks", completed.stderr)
            self.assertFalse((real_parent / "learner").exists())

    def test_missing_destination_parent_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory(prefix="embedded-workspace-") as temporary:
            destination = Path(temporary).resolve() / "missing" / "learner"
            completed = run_tool(UNIT, destination)
            self.assertNotEqual(0, completed.returncode)
            self.assertIn("destination parent must already exist", completed.stderr)

    def test_concurrent_creators_have_one_owner_and_preserve_starter(self) -> None:
        with tempfile.TemporaryDirectory(prefix="embedded-workspace-") as temporary:
            parent = Path(temporary).resolve()
            destination = parent / "learner"
            gate = parent / "gate"
            gate.mkdir()
            python_wrapper = parent / "gated-python"
            python_wrapper.write_text(
                """#!/bin/sh
output=$("$RACE_REAL_PYTHON" "$@")
status=$?
test "$status" -eq 0 || exit "$status"
if test "${3-}" = "$RACE_DESTINATION"; then
  : > "$RACE_GATE/ready.$$"
  while test ! -e "$RACE_GATE/release"; do
    sleep 0.01
  done
fi
printf '%s\n' "$output"
""",
                encoding="utf-8",
            )
            python_wrapper.chmod(0o755)

            environment = os.environ.copy()
            environment.update(
                {
                    "PYTHONDONTWRITEBYTECODE": "1",
                    "PYTHON": str(python_wrapper),
                    "RACE_REAL_PYTHON": os.environ.get("PYTHON", "python3"),
                    "RACE_DESTINATION": str(destination),
                    "RACE_GATE": str(gate),
                }
            )
            command = [str(SCRIPT), str(UNIT), str(destination)]
            processes = [
                subprocess.Popen(
                    command,
                    cwd=ROOT,
                    env=environment,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                )
                for _ in range(2)
            ]
            results: list[tuple[int, str, str]] = []
            try:
                deadline = time.monotonic() + 10
                while len(list(gate.glob("ready.*"))) != 2:
                    if time.monotonic() >= deadline:
                        self.fail("concurrent creators did not reach the ownership barrier")
                    time.sleep(0.01)
                (gate / "release").touch()
                for process in processes:
                    stdout, stderr = process.communicate(timeout=15)
                    results.append((process.returncode, stdout, stderr))
            finally:
                for process in processes:
                    if process.poll() is None:
                        process.kill()
                        process.communicate()

            winners = [result for result in results if result[0] == 0]
            losers = [result for result in results if result[0] != 0]
            self.assertEqual(1, len(winners), results)
            self.assertEqual(1, len(losers), results)
            self.assertIn("CREATED", winners[0][1])
            self.assertRegex(
                losers[0][2],
                r"destination (?:was created concurrently|already exists)",
            )
            starter_sentinel = (UNIT / "starter/submission.json").read_bytes()
            self.assertEqual(
                starter_sentinel,
                (destination / "submission.json").read_bytes(),
                "the losing creator must not remove or replace the winner's starter",
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
