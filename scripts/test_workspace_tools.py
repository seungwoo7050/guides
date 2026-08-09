#!/usr/bin/env python3
from __future__ import annotations

import contextlib
import io
import json
import os
import shutil
import signal
import subprocess
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest import mock

import exercise_tool


class WorkspaceToolTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="guide-workspace-tool-test-")
        self.root = Path(self.temporary.name)
        self.original_root = exercise_tool.ROOT
        exercise_tool.ROOT = self.root

    def tearDown(self) -> None:
        exercise_tool.ROOT = self.original_root
        self.temporary.cleanup()

    def exercise(self, name: str = "sample") -> tuple[str, Path, dict[str, dict]]:
        relative = f"exercises/{name}"
        path = self.root / relative
        skeleton = path / "skeleton"
        skeleton.mkdir(parents=True)
        solution = skeleton / "solution.py"
        solution.write_text("VALUE = 1\n", encoding="utf-8")
        return relative, path, {relative: {"path": relative, "kind": "code"}}

    def assert_no_internal_artifacts(self, path: Path) -> None:
        self.assertFalse((path / ".workspace-create.lock").exists())
        self.assertEqual(list(path.glob(".workspace-staging-*")), [])

    def create_silently(self, relative: str, items: dict[str, dict]) -> None:
        with contextlib.redirect_stdout(io.StringIO()):
            exercise_tool.command_new(relative, items)

    def test_nested_symlink_and_fifo_are_rejected(self) -> None:
        relative, path, items = self.exercise("unsafe-symlink")
        nested = path / "skeleton" / "nested"
        nested.mkdir()
        (nested / "link").symlink_to(self.root / "outside")
        with self.assertRaises(exercise_tool.ExerciseError):
            self.create_silently(relative, items)
        self.assertFalse((path / "workspace").exists())
        self.assert_no_internal_artifacts(path)

        if hasattr(os, "mkfifo"):
            relative, path, items = self.exercise("unsafe-fifo")
            nested = path / "skeleton" / "nested"
            nested.mkdir()
            os.mkfifo(nested / "pipe")
            with self.assertRaises(exercise_tool.ExerciseError):
                self.create_silently(relative, items)
            self.assertFalse((path / "workspace").exists())
            self.assert_no_internal_artifacts(path)

    def test_existing_file_directory_and_dangling_symlink_are_untouched(self) -> None:
        relative, path, items = self.exercise("existing-file")
        workspace = path / "workspace"
        workspace.write_text("owner-data", encoding="utf-8")
        with self.assertRaises(exercise_tool.ExerciseError):
            self.create_silently(relative, items)
        self.assertEqual(workspace.read_text(encoding="utf-8"), "owner-data")
        self.assert_no_internal_artifacts(path)

        relative, path, items = self.exercise("existing-directory")
        workspace = path / "workspace"
        workspace.mkdir()
        (workspace / "owner").write_text("keep", encoding="utf-8")
        with self.assertRaises(exercise_tool.ExerciseError):
            self.create_silently(relative, items)
        self.assertEqual((workspace / "owner").read_text(encoding="utf-8"), "keep")
        self.assert_no_internal_artifacts(path)

        relative, path, items = self.exercise("existing-dangling-link")
        workspace = path / "workspace"
        workspace.symlink_to(path / "missing-target")
        with self.assertRaises(exercise_tool.ExerciseError):
            self.create_silently(relative, items)
        self.assertTrue(workspace.is_symlink())
        self.assertEqual(os.readlink(workspace), str(path / "missing-target"))
        self.assert_no_internal_artifacts(path)

    def test_racing_destination_is_not_overwritten(self) -> None:
        relative, path, items = self.exercise("racing-destination")
        real_rename = exercise_tool.rename_noreplace

        def race(source: Path, target: Path) -> None:
            target.mkdir()
            (target / "owner").write_text("racer", encoding="utf-8")
            real_rename(source, target)

        with mock.patch.object(exercise_tool, "rename_noreplace", side_effect=race):
            with self.assertRaises(exercise_tool.ExerciseError):
                self.create_silently(relative, items)
        self.assertEqual((path / "workspace" / "owner").read_text(encoding="utf-8"), "racer")
        self.assert_no_internal_artifacts(path)

    def test_concurrent_creators_publish_once(self) -> None:
        relative, path, items = self.exercise("concurrent")
        barrier = threading.Barrier(2)
        outcomes: list[str] = []

        def create() -> None:
            barrier.wait()
            try:
                exercise_tool.command_new(relative, items)
            except exercise_tool.ExerciseError:
                outcomes.append("rejected")
            else:
                outcomes.append("created")

        threads = [threading.Thread(target=create) for _ in range(2)]
        with mock.patch("builtins.print"):
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join(timeout=5)
        self.assertEqual(sorted(outcomes), ["created", "rejected"])
        self.assertEqual((path / "workspace" / "solution.py").read_text(encoding="utf-8"), "VALUE = 1\n")
        self.assert_no_internal_artifacts(path)

    def test_interrupted_copy_cleans_owned_staging_and_lock(self) -> None:
        relative, path, items = self.exercise("interrupted")

        def interrupt_copy(source: Path, target: Path, **_: object) -> None:
            (target / "partial").write_text("partial", encoding="utf-8")
            raise KeyboardInterrupt

        with mock.patch.object(exercise_tool.shutil, "copytree", side_effect=interrupt_copy):
            with self.assertRaises(KeyboardInterrupt):
                self.create_silently(relative, items)
        self.assertFalse((path / "workspace").exists())
        self.assert_no_internal_artifacts(path)

    def test_sigterm_during_hold_cleans_owned_staging_and_lock(self) -> None:
        if not hasattr(signal, "SIGTERM"):
            self.skipTest("SIGTERM is unavailable")
        relative, path, items = self.exercise("signal-interrupted")

        def hold(_exercise: Path, _staging: Path) -> None:
            os.kill(os.getpid(), signal.SIGTERM)
            time.sleep(1)

        previous = signal.getsignal(signal.SIGTERM)
        with mock.patch.object(exercise_tool, "_WORKSPACE_HOLD_HOOK", side_effect=hold):
            with self.assertRaises(exercise_tool.WorkspaceInterrupted):
                self.create_silently(relative, items)
        self.assertIs(signal.getsignal(signal.SIGTERM), previous)
        self.assertFalse((path / "workspace").exists())
        self.assert_no_internal_artifacts(path)

    def test_replaced_lock_is_left_untouched(self) -> None:
        relative, path, items = self.exercise("replaced-lock")
        replacement = "other-owner"

        def replace_lock(source: Path, target: Path, **_: object) -> None:
            lock = path / ".workspace-create.lock"
            lock.unlink()
            lock.write_text(replacement, encoding="utf-8")
            raise RuntimeError("copy failed")

        with mock.patch.object(exercise_tool.shutil, "copytree", side_effect=replace_lock):
            with self.assertRaises(exercise_tool.ExerciseError):
                self.create_silently(relative, items)
        self.assertEqual((path / ".workspace-create.lock").read_text(encoding="utf-8"), replacement)

    def test_modes_and_source_bytes_are_preserved(self) -> None:
        relative, path, items = self.exercise("modes")
        nested = path / "skeleton" / "nested"
        nested.mkdir()
        script = nested / "run.sh"
        script.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
        nested.chmod(0o711)
        script.chmod(0o751)
        source_fingerprint = exercise_tool.tree_fingerprint(path / "skeleton")
        self.create_silently(relative, items)
        workspace = path / "workspace"
        self.assertEqual(exercise_tool.tree_fingerprint(workspace), source_fingerprint)
        self.assertEqual(workspace.joinpath("nested").stat().st_mode & 0o777, 0o711)
        self.assertEqual(workspace.joinpath("nested/run.sh").stat().st_mode & 0o777, 0o751)
        self.assert_no_internal_artifacts(path)

    def test_strict_path_spelling(self) -> None:
        for raw in (" exercises/x", "exercises/x ", "exercises//x", "exercises/./x", "exercises/../x", "exercises\\x", "exercises/\x00x"):
            with self.subTest(raw=raw), self.assertRaises(exercise_tool.ExerciseError):
                exercise_tool.contained_path(self.root, raw, label="test")

    def test_capstone_template_and_completed_submission_are_distinct(self) -> None:
        capstone = self.root / "exercises/capstone"
        capstone.mkdir(parents=True)
        (capstone / "rubric.json").write_text(
            json.dumps(
                {
                    "required_artifacts": ["design.md", "submission.json"],
                    "criteria": ["human review"],
                    "reference_implementation": False,
                }
            ),
            encoding="utf-8",
        )
        template = capstone / "skeleton"
        template.mkdir()
        (template / "design.md").write_text("# Design\n", encoding="utf-8")
        (template / "submission.json").write_text(
            json.dumps(
                {
                    "implementation_profile": "TODO",
                    "run_command": "TODO",
                    "verify_command": "TODO",
                    "input_fixture": "TODO",
                    "output_location": "TODO",
                    "known_limits": [],
                }
            ),
            encoding="utf-8",
        )
        with contextlib.redirect_stdout(io.StringIO()):
            exercise_tool.capstone_check(capstone, template, template=True)
        with self.assertRaises(exercise_tool.ExerciseError):
            exercise_tool.capstone_check(capstone, template, template=False)

        complete = capstone / "complete"
        shutil.copytree(template, complete)
        (complete / "submission.json").write_text(
            json.dumps(
                {
                    "implementation_profile": "local-python",
                    "run_command": "python pipeline.py",
                    "verify_command": "python verify.py",
                    "input_fixture": "fixtures/input.json",
                    "output_location": "output/snapshot",
                    "known_limits": ["local model only"],
                }
            ),
            encoding="utf-8",
        )
        with contextlib.redirect_stdout(io.StringIO()):
            exercise_tool.capstone_check(capstone, complete, template=False)
        with self.assertRaises(exercise_tool.ExerciseError):
            exercise_tool.capstone_check(capstone, complete, template=True)

    def test_check_workspace_rejects_extra_argument(self) -> None:
        wrapper = Path(__file__).with_name("check-workspace.sh")
        result = subprocess.run(
            [str(wrapper), "exercises/a", "exercises/b"],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
            timeout=3,
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("usage:", result.stdout)

    def test_semantic_failure_requires_exact_marker_and_diagnostic(self) -> None:
        valid = subprocess.CompletedProcess(
            args=[], returncode=1, stdout="GUIDE_SEMANTIC:sample: precise reason\n"
        )
        exercise_tool.require_semantic_failure(
            valid, expected="GUIDE_SEMANTIC:sample", label="known-bad"
        )

        for stdout in (
            "GUIDE_SEMANTIC:sample:\n",
            "prefix GUIDE_SEMANTIC:sample: precise reason\n",
            "GUIDE_SEMANTIC:sample: first\nGUIDE_SEMANTIC:sample: second\n",
        ):
            with self.subTest(stdout=stdout), self.assertRaises(exercise_tool.ExerciseError):
                exercise_tool.require_semantic_failure(
                    subprocess.CompletedProcess(args=[], returncode=1, stdout=stdout),
                    expected="GUIDE_SEMANTIC:sample",
                    label="known-bad",
                )


if __name__ == "__main__":
    unittest.main()
