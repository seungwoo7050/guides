from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from coding_agent.evaluation import ExternalEvaluator, materialize_task
from evaluator.solutions import install_known_good


FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "tasks"


def evidence_for(task: dict) -> tuple[dict, ...]:
    events: list[dict] = [
        {"type": "USER_INPUT_RECEIVED", "payload": {}},
        {"type": "TOOL_COMPLETED", "payload": {"tool": "apply_patch"}},
        {"type": "TOOL_COMPLETED", "payload": {"tool": "run_check"}},
        {"type": "TOOL_COMPLETED", "payload": {"tool": "show_diff"}},
    ]
    scopes = task.get("knowledge_scopes", [])
    if scopes:
        reference = {
            "source_id": "knowledge:test-authorized",
            "origin": "knowledge",
            "location": "test-authorized.json",
            "revision": "1",
            "digest": "sha256:" + "1" * 64,
            "trust": "CURATED",
            "scope": scopes[0],
            "freshness": "current",
            "retrieved_at": "2026-08-10T00:00:00+00:00",
        }
        citation_identity = {
            field: reference[field]
            for field in ("source_id", "origin", "scope", "location", "revision", "digest")
        }
        citation = "source-ref:" + json.dumps(
            citation_identity, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        )
        events.extend(
            (
                {
                    "type": "TOOL_COMPLETED",
                    "payload": {
                        "tool": "search_knowledge",
                        "receipt_id": "receipt-knowledge",
                        "status": "OK",
                        "authorized_scopes": scopes,
                        "source_refs": [reference],
                    },
                },
                {
                    "type": "MODEL_EVENT",
                    "payload": {
                        "kind": "ACTION_COMPLETE",
                        "payload": {
                            "action": {
                                "kind": "SUBMIT_RESULT",
                                "arguments": {
                                    "artifact_ids": ["receipt-knowledge"],
                                    "citations": [citation],
                                },
                            }
                        },
                    },
                },
            )
        )
    return tuple(events)


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
                events = evidence_for(task)
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
