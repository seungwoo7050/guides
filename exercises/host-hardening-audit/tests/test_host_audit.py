from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from host_audit import audit, load_snapshot, main

ROOT = Path(__file__).resolve().parents[1]


# [Implementation 8] Audit regression suite
class HostAuditTest(unittest.TestCase):
    def test_secure_snapshot_has_no_findings(self) -> None:
        snapshot = load_snapshot(ROOT / "examples/secure.json")
        self.assertEqual(audit(snapshot), [])
        self.assertEqual(main([str(ROOT / "examples/secure.json"), "--fail-on-findings"]), 0)

    def test_insecure_snapshot_reports_all_baseline_boundaries(self) -> None:
        findings = audit(load_snapshot(ROOT / "examples/insecure.json"))
        identifiers = {item["id"] for item in findings}
        self.assertEqual(
            identifiers,
            {
                "backup-local-only",
                "disk-alert-missing",
                "docker-socket-mounted",
                "ipv6-firewall-unreviewed",
                "non-admin-docker-group",
                "shared-admin-key",
                "ssh-password-authentication",
                "ssh-root-login",
                "time-not-synchronized",
                "unexpected-public-service-port",
                "unprotected-docker-tcp",
                "unrestricted-ssh-source",
            },
        )
        self.assertEqual([item["id"] for item in findings], sorted(identifiers))
        self.assertTrue(all(set(item) == {"id", "severity", "evidence", "remediation", "safe_order"} for item in findings))

    def test_invalid_snapshot_shape_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bad.json"
            path.write_text(json.dumps({"users": "not-an-array"}), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "users must be an array"):
                audit(load_snapshot(path))


if __name__ == "__main__":
    unittest.main()
