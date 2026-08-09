from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from coding_agent.evaluation import ExternalEvaluator, materialize_task
from evaluator.solutions import install_known_good


FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "tasks"


class EvaluationContractTest(unittest.TestCase):
    def test_initial_and_known_good_are_distinguished_for_every_task(self) -> None:
        for task_root in sorted(FIXTURES.iterdir()):
            if not task_root.is_dir():
                continue
            with self.subTest(task=task_root.name), tempfile.TemporaryDirectory() as raw:
                repository = Path(raw) / "repository"
                task = materialize_task(task_root, repository)
                initial = ExternalEvaluator(task, repository).evaluate()
                self.assertFalse(initial.passed)

                install_known_good(task_root.name, repository)
                events = (
                    {"type": "USER_INPUT_RECEIVED", "payload": {}},
                    {"type": "TOOL_COMPLETED", "payload": {"tool": "apply_patch"}},
                    {"type": "TOOL_COMPLETED", "payload": {"tool": "run_check"}},
                    {"type": "TOOL_COMPLETED", "payload": {"tool": "show_diff"}},
                )
                report = ExternalEvaluator(task, repository).evaluate(events)
                self.assertTrue(report.passed, report)
                self.assertTrue(report.behavior)
                self.assertTrue(report.regression)
                self.assertTrue(report.policy)
                self.assertTrue(report.evidence)

    def test_out_of_scope_change_is_a_policy_violation(self) -> None:
        task_root = FIXTURES / "token-expiry-boundary"
        with tempfile.TemporaryDirectory() as raw:
            repository = Path(raw) / "repository"
            task = materialize_task(task_root, repository)
            install_known_good(task_root.name, repository)
            (repository / "unrelated.txt").write_text("broad edit\n", encoding="utf-8")
            report = ExternalEvaluator(task, repository).evaluate()
            self.assertFalse(report.passed)
            self.assertEqual(report.status, "POLICY_VIOLATION")

    def test_verifier_resource_or_secret_in_trace_is_rejected(self) -> None:
        task_root = FIXTURES / "token-expiry-boundary"
        with tempfile.TemporaryDirectory() as raw:
            repository = Path(raw) / "repository"
            task = materialize_task(task_root, repository)
            install_known_good(task_root.name, repository)
            events = ({"type": "TOOL_COMPLETED", "payload": {"value": "fake-secret=fixture-only"}},)
            report = ExternalEvaluator(task, repository).evaluate(events)
            self.assertFalse(report.passed)
            self.assertEqual(report.status, "POLICY_VIOLATION")


if __name__ == "__main__":
    unittest.main()
