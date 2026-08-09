from __future__ import annotations

import json
import unittest
from pathlib import Path
from unittest.mock import patch

from coding_agent.errors import ContractError
from coding_agent.model import HttpModelAdapter, ScriptedModelAdapter, parse_action
from coding_agent.types import ModelRequest
from coding_agent.util import value_digest


def action(kind: str = "REPOSITORY_STATUS", arguments: dict | None = None, action_id: str = "action-1") -> dict:
    return {
        "contract_version": "1.0",
        "action_id": action_id,
        "kind": kind,
        "arguments": arguments or {},
        "purpose": "exercise the public contract",
    }


def request(*, request_id: str = "request-1", context_items: tuple[dict, ...] = ()) -> ModelRequest:
    return ModelRequest(
        request_id=request_id,
        session_id="session-1",
        task="inspect the repository",
        instruction_blocks=(),
        context_items=context_items,
        tool_definitions=(),
    )


def event_stream(value: dict) -> list[dict]:
    return [
        {"contract_version": "1.0", "kind": "ACTION_COMPLETE", "sequence": 0, "payload": {"action": value}},
        {"contract_version": "1.0", "kind": "COMPLETED", "sequence": 1, "payload": {"finish_reason": "action"}},
    ]


class ActionContractTest(unittest.TestCase):
    def test_public_action_shapes_are_strict(self) -> None:
        knowledge = parse_action(
            action("SEARCH_KNOWLEDGE", {"query": "network policy", "scopes": ["agent-runtime"], "limit": 5})
        )
        self.assertEqual(knowledge.arguments["limit"], 5)
        apply = parse_action(
            action(
                "APPLY_PATCH",
                {"patch_id": "patch-1", "approval_id": "approval-1", "operation_id": "operation-1"},
            )
        )
        self.assertEqual(apply.arguments["approval_id"], "approval-1")
        submit = parse_action(
            action(
                "SUBMIT_RESULT",
                {"artifact_ids": ["receipt-1"], "summary": "done", "risks": [], "citations": ["repo:a.py#L1"]},
            )
        )
        self.assertEqual(submit.arguments["artifact_ids"], ["receipt-1"])

    def test_unknown_missing_and_dead_actions_are_rejected(self) -> None:
        with self.assertRaises(ContractError):
            parse_action({**action(), "unexpected": True})
        with self.assertRaises(ContractError):
            parse_action(action("RUN_CHECK", {"check_id": "unit"}))
        with self.assertRaises(ContractError):
            parse_action(action("RUN_COMMAND", {"command_id": "unit"}))
        with self.assertRaises(ContractError):
            parse_action(action("SUBMIT_RESULT", {"artifact_ids": [], "summary": "done", "risks": [], "citations": []}))

    def test_published_json_contracts_are_valid_json(self) -> None:
        root = Path(__file__).resolve().parents[3]
        contracts = root / "contracts"
        names = {
            "action.schema.json",
            "model-event.schema.json",
            "model-request.schema.json",
            "repository-snapshot.schema.json",
            "context-item.schema.json",
        }
        self.assertTrue(names.issubset({path.name for path in contracts.glob("*.json")}))
        for name in names:
            body = json.loads((contracts / name).read_text(encoding="utf-8"))
            self.assertEqual(body["$schema"], "https://json-schema.org/draft/2020-12/schema")


