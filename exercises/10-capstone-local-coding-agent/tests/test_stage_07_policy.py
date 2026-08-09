from __future__ import annotations

import datetime as dt
import sys
import tempfile
import unittest
from pathlib import Path

from coding_agent.errors import ApprovalRequired, OperationConflict, PolicyDenied
from coding_agent.patching import PatchEngine
from coding_agent.policy import ApprovalStore, PolicyEngine
from coding_agent.process import CommandCatalog, CommandSpec, ProcessRunner
from coding_agent.tools import ToolGateway
from coding_agent.types import Approval, Grant, PatchOperation, ToolRequest
from coding_agent.util import sha256_bytes


def future(minutes: int = 10) -> str:
    return (dt.datetime.now(dt.timezone.utc) + dt.timedelta(minutes=minutes)).isoformat()


class PolicyAndGatewayTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.base = Path(self.temporary.name)
        self.workspace = self.base / "workspace"
        self.workspace.mkdir()
        (self.workspace / "src").mkdir()
        (self.workspace / "src/app.py").write_text("answer = 1\n", encoding="utf-8")
        (self.workspace / ".env").write_text("TOKEN=fake-fixture\n", encoding="utf-8")
        self.store = ApprovalStore(self.base / "authority" / "approvals.json")
        self.grant = Grant(
            grant_id="task-grant",
            principal="agent:test",
            purpose="fix-task",
            read_paths=(".",),
            write_paths=("src",),
            command_ids=("check",),
            knowledge_scopes=("public-docs",),
            network="deny",
            expires_at=future(),
        )
        self.policy = PolicyEngine(self.workspace, grants=(self.grant,), approval_store=self.store)
        self.patch_engine = PatchEngine(self.workspace, journal_dir=self.base / "patch-journal")

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def make_artifact(self, content: str = "answer = 2\n"):
        target = self.workspace / "src/app.py"
        return self.patch_engine.prepare(
            "snapshot-policy",
            (PatchOperation("MODIFY", "src/app.py", sha256_bytes(target.read_bytes()), content),),
        )

    def test_path_permission_secret_deny_and_durable_revoke(self) -> None:
        self.assertEqual(self.policy.authorize_read("agent:test", "src/app.py", purpose="fix-task"), "src/app.py")
        with self.assertRaises(PolicyDenied):
            self.policy.authorize_read("agent:test", ".env", purpose="fix-task")
        with self.assertRaises(PolicyDenied):
            self.policy.authorize_write("agent:test", "README.md", purpose="fix-task")
        self.policy.revoke("task-grant")
        restarted = PolicyEngine(self.workspace, grants=(self.grant,), approval_store=ApprovalStore(self.store.path))
        with self.assertRaises(PolicyDenied):
            restarted.authorize_read("agent:test", "src/app.py", purpose="fix-task")

    def test_exact_approval_binds_principal_patch_digest_operation_and_is_one_shot(self) -> None:
        artifact = self.make_artifact()
        approval = Approval(
            approval_id="approve-exact",
            principal="agent:test",
            patch_id=artifact.patch_id,
            patch_digest=artifact.digest,
            expires_at=future(),
            operation_id="apply-1",
        )
        self.store.add(approval)
        with self.assertRaises(ApprovalRequired):
            self.policy.authorize_patch(
                "agent:test", artifact, approval_id="approve-exact", operation_id="other", purpose="fix-task"
            )
        consumed = self.policy.authorize_patch(
            "agent:test", artifact, approval_id="approve-exact", operation_id="apply-1", purpose="fix-task"
        )
        self.assertTrue(consumed.used)
        with self.assertRaises(ApprovalRequired):
            self.policy.authorize_patch(
                "agent:test", artifact, approval_id="approve-exact", operation_id="apply-1", purpose="fix-task"
            )

    def test_expired_approval_and_network_command_are_denied(self) -> None:
        artifact = self.make_artifact()
        self.store.add(
            Approval(
                "expired",
                "agent:test",
                artifact.patch_id,
                artifact.digest,
                (dt.datetime.now(dt.timezone.utc) - dt.timedelta(seconds=1)).isoformat(),
            )
        )
        with self.assertRaises(ApprovalRequired):
            self.policy.authorize_patch("agent:test", artifact, approval_id="expired", operation_id=None)
        with self.assertRaises(PolicyDenied):
            self.policy.authorize_command("agent:test", "check", argv=("curl", "https://example.invalid"))
        with self.assertRaises(PolicyDenied):
            self.policy.authorize_command("agent:test", "unregistered", argv=(sys.executable, "-V"))

    def test_gateway_authorizes_retrieval_before_call_and_applies_exact_patch_idempotently(self) -> None:
        calls: list[tuple[str, tuple[str, ...], int]] = []

        def knowledge(query: str, scopes, limit: int):
            calls.append((query, tuple(scopes), limit))
            return ({"source_id": "doc-1", "text": "bounded evidence"},)

        check_argv = (sys.executable, "-c", "print('ok')")
        catalog = CommandCatalog((CommandSpec("check", check_argv),))
        gateway = ToolGateway(
            self.workspace,
            policy=self.policy,
            patch_engine=self.patch_engine,
            process_runner=ProcessRunner(self.workspace, catalog=catalog),
            knowledge_search=knowledge,
            state_dir=self.base / "gateway-state",
        )
        result = gateway.invoke(
            ToolRequest(
                "knowledge-1",
                "agent:test",
                "search_knowledge",
                {"query": "limits", "scopes": ["public-docs"], "limit": 3},
            )
        )
        self.assertEqual(result.status, "OK")
        self.assertEqual(calls, [("limits", ("public-docs",), 3)])
        with self.assertRaises(PolicyDenied):
            gateway.invoke(
                ToolRequest("knowledge-2", "agent:test", "search_knowledge", {"query": "secret", "scopes": ["hidden"]})
            )
        self.assertEqual(len(calls), 1, "provider was called before scope authorization")

        prepared = gateway.invoke(
            ToolRequest(
                "prepare-1",
                "agent:test",
                "prepare_patch",
                {
                    "operations": [
                        {
                            "kind": "MODIFY",
                            "path": "src/app.py",
                            "before_digest": sha256_bytes((self.workspace / "src/app.py").read_bytes()),
                            "content": "answer = 42\n",
                        }
                    ]
                },
            )
        )
        artifact = prepared.output["artifact"]
        self.store.add(
            Approval(
                "gateway-approval",
                "agent:test",
                artifact["patch_id"],
                artifact["digest"],
                future(),
                operation_id="apply-operation",
            )
        )
        request = ToolRequest(
            "apply-1",
            "agent:test",
            "apply_patch",
            {"patch_id": artifact["patch_id"]},
            operation_id="apply-operation",
            approval_id="gateway-approval",
        )
        first = gateway.invoke(request)
        second = gateway.invoke(request)
        self.assertFalse(first.duplicate)
        self.assertTrue(second.duplicate)
        self.assertEqual((self.workspace / "src/app.py").read_text(encoding="utf-8"), "answer = 42\n")
        with self.assertRaises(OperationConflict):
            gateway.invoke(
                ToolRequest(
                    "apply-conflict",
                    "agent:test",
                    "apply_patch",
                    {"patch_id": "different"},
                    operation_id="apply-operation",
                    approval_id="gateway-approval",
                )
            )

        checked = gateway.invoke(
            ToolRequest(
                "check-1",
                "agent:test",
                "run_check",
                {"check_id": "check"},
                operation_id="check-operation",
            )
        )
        self.assertEqual(checked.output["exit_kind"], "SUCCESS")
        self.assertEqual(checked.output["catalog_entry_digest"], catalog.entry_digest("check"))
        self.assertEqual(checked.output["network_enforcement"], "CATALOG_POLICY_ONLY")


if __name__ == "__main__":
    unittest.main()
