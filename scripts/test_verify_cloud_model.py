#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import os
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VERIFY = ROOT / "scripts/verify_cloud_model.py"
EXERCISE = ROOT / "exercises/07-local-cloud-model"
REFERENCE = EXERCISE / "reference/cloud_model.py"
SKELETON = EXERCISE / "skeleton/cloud_model.py"
CONTRACT = EXERCISE / "contract.json"
FIXTURES = EXERCISE / "tests/fixtures"
MUTANTS = EXERCISE / "tests/mutants"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def invoke(implementation: Path, report: Path | None = None) -> subprocess.CompletedProcess[str]:
    command = [sys.executable, str(VERIFY), "--implementation", str(implementation)]
    if report is not None:
        command.extend(["--report", str(report)])
    environment = os.environ.copy()
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    return subprocess.run(
        command,
        cwd=ROOT,
        env=environment,
        text=True,
        capture_output=True,
        check=False,
        timeout=15,
    )


def load_report(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


class VerifyCloudModelMetaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
        cls.check_ids = cls.contract["check_ids"]
        cls.starter_failures = cls.contract["expected_starter_failures"]

    def test_reference_passes_with_stable_evidence(self) -> None:
        with tempfile.TemporaryDirectory(prefix="cloud-model-report-") as temporary:
            report_path = Path(temporary) / "reference.json"
            completed = invoke(REFERENCE, report_path)
            self.assertEqual(0, completed.returncode, completed.stdout + completed.stderr)
            report = load_report(report_path)

        self.assertEqual("PASS", report["summary"]["result"])
        self.assertEqual([], report["summary"]["failed_ids"])
        self.assertEqual(self.check_ids, report["contract"]["check_ids"])
        self.assertEqual(self.check_ids, [item["id"] for item in report["checks"]])
        self.assertEqual(
            "exercises/07-local-cloud-model/reference/cloud_model.py",
            report["implementation"]["path"],
        )
        self.assertEqual(sha256(REFERENCE), report["implementation"]["sha256"])
        by_id = {item["id"]: item for item in report["checks"]}
        self.assertEqual(
            ["processed", "duplicate", "processed"],
            by_id["CM-006"]["observed"]["statuses"],
        )
        self.assertEqual(2, by_id["CM-006"]["observed"]["output_count"])
        self.assertEqual(True, by_id["CM-011"]["observed"]["active_state_cleared"])
        self.assertTrue(all(item["evidence_sha256"] for item in report["checks"]))

    def test_skeleton_fails_only_declared_starter_checks(self) -> None:
        with tempfile.TemporaryDirectory(prefix="cloud-model-starter-") as temporary:
            report_path = Path(temporary) / "starter.json"
            completed = invoke(SKELETON, report_path)
            self.assertEqual(1, completed.returncode, completed.stdout + completed.stderr)
            report = load_report(report_path)
        self.assertEqual(self.starter_failures, report["summary"]["failed_ids"])
        self.assertEqual(8, report["summary"]["failed"])
        self.assertEqual(0, report["summary"]["errors"])

    def test_single_defect_mutants_are_rejected_by_known_checks(self) -> None:
        expected = {
            "cm_001_public_state.py": ["CM-001"],
            "cm_003_deny_owner.py": ["CM-003"],
            "cm_004_cross_tenant_read.py": ["CM-004"],
            "cm_005_write_before_quota.py": ["CM-005"],
            "cm_006_duplicate_effect.py": ["CM-006"],
            "cm_007_event_id_alias.py": ["CM-007"],
            "cm_008_retry_off_by_one.py": ["CM-008", "CM-011"],
            "cm_009_cross_tenant_event.py": ["CM-009"],
            "cm_010_silent_drain.py": ["CM-010"],
            "cm_011_partial_cleanup.py": ["CM-011"],
            "cm_012_tenant_resurrection.py": ["CM-012"],
        }
        with tempfile.TemporaryDirectory(prefix="cloud-model-mutants-") as temporary:
            temporary_path = Path(temporary)
            for filename, expected_ids in expected.items():
                with self.subTest(mutant=filename):
                    report_path = temporary_path / f"{filename}.json"
                    completed = invoke(MUTANTS / filename, report_path)
                    self.assertEqual(1, completed.returncode, completed.stdout + completed.stderr)
                    report = load_report(report_path)
                    self.assertEqual(expected_ids, report["summary"]["failed_ids"])

    def test_path_import_and_api_errors_are_not_contract_failures(self) -> None:
        cases = (
            (FIXTURES / "does-not-exist.py", "E_PATH"),
            (FIXTURES / "import_error.py", "E_IMPORT"),
            (FIXTURES / "missing_api.py", "E_API"),
            (FIXTURES / "timeout.py", "E_TIMEOUT"),
        )
        for implementation, code in cases:
            with self.subTest(code=code):
                completed = invoke(implementation)
                self.assertEqual(2, completed.returncode, completed.stdout + completed.stderr)
                self.assertIn(f"MODEL VERIFY ERROR [{code}]", completed.stderr)
                self.assertNotIn("MODEL RESULT:", completed.stdout)

    def test_report_is_deterministic_private_and_create_only(self) -> None:
        with tempfile.TemporaryDirectory(prefix="cloud-model-determinism-") as temporary:
            temporary_path = Path(temporary)
            first = temporary_path / "first.json"
            second = temporary_path / "second.json"

            first_run = invoke(REFERENCE, first)
            second_run = invoke(REFERENCE, second)
            self.assertEqual(0, first_run.returncode, first_run.stdout + first_run.stderr)
            self.assertEqual(0, second_run.returncode, second_run.stdout + second_run.stderr)
            first_payload = first.read_bytes()
            self.assertEqual(first_payload, second.read_bytes())
            self.assertEqual(0o600, stat.S_IMODE(first.stat().st_mode))

            repeated = invoke(REFERENCE, first)
            self.assertEqual(2, repeated.returncode, repeated.stdout + repeated.stderr)
            self.assertIn("MODEL VERIFY ERROR [E_REPORT]", repeated.stderr)
            self.assertEqual(first_payload, first.read_bytes())

            decoded = first_payload.decode("utf-8")
            self.assertNotIn(str(ROOT), decoded)
            self.assertNotIn("generated_at", decoded)
            report = json.loads(decoded)
            self.assertEqual(False, report["execution"]["network_required"])
            self.assertEqual(False, report["execution"]["external_resources_created"])
            self.assertEqual(False, report["execution"]["os_sandboxed"])
            self.assertEqual(5, report["execution"]["timeout_seconds"])
            self.assertTrue(any("OS sandbox" in item for item in report["limitations"]))


if __name__ == "__main__":
    unittest.main(verbosity=2)
