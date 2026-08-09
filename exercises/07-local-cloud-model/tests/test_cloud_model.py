from __future__ import annotations

import importlib.util
import os
import sys
import unittest
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
PROFILE = os.environ.get("CLOUD_MODEL_PROFILE", "reference")
MODULE_PATH = BASE / PROFILE / "cloud_model.py"
spec = importlib.util.spec_from_file_location("cloud_model_under_test", MODULE_PATH)
if spec is None or spec.loader is None:
    raise RuntimeError(f"cannot load {MODULE_PATH}")
model_module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = model_module
spec.loader.exec_module(model_module)
CloudModel = model_module.CloudModel
AccessDenied = model_module.AccessDenied
QuotaExceeded = model_module.QuotaExceeded
TenantInactive = model_module.TenantInactive


class CloudModelContractTest(unittest.TestCase):
    def setUp(self) -> None:
        self.model = CloudModel()
        self.model.provision_tenant("tenant-a", "starter")
        self.model.provision_tenant("tenant-b", "starter")

    def test_stateful_resources_are_private(self) -> None:
        stateful = [resource for resource in self.model.resource_inventory() if resource["stateful"]]
        self.assertTrue(stateful)
        self.assertTrue(all(resource["public"] is False for resource in stateful))

    def test_cross_tenant_read_is_denied(self) -> None:
        self.model.store_document("tenant-a", "doc-a", "secret-a")
        with self.assertRaises(AccessDenied):
            self.model.read_document("tenant-b", "doc-a")

    def test_quota_rejection_is_atomic(self) -> None:
        self.model.store_document("tenant-a", "doc-1", "one")
        self.model.store_document("tenant-a", "doc-2", "two")
        with self.assertRaises(QuotaExceeded):
            self.model.store_document("tenant-a", "doc-3", "three")
        tenant_docs = [value for value in self.model.documents.values() if value["tenant_id"] == "tenant-a"]
        self.assertEqual(2, len(tenant_docs))
        self.assertNotIn("doc-3", self.model.documents)

    def test_duplicate_event_has_one_output_and_one_usage(self) -> None:
        self.model.store_document("tenant-a", "doc-a", "data")
        self.model.enqueue_event("event-1", "tenant-a", "doc-a")
        self.model.enqueue_event("event-1", "tenant-a", "doc-a")
        self.model.drain_events()
        tenant_outputs = [value for value in self.model.outputs.values() if value["tenant_id"] == "tenant-a"]
        self.assertEqual(1, len(tenant_outputs))
        self.assertEqual(1, self.model.usage_for("tenant-a"))

    def test_terminal_failure_is_dead_lettered_without_usage(self) -> None:
        self.model.enqueue_event("event-missing", "tenant-a", "missing-doc")
        self.model.drain_events(max_attempts=2)
        self.assertEqual(1, len(self.model.dead_letters))
        self.assertEqual("event-missing", self.model.dead_letters[0].event_id)
        self.assertEqual(0, self.model.usage_for("tenant-a"))

    def test_tenant_deletion_cleans_active_state(self) -> None:
        self.model.store_document("tenant-a", "doc-a", "data")
        self.model.enqueue_event("event-a", "tenant-a", "doc-a")
        self.model.delete_tenant("tenant-a")
        self.assertFalse(any(value["tenant_id"] == "tenant-a" for value in self.model.documents.values()))
        self.assertFalse(any(event.tenant_id == "tenant-a" for event in self.model.queue))
        self.assertFalse(any(resource["tenant_id"] == "tenant-a" for resource in self.model.resource_inventory()))
        with self.assertRaises(TenantInactive):
            self.model.read_document("tenant-a", "doc-a")


if __name__ == "__main__":
    unittest.main()
