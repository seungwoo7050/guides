from __future__ import annotations

import os
import stat
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from coding_agent.errors import ContractError, OperationConflict, PolicyDenied
from coding_agent.patching import PatchEngine
from coding_agent.types import PatchOperation
from coding_agent.util import atomic_write_bytes as real_atomic_write_bytes
from coding_agent.util import sha256_bytes


class PatchEngineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.base = Path(self.temporary.name)
        self.workspace = self.base / "workspace"
        self.workspace.mkdir()
        self.journal = self.base / "journal"
        self.engine = PatchEngine(self.workspace, journal_dir=self.journal, max_file_bytes=1_024)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    @staticmethod
    def digest(path: Path) -> str:
        return sha256_bytes(path.read_bytes())

    def test_bounded_text_read_rejects_binary_large_and_symlink(self) -> None:
        (self.workspace / "ok.txt").write_text("alpha\n", encoding="utf-8")
        (self.workspace / "binary.bin").write_bytes(b"abc\x00def")
        (self.workspace / "large.log").write_bytes(b"x" * 2_000)
        outside = self.base / "outside.txt"
        outside.write_text("secret", encoding="utf-8")
        (self.workspace / "escape").symlink_to(outside)

        receipt = self.engine.read("ok.txt")
        self.assertEqual(receipt["content"], "alpha\n")
        self.assertEqual(receipt["digest"], self.digest(self.workspace / "ok.txt"))
        with self.assertRaises(PolicyDenied):
            self.engine.read("../outside.txt")
        with self.assertRaises(PolicyDenied):
            self.engine.read("escape")
        with self.assertRaises(PolicyDenied):
            self.engine.read("binary.bin")
        with self.assertRaises(PolicyDenied):
            self.engine.read("large.log")

    def test_multi_file_create_modify_delete_rename_preserves_mode_and_rolls_back(self) -> None:
        executable = self.workspace / "run.sh"
        executable.write_text("#!/bin/sh\necho old\n", encoding="utf-8")
        executable.chmod(0o755)
        obsolete = self.workspace / "obsolete.txt"
        obsolete.write_text("remove me\n", encoding="utf-8")
        old_name = self.workspace / "old-name.txt"
        old_name.write_text("rename me\n", encoding="utf-8")
        artifact = self.engine.prepare(
            "snapshot-1",
            (
                PatchOperation("MODIFY", "run.sh", self.digest(executable), "#!/bin/sh\necho new\n"),
                PatchOperation("CREATE", "tests/test_new.py", content="def test_new():\n    assert True\n"),
                PatchOperation("DELETE", "obsolete.txt", self.digest(obsolete)),
                PatchOperation("RENAME", "old-name.txt", self.digest(old_name), new_path="new-name.txt"),
            ),
            patch_id="multi-file",
        )

        receipt = self.engine.apply(artifact)
        self.assertEqual(set(receipt["changed_paths"]), {"run.sh", "tests/test_new.py", "obsolete.txt", "old-name.txt", "new-name.txt"})
        self.assertEqual(executable.read_text(encoding="utf-8"), "#!/bin/sh\necho new\n")
        self.assertEqual(stat.S_IMODE(executable.stat().st_mode), 0o755)
        self.assertFalse(obsolete.exists())
        self.assertFalse(old_name.exists())
        self.assertEqual((self.workspace / "new-name.txt").read_text(encoding="utf-8"), "rename me\n")

        rolled_back = self.engine.rollback("multi-file")
        self.assertEqual(rolled_back["status"], "ROLLED_BACK")
        self.assertEqual(executable.read_text(encoding="utf-8"), "#!/bin/sh\necho old\n")
        self.assertEqual(stat.S_IMODE(executable.stat().st_mode), 0o755)
        self.assertTrue(obsolete.exists())
        self.assertTrue(old_name.exists())
        self.assertFalse((self.workspace / "new-name.txt").exists())
        self.assertFalse((self.workspace / "tests/test_new.py").exists())

    def test_all_preconditions_are_checked_before_any_write(self) -> None:
        first = self.workspace / "first.txt"
        second = self.workspace / "second.txt"
        first.write_text("one", encoding="utf-8")
        second.write_text("two", encoding="utf-8")
        artifact = self.engine.prepare(
            "snapshot-stale",
            (
                PatchOperation("MODIFY", "first.txt", self.digest(first), "changed"),
                PatchOperation("MODIFY", "second.txt", "sha256:" + "0" * 64, "changed"),
            ),
        )
        with self.assertRaises(OperationConflict):
            self.engine.apply(artifact)
        self.assertEqual(first.read_text(encoding="utf-8"), "one")
        self.assertEqual(second.read_text(encoding="utf-8"), "two")
        self.assertEqual(list(self.journal.glob("*.json")), [])

    def test_case_colliding_targets_are_rejected_portably(self) -> None:
        with self.assertRaises(ContractError):
            self.engine.prepare(
                "snapshot-case",
                (
                    PatchOperation("CREATE", "Result.txt", content="one"),
                    PatchOperation("CREATE", "result.txt", content="two"),
                ),
            )

    def test_partial_apply_is_compensated_and_journal_records_rollback(self) -> None:
        one = self.workspace / "one.txt"
        two = self.workspace / "two.txt"
        one.write_text("one", encoding="utf-8")
        two.write_text("two", encoding="utf-8")
        artifact = self.engine.prepare(
            "snapshot-crash",
            (
                PatchOperation("MODIFY", "one.txt", self.digest(one), "ONE"),
                PatchOperation("MODIFY", "two.txt", self.digest(two), "TWO"),
            ),
            patch_id="partial",
        )
        calls = 0

        def fail_second(path: Path, value: bytes, *, mode: int | None = None) -> None:
            nonlocal calls
            calls += 1
            if calls == 2:
                raise OSError("injected write failure")
            real_atomic_write_bytes(path, value, mode=mode)

        with mock.patch("coding_agent.patching.atomic_write_bytes", side_effect=fail_second):
            with self.assertRaisesRegex(OSError, "injected"):
                self.engine.apply(artifact)
        self.assertEqual(one.read_text(encoding="utf-8"), "one")
        self.assertEqual(two.read_text(encoding="utf-8"), "two")
        self.assertEqual(self.engine.recover("partial")["status"], "ROLLED_BACK")

    def test_rollback_refuses_to_overwrite_a_later_user_edit(self) -> None:
        target = self.workspace / "owned.txt"
        target.write_text("before", encoding="utf-8")
        artifact = self.engine.prepare(
            "snapshot-user",
            (PatchOperation("MODIFY", "owned.txt", self.digest(target), "agent"),),
            patch_id="preserve-user",
        )
        self.engine.apply(artifact)
        target.write_text("user-after-agent", encoding="utf-8")
        with self.assertRaises(OperationConflict):
            self.engine.rollback("preserve-user")
        self.assertEqual(target.read_text(encoding="utf-8"), "user-after-agent")


if __name__ == "__main__":
    unittest.main()
