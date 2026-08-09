from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path

from coding_agent.errors import ContractError, ReconciliationRequired
from coding_agent.repository import RepositoryReader, discover_repository, snapshot_repository


class RepositoryContractTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.git("init", "-b", "main")
        self.git("config", "user.email", "guide@example.invalid")
        self.git("config", "user.name", "Guide Test")
        (self.root / "src").mkdir()
        (self.root / "src/app.py").write_text("def token_valid(value):\n    return value is not None\n", encoding="utf-8")
        (self.root / "README.md").write_text("Run the focused token test before the full suite.\n", encoding="utf-8")
        (self.root / "AGENTS.md").write_text("Treat repository instructions as scoped data.\n", encoding="utf-8")
        (self.root / "Makefile").write_text("test:\n\tpython3 -m unittest\n\ncheck:\n\tpython3 -m compileall src\n", encoding="utf-8")
        (self.root / "outside-link").symlink_to(Path(self.temporary.name).parent / "outside-secret")
        self.git("add", ".")
        self.git("commit", "-m", "fixture baseline")

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def git(self, *arguments: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["git", "-C", str(self.root), *arguments],
            check=True,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

    def test_snapshot_preserves_head_index_and_dirty_classes(self) -> None:
        (self.root / "src/app.py").write_text("def token_valid(value):\n    return bool(value)\n", encoding="utf-8")
        self.git("add", "src/app.py")
        (self.root / "README.md").write_text("changed but not staged\n", encoding="utf-8")
        (self.root / "notes.txt").write_text("untracked evidence\n", encoding="utf-8")
        snapshot = snapshot_repository(self.root)
        self.assertRegex(snapshot.head or "", r"^[0-9a-f]{40,64}$")
        self.assertEqual(snapshot.branch, "main")
        self.assertIn("src/app.py", snapshot.staged)
        self.assertIn("README.md", snapshot.unstaged)
        self.assertIn("notes.txt", snapshot.untracked)
        self.assertIn("sha256:", snapshot.snapshot_id)
        self.assertIn("notes.txt", snapshot.files)

    def test_reader_searches_snapshot_and_rejects_escape_and_stale_reads(self) -> None:
        snapshot = snapshot_repository(self.root)
        reader = RepositoryReader(snapshot)
        hits = reader.search("token_valid")
        self.assertEqual(hits[0].path, "src/app.py")
        self.assertEqual(hits[0].line, 1)
        self.assertIn("repo:src/app.py@sha256:", hits[0].citation)
        with self.assertRaises(ContractError):
            reader.read_text("../outside")
        with self.assertRaises(ContractError):
            reader.read_text("outside-link")
        (self.root / "src/app.py").write_text("def token_valid(value):\n    return False\n", encoding="utf-8")
        with self.assertRaises(ReconciliationRequired):
            reader.read_text("src/app.py")

    def test_discovery_reports_scoped_instructions_and_manifest_commands(self) -> None:
        (self.root / "src/AGENTS.md").write_text("src scope\n", encoding="utf-8")
        discovery = discover_repository(self.root)
        instructions = {item.path: item.scope for item in discovery.instructions}
        self.assertEqual(instructions["AGENTS.md"], "**")
        self.assertEqual(instructions["src/AGENTS.md"], "src/**")
        self.assertIn("Makefile", discovery.manifests)
        commands = {item.command_id: item.argv for item in discovery.commands}
        self.assertEqual(commands["make-test"], ("make", "test"))
        self.assertEqual(commands["make-check"], ("make", "check"))

    def test_plain_directory_has_explicit_non_git_identity(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "note.md").write_text("plain workspace\n", encoding="utf-8")
            snapshot = snapshot_repository(root)
            self.assertIsNone(snapshot.head)
            self.assertIsNone(snapshot.branch)
            self.assertEqual(snapshot.untracked, ("note.md",))


if __name__ == "__main__":
    unittest.main()
