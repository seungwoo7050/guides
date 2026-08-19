from __future__ import annotations

import fcntl
import json
import os
import tempfile
import unittest
from pathlib import Path

import yaml

from deployment import deploy

ROOT = Path(__file__).resolve().parents[1]


def manifest(name: str) -> dict:
    return yaml.safe_load((ROOT / "examples/manifests" / name).read_text(encoding="utf-8"))


# [Implementation 8] Deployment state-machine verification
class DeploymentTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.state = Path(self.temporary.name)
        initial = json.loads((ROOT / "examples/state/current.json").read_text(encoding="utf-8"))
        (self.state / "current.json").write_text(json.dumps(initial) + "\n", encoding="utf-8")

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def current(self) -> dict:
        return json.loads((self.state / "current.json").read_text(encoding="utf-8"))

    def events(self) -> list[dict]:
        path = self.state / "events.jsonl"
        return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]

    def test_successful_release_updates_current_and_previous(self) -> None:
        result = deploy(self.state, manifest("v1.yaml"))
        self.assertEqual(result, {"status": "success", "phase": "committed", "current": "v1"})
        current = self.current()
        self.assertEqual(current["current"], "v1")
        self.assertEqual(current["previous"], "v0")
        self.assertEqual(current["db_schema"], 3)
        self.assertFalse((self.state / "staged.json").exists())
        self.assertEqual(self.events()[-1]["event"], "release-committed")
        self.assertEqual((self.state / "events.jsonl").stat().st_mode & 0o777, 0o600)

    def test_smoke_failure_retains_previous_release_with_compatible_migration(self) -> None:
        self.assertEqual(deploy(self.state, manifest("v1.yaml"))["status"], "success")
        result = deploy(self.state, manifest("bad-smoke.yaml"))
        self.assertEqual(result["phase"], "smoke")
        current = self.current()
        self.assertEqual(current["current"], "v1")
        self.assertEqual(current["db_schema"], 4)
        event_names = [event["event"] for event in self.events()]
        self.assertIn("rollback-completed", event_names)
        self.assertFalse((self.state / "staged.json").exists())

    def test_incompatible_schema_is_rejected_before_staging(self) -> None:
        before = self.current()
        result = deploy(self.state, manifest("incompatible.yaml"))
        self.assertEqual(result["phase"], "preflight")
        self.assertEqual(self.current(), before)
        self.assertFalse((self.state / "staged.json").exists())

    def test_concurrent_environment_lock_is_rejected(self) -> None:
        lock_path = self.state / "deployment.lock"
        descriptor = os.open(lock_path, os.O_RDWR | os.O_CREAT, 0o600)
        try:
            fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
            result = deploy(self.state, manifest("v1.yaml"))
            self.assertEqual(result["phase"], "lock")
        finally:
            fcntl.flock(descriptor, fcntl.LOCK_UN)
            os.close(descriptor)


if __name__ == "__main__":
    unittest.main()
