from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from coding_agent.capstone import FixtureCapstone
from coding_agent.runtime import InjectedCrash


GUIDE_ROOT = Path(__file__).resolve().parents[3]
TASKS = ("token-expiry-boundary", "dry-run-multifile", "refresh-token-race")


def git_status(repository: Path) -> str:
    completed = subprocess.run(
        ["git", "-C", str(repository), "status", "--short"],
        text=True,
        capture_output=True,
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError(completed.stderr)
    return completed.stdout


class CapstoneContractTest(unittest.TestCase):
    def setUp(self) -> None:
        self.capstone = FixtureCapstone(GUIDE_ROOT)

    def test_all_three_tasks_complete_with_external_evidence(self) -> None:
        for task_id in TASKS:
            with self.subTest(task=task_id), tempfile.TemporaryDirectory() as raw:
                session = Path(raw) / "session"
                result = self.capstone.run(session, task_id=task_id)
                self.assertEqual(result.state, "SUCCEEDED", result)
                self.assertTrue(result.verification["passed"])
                self.assertTrue(result.verification["behavior"])
                self.assertTrue(result.verification["regression"])
                self.assertTrue(result.verification["policy"])
                self.assertTrue(result.verification["evidence"])

                manifest = json.loads((session / "session.json").read_text(encoding="utf-8"))
                source = Path(manifest["source"])
                self.assertEqual(git_status(source), "?? USER-NOTES.txt\n")
                self.assertEqual((source / "USER-NOTES.txt").read_text(encoding="utf-8"),
                                 "pre-existing user note; the agent must preserve this file\n")
                self.assertTrue(self.capstone.diff(session))

                exported = Path(raw) / "exported"
                self.capstone.export(session, exported)
                self.assertTrue((exported / "agent.patch").is_file())
                self.assertTrue((exported / "events.jsonl").is_file())
                self.assertTrue((exported / "evaluation-report.json").is_file())

    def test_crash_after_patch_resumes_without_duplicate_effect(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            session = Path(raw) / "session"
            with self.assertRaises(InjectedCrash):
                self.capstone.run(
                    session,
                    task_id="token-expiry-boundary",
                    crash_after_effect="apply_patch",
                )
            worktree = Path(json.loads((session / "session.json").read_text(encoding="utf-8"))["worktree"])
            self.assertIn("return expires_at > now", (worktree / "app" / "tokens.py").read_text(encoding="utf-8"))

            result = self.capstone.run(session, resume=True)
            self.assertEqual(result.state, "SUCCEEDED")
            ledger = json.loads((session / "state" / "tool-operations.json").read_text(encoding="utf-8"))
            applied = ledger["operations"]["effect-apply-001"]
            self.assertEqual(applied["status"], "COMPLETED")
            journals = list((session / "state" / "patch-journal").glob("*.json"))
            self.assertEqual(len(journals), 1)

    def test_cancel_and_status_are_control_plane_operations(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            session = Path(raw) / "session"
            self.capstone.create("token-expiry-boundary", session)
            cancelled = self.capstone.cancel(session)
            self.assertEqual(cancelled["status"], "CANCEL_REQUESTED")
            self.assertTrue(Path(cancelled["marker"]).is_file())


if __name__ == "__main__":
    unittest.main()
