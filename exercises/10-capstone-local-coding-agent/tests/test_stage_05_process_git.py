from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path

from coding_agent.errors import OperationConflict, PolicyDenied
from coding_agent.git_adapter import GitAdapter
from coding_agent.process import CommandCatalog, CommandSpec, ProcessRunner
from coding_agent.types import CommandRequest


FIXTURES = Path(__file__).parents[1] / "fixtures" / "process"


class ProcessRunnerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.workspace = Path(self.temporary.name) / "workspace"
        self.workspace.mkdir()

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def request(
        self,
        command_id: str,
        argv: tuple[str, ...],
        *,
        timeout: float = 2.0,
        max_output: int = 100_000,
    ) -> CommandRequest:
        return CommandRequest(command_id, argv, ".", {}, timeout, max_output, "deny")

    def runner_for(self, command_id: str, argv: tuple[str, ...]) -> ProcessRunner:
        return ProcessRunner(self.workspace, catalog=CommandCatalog((CommandSpec(command_id, argv),)))

    def test_stdout_stderr_unicode_replacement_and_nonzero_are_distinct(self) -> None:
        argv = (sys.executable, str(FIXTURES / "emit.py"), "7")
        runner = self.runner_for("emit", argv)
        result = runner.run(self.request("emit", argv))
        self.assertEqual(result.exit_kind, "NONZERO")
        self.assertEqual(result.exit_code, 7)
        self.assertIn("stdout: 안녕", result.stdout)
        self.assertIn("�", result.stdout)
        self.assertIn("stderr: fixture", result.stderr)
        self.assertEqual(result.cleanup_status, "CLEAN")

    def test_catalog_rejects_same_id_with_different_arguments_and_publishes_digests(self) -> None:
        argv = (sys.executable, str(FIXTURES / "emit.py"), "0")
        catalog = CommandCatalog((CommandSpec("emit", argv),))
        self.assertTrue(catalog.digest.startswith("sha256:"))
        self.assertTrue(catalog.entry_digest("emit").startswith("sha256:"))
        with self.assertRaises(PolicyDenied):
            catalog.validate(self.request("emit", (*argv[:-1], "1")))

    def test_timeout_terminates_descendant_process_group(self) -> None:
        pid_file = self.workspace / "child.pid"
        argv = (sys.executable, str(FIXTURES / "child_tree.py"), "parent", str(pid_file))
        runner = self.runner_for("tree", argv)
        result = runner.run(self.request("tree", argv, timeout=0.25))
        self.assertEqual(result.exit_kind, "TIMEOUT")
        self.assertIn(result.cleanup_status, {"TERMINATED", "KILLED"})
        deadline = time.monotonic() + 1
        while pid_file.exists() and time.monotonic() < deadline:
            time.sleep(0.01)
        self.assertFalse(pid_file.exists(), "child SIGTERM handler did not run")

    def test_cancel_and_output_limit_do_not_deadlock_pipe_draining(self) -> None:
        flood_argv = (sys.executable, str(FIXTURES / "output_flood.py"))
        flood = self.runner_for("flood", flood_argv).run(
            self.request("flood", flood_argv, max_output=4_096)
        )
        self.assertEqual(flood.exit_kind, "SUCCESS")
        self.assertTrue(flood.truncated)
        self.assertLessEqual(len(flood.stdout.encode()) + len(flood.stderr.encode()), 4_096)

        pid_file = self.workspace / "cancel-child.pid"
        tree_argv = (sys.executable, str(FIXTURES / "child_tree.py"), "parent", str(pid_file))
        runner = self.runner_for("cancel-tree", tree_argv)
        result_holder: list[object] = []
        thread = threading.Thread(
            target=lambda: result_holder.append(runner.run(self.request("cancel-tree", tree_argv, timeout=5))),
        )
        thread.start()
        deadline = time.monotonic() + 2
        while not pid_file.exists() and time.monotonic() < deadline:
            time.sleep(0.01)
        self.assertTrue(runner.cancel("cancel-tree"))
        thread.join(timeout=3)
        self.assertFalse(thread.is_alive())
        self.assertEqual(result_holder[0].exit_kind, "CANCELLED")

    def test_workspace_mutation_changes_receipt_digest(self) -> None:
        target = self.workspace / "created.txt"
        argv = (sys.executable, str(FIXTURES / "mutate.py"), str(target), "value")
        result = self.runner_for("mutate", argv).run(self.request("mutate", argv))
        self.assertEqual(result.exit_kind, "SUCCESS")
        self.assertNotEqual(result.workspace_before, result.workspace_after)
        self.assertEqual(target.read_text(encoding="utf-8"), "value")

    def test_successful_parent_may_not_leave_a_background_child(self) -> None:
        marker = self.workspace / "background.pid"
        argv = (sys.executable, str(FIXTURES / "background_child.py"), "parent", str(marker))
        result = self.runner_for("background", argv).run(self.request("background", argv))
        self.assertEqual(result.exit_kind, "SUCCESS")
        self.assertIn(result.cleanup_status, {"TERMINATED", "KILLED"})
        deadline = time.monotonic() + 1
        while marker.exists() and time.monotonic() < deadline:
            time.sleep(0.01)
        self.assertFalse(marker.exists())


class GitAdapterTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.base = Path(self.temporary.name)
        self.repo = self.base / "repo"
        self.repo.mkdir()
        self.git("init", "-q")
        self.git("config", "user.name", "Fixture")
        self.git("config", "user.email", "fixture@example.invalid")
        (self.repo / "tracked.txt").write_text("base\n", encoding="utf-8")
        self.git("add", "tracked.txt")
        self.git("commit", "-qm", "base")

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def git(self, *arguments: str) -> str:
        return subprocess.run(
            ("git", "-C", str(self.repo), *arguments),
            check=True,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        ).stdout

    def test_snapshot_and_detached_worktree_preserve_original_dirty_state(self) -> None:
        (self.repo / "tracked.txt").write_text("user dirty\n", encoding="utf-8")
        (self.repo / "untracked.txt").write_text("user untracked\n", encoding="utf-8")
        adapter = GitAdapter(self.repo)
        before = adapter.snapshot()
        self.assertEqual(before.unstaged, ("tracked.txt",))
        self.assertEqual(before.untracked, ("untracked.txt",))
        destination = self.base / "agent-worktree"
        receipt = adapter.create_worktree(destination)
        self.assertEqual(receipt["source_snapshot_id"], before.snapshot_id)
        self.assertEqual(adapter.snapshot(), before)
        self.assertEqual((self.repo / "tracked.txt").read_text(encoding="utf-8"), "user dirty\n")
        self.assertFalse((destination / "untracked.txt").exists())
        adapter.remove_worktree(destination)
        self.assertFalse(destination.exists())

    def test_refuses_to_remove_dirty_agent_worktree(self) -> None:
        adapter = GitAdapter(self.repo)
        destination = self.base / "dirty-worktree"
        adapter.create_worktree(destination)
        (destination / "tracked.txt").write_text("agent dirty\n", encoding="utf-8")
        with self.assertRaises(OperationConflict):
            adapter.remove_worktree(destination)
        self.assertTrue(destination.exists())


if __name__ == "__main__":
    unittest.main()
