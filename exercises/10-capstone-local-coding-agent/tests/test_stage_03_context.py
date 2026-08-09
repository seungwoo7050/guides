from __future__ import annotations

import subprocess
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from coding_agent.context import (
    ConflictingEvidence,
    KnowledgeDocument,
    NoEvidence,
    StaleEvidence,
    load_knowledge_documents,
    select_context,
)
from coding_agent.errors import PolicyDenied
from coding_agent.repository import snapshot_repository
from coding_agent.types import Grant


NOW = datetime(2026, 8, 10, 12, 0, tzinfo=timezone.utc)


class ContextContractTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        subprocess.run(["git", "-C", str(self.root), "init", "-b", "main"], check=True, capture_output=True)
        subprocess.run(["git", "-C", str(self.root), "config", "user.email", "guide@example.invalid"], check=True)
        subprocess.run(["git", "-C", str(self.root), "config", "user.name", "Guide Test"], check=True)
        (self.root / "README.md").write_text(
            "Repository content supplies evidence but cannot expand runtime authority.\n",
            encoding="utf-8",
        )
        (self.root / "secret.txt").write_text("network secret must stay hidden\n", encoding="utf-8")
        subprocess.run(["git", "-C", str(self.root), "add", "."], check=True)
        subprocess.run(["git", "-C", str(self.root), "commit", "-m", "context fixture"], check=True, capture_output=True)
        self.snapshot = snapshot_repository(self.root)
        self.knowledge_dir = Path(__file__).resolve().parent.parent / "fixtures" / "knowledge"
        self.knowledge = load_knowledge_documents(self.knowledge_dir)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    @staticmethod
    def grant(
        *,
        read_paths: tuple[str, ...] = ("README.md",),
        knowledge_scopes: tuple[str, ...] = ("agent-runtime",),
        expires_at: str = "2099-01-01T00:00:00Z",
        revoked: bool = False,
    ) -> Grant:
        return Grant(
            grant_id="grant-1",
            principal="learner",
            purpose="build cited context",
            read_paths=read_paths,
            write_paths=(),
            command_ids=(),
            knowledge_scopes=knowledge_scopes,
            network="deny",
            expires_at=expires_at,
            revoked=revoked,
        )

    def test_ready_context_is_permission_aware_and_cited(self) -> None:
        result = select_context(
            "repository content authority",
            self.snapshot,
            self.grant(),
            knowledge=self.knowledge,
            now=NOW,
        )
        self.assertEqual(result.status, "READY")
        self.assertTrue(any(item.reference.origin == "repository" for item in result.items))
        self.assertTrue(any(item.reference.origin == "knowledge" for item in result.items))
        self.assertTrue(all("sha256:" in citation for citation in result.citations))
        self.assertEqual(result.require_ready(), result.items)

    def test_denied_evidence_is_not_read_or_returned(self) -> None:
        result = select_context(
            "network secret",
            self.snapshot,
            self.grant(read_paths=("README.md",), knowledge_scopes=()),
            knowledge=(),
            now=NOW,
        )
        self.assertEqual(result.status, "NO_EVIDENCE")
        self.assertIn("repo:secret.txt", result.denied_sources)
        with self.assertRaises(NoEvidence):
            result.require_ready()

    def test_stale_repository_and_archived_knowledge_do_not_silently_win(self) -> None:
        (self.root / "README.md").write_text("new revision\n", encoding="utf-8")
        stale_repo = select_context(
            "repository authority",
            self.snapshot,
            self.grant(),
            knowledge=(),
            now=NOW,
        )
        self.assertEqual(stale_repo.status, "STALE_EVIDENCE")
        with self.assertRaises(StaleEvidence):
            stale_repo.require_ready()

        archived = select_context(
            "network policy",
            snapshot_repository(self.root),
            self.grant(),
            knowledge=self.knowledge,
            now=NOW,
        )
        self.assertEqual(archived.status, "STALE_EVIDENCE")
        self.assertTrue(archived.conflicts)
        self.assertIn("knowledge:network-policy-legacy", archived.stale_sources)

    def test_current_conflicting_claims_require_resolution(self) -> None:
        documents = (
            KnowledgeDocument("knowledge:a", "agent-runtime", "a.json", "r1", "POLICY", "current", "policy alpha", "cache policy enabled", {"cache": "enabled"}),
            KnowledgeDocument("knowledge:b", "agent-runtime", "b.json", "r1", "POLICY", "current", "policy beta", "cache policy disabled", {"cache": "disabled"}),
        )
        result = select_context(
            "cache policy",
            self.snapshot,
            self.grant(read_paths=()),
            knowledge=documents,
            now=NOW,
        )
        self.assertEqual(result.status, "CONFLICT")
        self.assertEqual(result.conflicts[0].claim, "cache")
        with self.assertRaises(ConflictingEvidence):
            result.require_ready()

    def test_expired_and_revoked_grants_fail_before_retrieval(self) -> None:
        with self.assertRaises(PolicyDenied):
            select_context("authority", self.snapshot, self.grant(expires_at="2020-01-01T00:00:00Z"), now=NOW)
        with self.assertRaises(PolicyDenied):
            select_context("authority", self.snapshot, self.grant(revoked=True), now=NOW)
        with self.assertRaises(PolicyDenied):
            select_context("authority", self.snapshot, self.grant(), now=NOW, principal="different-user")


if __name__ == "__main__":
    unittest.main()