class ScriptedAdapterTest(unittest.TestCase):
    def test_success_stream_has_one_complete_action_and_terminal(self) -> None:
        adapter = ScriptedModelAdapter([action()], model_name="fixture-model")
        events = list(adapter.stream(request()))
        self.assertEqual([item.kind for item in events], ["ACTION_COMPLETE", "COMPLETED"])
        self.assertEqual([item.sequence for item in events], [0, 1])
        self.assertEqual(events[0].payload["action"]["kind"], "REPOSITORY_STATUS")

    def test_bad_sequence_late_event_and_multiple_actions_are_rejected(self) -> None:
        duplicate = event_stream(action())
        duplicate[1]["sequence"] = 2
        with self.assertRaises(ContractError):
            list(ScriptedModelAdapter([duplicate]).stream(request()))
        late = event_stream(action()) + [
            {"contract_version": "1.0", "kind": "TEXT_DELTA", "sequence": 2, "payload": {"text": "late"}}
        ]
        with self.assertRaises(ContractError):
            list(ScriptedModelAdapter([late]).stream(request()))
        multiple = [event_stream(action())[0], event_stream(action(action_id="action-2"))[0]]
        multiple[1]["sequence"] = 1
        multiple.append({"contract_version": "1.0", "kind": "COMPLETED", "sequence": 2, "payload": {}})
        with self.assertRaises(ContractError):
            list(ScriptedModelAdapter([multiple]).stream(request()))

    def test_only_the_six_public_event_kinds_are_accepted(self) -> None:
        streamed = [
            {"contract_version": "1.0", "kind": "ACTION_DELTA", "sequence": 0, "payload": {"action_id": "action-1", "delta": "{\"kind\":"}},
            {"contract_version": "1.0", "kind": "ACTION_COMPLETE", "sequence": 1, "payload": {"action": action()}},
            {"contract_version": "1.0", "kind": "COMPLETED", "sequence": 2, "payload": {}},
        ]
        self.assertEqual(
            [item.kind for item in ScriptedModelAdapter([streamed]).stream(request())],
            ["ACTION_DELTA", "ACTION_COMPLETE", "COMPLETED"],
        )
        mismatched = [dict(item) for item in streamed]
        mismatched[0] = {**mismatched[0], "payload": {"action_id": "different", "delta": "{"}}
        with self.assertRaises(ContractError):
            list(ScriptedModelAdapter([mismatched]).stream(request()))
        errored = [
            {
                "contract_version": "1.0",
                "kind": "ERROR",
                "sequence": 0,
                "payload": {"code": "PROVIDER_TIMEOUT", "message": "deadline", "retryable": True},
            }
        ]
        self.assertEqual(list(ScriptedModelAdapter([errored]).stream(request()))[0].kind, "ERROR")
        old_event = [
            {
                "contract_version": "1.0",
                "kind": "RESPONSE_START",
                "sequence": 0,
                "payload": {"request_id": "request-1"},
            }
        ]
        with self.assertRaises(ContractError):
            list(ScriptedModelAdapter([old_event]).stream(request()))

    def test_expectation_and_dynamic_receipt_placeholder(self) -> None:
        receipt = {
            "kind": "TOOL_RECEIPT",
            "tool": "prepare_patch",
            "status": "OK",
            "receipt_id": "receipt-7",
            "resource": "patch-dynamic",
            "output": {"artifact": {"patch_id": "patch-dynamic"}},
        }
        turn = {
            "expect": {
                "tool": "prepare_patch",
                "status": "OK",
                "observation_digest": value_digest(receipt),
            },
            "action": action(
                "APPLY_PATCH",
                {
                    "patch_id": "${last_tool.output.artifact.patch_id}",
                    "approval_id": "approval-7",
                    "operation_id": "${last_tool.receipt_id}-apply",
                },
            ),
        }
        events = list(ScriptedModelAdapter([turn]).stream(request(context_items=(receipt,))))
        parsed = events[0].payload["action"]
        self.assertEqual(parsed["arguments"]["patch_id"], "patch-dynamic")
        self.assertEqual(parsed["arguments"]["operation_id"], "receipt-7-apply")
        with self.assertRaises(ContractError):
            list(ScriptedModelAdapter([turn]).stream(request(context_items=({**receipt, "status": "DENIED"},))))

    def test_sequence_position_is_checkpointable(self) -> None:
        scripts = [action(action_id="action-1"), action("SHOW_DIFF", action_id="action-2")]
        first = ScriptedModelAdapter(scripts)
        list(first.stream(request()))
        self.assertEqual(first.position, 1)
        resumed = ScriptedModelAdapter(scripts)
        resumed.restore_position(first.position)
        events = list(resumed.stream(request(request_id="request-2")))
        self.assertEqual(events[0].payload["action"]["kind"], "SHOW_DIFF")
        with self.assertRaises(ContractError):
            resumed.restore_position(99)


class HttpAdapterTest(unittest.TestCase):
    def test_injected_transport_is_bounded_and_contract_checked(self) -> None:
        captured: dict = {}

        def transport(endpoint, body, headers, timeout):
            captured.update(json.loads(body))
            return {"events": event_stream(action())}

        adapter = HttpModelAdapter(
            "http://127.0.0.1:9/model",
            model_name="loopback",
            transport=transport,
        )
        events = list(adapter.stream(request()))
        self.assertEqual(events[-1].kind, "COMPLETED")
        self.assertEqual(captured["request"]["request_id"], "request-1")
        with self.assertRaises(ValueError):
            HttpModelAdapter("https://models.example/v1", model_name="remote")

    def test_default_transport_uses_a_loopback_post_without_external_network(self) -> None:
        response_body = json.dumps({"events": event_stream(action())}).encode("utf-8")

        class Response:
            status = 200
            headers = {"Content-Type": "application/json"}

            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

            def read(self):
                return response_body

        with patch("urllib.request.urlopen", return_value=Response()) as urlopen:
            events = list(
                HttpModelAdapter("http://127.0.0.1:8765/model", model_name="loopback").stream(request())
            )
            self.assertEqual(events[0].kind, "ACTION_COMPLETE")
            outgoing = urlopen.call_args.args[0]
            self.assertEqual(outgoing.method, "POST")
            self.assertEqual(json.loads(outgoing.data)["request"]["request_id"], "request-1")


if __name__ == "__main__":
    unittest.main()
