from __future__ import annotations

import io
import json
import subprocess
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from coding_agent.capstone import FixtureCapstone
from coding_agent.cli import main as cli_main
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
                retrieval = result.verification["details"]["retrieval"]
                if task_id == "refresh-token-race":
                    self.assertTrue(retrieval["required"])
                    self.assertTrue(retrieval["authorized"])
                    self.assertTrue(retrieval["matched"])
                    self.assertEqual(retrieval["expected_citations"], retrieval["submitted_citations"])
                    self.assertTrue(retrieval["expected_citations"][0].startswith("source-ref:"))
                    self.assertIn(retrieval["receipt_id"], result.artifacts)
                else:
                    self.assertFalse(retrieval["required"])

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

    def test_crash_after_command_resumes_from_the_recorded_receipt(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            session = Path(raw) / "session"
            with self.assertRaises(InjectedCrash):
                self.capstone.run(
                    session,
                    task_id="token-expiry-boundary",
                    crash_after_effect="run_check",
                )
            ledger_path = session / "state" / "tool-operations.json"
            ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
            self.assertEqual(ledger["operations"]["effect-check-001"]["status"], "COMPLETED")

            result = self.capstone.run(session, resume=True)
            self.assertEqual(result.state, "SUCCEEDED")
            check_events = [
                event
                for event in result.events
                if event.get("type") == "TOOL_COMPLETED"
                and event.get("payload", {}).get("tool") == "run_check"
            ]
            self.assertEqual(len(check_events), 1)
            self.assertTrue(check_events[0]["payload"]["duplicate"])
            reconciled = [event for event in result.events if event.get("type") == "EFFECT_RECONCILED"]
            self.assertTrue(reconciled[-1]["payload"]["duplicate"])

    def test_budget_exhaustion_is_terminal_before_a_new_effect(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            session = Path(raw) / "session"
            manifest = dict(self.capstone.create("token-expiry-boundary", session))
            task = dict(manifest["task"])
            task["budget"] = {**dict(task["budget"]), "max_model_calls": 0}
            manifest["task"] = task
            (session / "session.json").write_text(
                json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )

            result = self.capstone.run(session)
            self.assertEqual(result.state, "BUDGET_EXHAUSTED")
            self.assertIsNone(result.verification)
            self.assertFalse(any(event.get("type") == "TOOL_COMPLETED" for event in result.events))
            exhausted = [event for event in result.events if event.get("type") == "BUDGET_EXHAUSTED"]
            self.assertEqual(len(exhausted), 1)
            self.assertIn("model-call", exhausted[0]["payload"]["message"])

    def test_cancel_and_status_are_control_plane_operations(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            session = Path(raw) / "session"
            self.capstone.create("token-expiry-boundary", session)
            cancelled = self.capstone.cancel(session)
            self.assertEqual(cancelled["status"], "CANCEL_REQUESTED")
            self.assertTrue(Path(cancelled["marker"]).is_file())
            result = self.capstone.run(session)
            self.assertEqual(result.state, "CANCELLED")
            self.assertEqual(self.capstone.status(session)["status"], "CANCELLED")
            self.assertFalse(any(event.get("type") == "TOOL_COMPLETED" for event in result.events))

    def test_all_published_cli_commands_are_executable(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            base = Path(raw)
            session = base / "resumable-session"
            output = io.StringIO()
            errors = io.StringIO()
            with redirect_stdout(output), redirect_stderr(errors):
                crashed = cli_main(
                    [
                        "run",
                        "--task-fixture",
                        "token-expiry-boundary",
                        "--session",
                        str(session),
                        "--crash-after-effect",
                        "apply_patch",
                    ]
                )
                resumed = cli_main(["resume", "--session", str(session)])
                status = cli_main(["status", "--session", str(session)])
                inspected = cli_main(["inspect", "--session", str(session)])
                diffed = cli_main(["diff", "--session", str(session)])
                exported = cli_main(
                    [
                        "export",
                        "--session",
                        str(session),
                        "--destination",
                        str(base / "exported"),
                    ]
                )

                cancel_session = base / "cancel-session"
                self.capstone.create("token-expiry-boundary", cancel_session)
                cancelled = cli_main(["cancel", "--session", str(cancel_session)])

            self.assertEqual(crashed, 75)
            self.assertEqual((resumed, status, inspected, diffed, exported, cancelled), (0, 0, 0, 0, 0, 0))
            self.assertIn('"status": "SUCCEEDED"', output.getvalue())
            self.assertIn("injected crash", errors.getvalue())
            self.assertTrue((base / "exported" / "agent.patch").is_file())


if __name__ == "__main__":
    unittest.main()
