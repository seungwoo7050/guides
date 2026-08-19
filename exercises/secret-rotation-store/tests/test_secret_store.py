from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from secret_store import SecretStore


# [Implementation 7] Secret lifecycle regression suite
class SecretStoreTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name) / "store"
        self.store = SecretStore(self.root)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def event_text(self) -> str:
        return (self.root / "events.jsonl").read_text(encoding="utf-8")

    def test_install_activates_without_logging_secret_value(self) -> None:
        value = "database-password-one"
        accepted = self.store.install("database_password", "v1", value, lambda path: path.read_text() == value)
        self.assertTrue(accepted)
        current = self.store.current("database_password")
        self.assertEqual(current["version"], "v1")
        self.assertIsNone(current["previous"])
        self.assertNotIn(value, self.event_text())
        self.assertNotIn(value, json.dumps(current))
        self.assertEqual(self.store.secret_path("database_password").read_text(), value)
        self.assertEqual(self.root.stat().st_mode & 0o777, 0o700)
        self.assertEqual((self.root / "audit_hmac_key.bin").stat().st_mode & 0o777, 0o600)
        self.assertEqual(self.store.secret_path("database_password").stat().st_mode & 0o777, 0o600)

    def test_rejected_candidate_does_not_move_current(self) -> None:
        self.assertTrue(self.store.install("session_key", "v1", "accepted", lambda _: True))
        self.assertFalse(self.store.install("session_key", "v2", "rejected", lambda _: False))
        self.assertEqual(self.store.current("session_key")["version"], "v1")
        self.assertFalse((self.root / "session_key/versions/v2").exists())
        self.assertIn("candidate-rejected", self.event_text())

    def test_retire_protects_current_and_removes_previous(self) -> None:
        self.assertTrue(self.store.install("api_token", "v1", "first", lambda _: True))
        self.assertTrue(self.store.install("api_token", "v2", "second", lambda _: True))
        self.assertEqual(self.store.current("api_token")["previous"], "v1")
        with self.assertRaisesRegex(ValueError, "cannot retire current secret"):
            self.store.retire("api_token", "v2")
        self.store.retire("api_token", "v1")
        self.assertFalse((self.root / "api_token/versions/v1").exists())
        self.assertIn("version-retired", self.event_text())

    def test_invalid_names_versions_and_values_are_rejected(self) -> None:
        with self.assertRaises(ValueError):
            self.store.install("../escape", "v1", "value", lambda _: True)
        with self.assertRaises(ValueError):
            self.store.install("valid_name", "latest", "value", lambda _: True)
        with self.assertRaises(ValueError):
            self.store.install("valid_name", "v1", "two\nlines", lambda _: True)


if __name__ == "__main__":
    unittest.main()
