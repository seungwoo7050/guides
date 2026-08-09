from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from coding_agent.budget import BudgetLedger
from coding_agent.checkpoint import CheckpointStore, OperationLedger
from coding_agent.errors import BudgetExceeded, ContractError, OperationConflict
from coding_agent.trace import EventLog, redact
from coding_agent.types import RunBudget


class DurableContractTest(unittest.TestCase):
    def test_budget_reserves_before_an_effect(self) -> None:
        ledger = BudgetLedger(RunBudget(max_steps=1, max_tool_calls=1, max_writes=0))
        ledger.reserve_step()
        with self.assertRaises(BudgetExceeded):
            ledger.reserve_step()
        with self.assertRaises(BudgetExceeded):
            ledger.reserve_tool_call(writes=1)
        self.assertEqual(ledger.budget.tool_calls, 0)

    def test_redaction_preserves_usage_but_removes_credentials(self) -> None:
        value = redact(
            {
                "input_tokens": 13,
                "access_token": "do-not-log",
                "message": "api_key=fixture-key",
            }
        )
        self.assertEqual(value["input_tokens"], 13)
        self.assertEqual(value["access_token"], "[REDACTED]")
        self.assertNotIn("fixture-key", value["message"])

    def test_checkpoint_and_trace_detect_tampering(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            log = EventLog(root / "events.jsonl", session_id="session-test")
            log.append("CREATED", {"safe": True})
            checkpoint = CheckpointStore(root / "checkpoint.json")
            checkpoint.save({"status": "RUNNING"}, event_head=log.head)
            self.assertEqual(checkpoint.load()["state"]["status"], "RUNNING")

            envelope = json.loads((root / "checkpoint.json").read_text(encoding="utf-8"))
            envelope["body"]["state"]["status"] = "SUCCEEDED"
            (root / "checkpoint.json").write_text(json.dumps(envelope), encoding="utf-8")
            with self.assertRaises(ContractError):
                checkpoint.load()

            text = (root / "events.jsonl").read_text(encoding="utf-8").replace("CREATED", "FORGED")
            (root / "events.jsonl").write_text(text, encoding="utf-8")
            with self.assertRaises(ContractError):
                EventLog(root / "events.jsonl", session_id="session-test")

    def test_operation_ids_are_idempotent_and_input_bound(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            ledger = OperationLedger(Path(raw) / "operations.json")
            first = ledger.begin("op-1", fingerprint="a", details={"patch": "p1"})
            duplicate = ledger.begin("op-1", fingerprint="a", details={"patch": "p1"})
            self.assertEqual(first, duplicate)
            with self.assertRaises(OperationConflict):
                ledger.begin("op-1", fingerprint="different", details={"patch": "p2"})
            ledger.complete("op-1", receipt={"status": "APPLIED"})
            self.assertEqual(ledger.lookup("op-1")["status"], "COMPLETED")


if __name__ == "__main__":
    unittest.main()
