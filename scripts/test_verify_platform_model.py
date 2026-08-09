#!/usr/bin/env python3
"""Meta-tests for the deterministic platform model validator."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LAB = ROOT / "exercises/13-platform-control-plane"
VALIDATOR = ROOT / "scripts/verify_platform_model.py"
REFERENCE = LAB / "reference/platform_model.py"
SKELETON = LAB / "skeleton/platform_model.py"
MUTANTS = LAB / "tests/mutants"
FIXTURES = LAB / "tests/fixtures"
CONTRACT = json.loads((LAB / "contract.json").read_text(encoding="utf-8"))


def invoke(implementation: Path, report: Path | None = None, timeout: int = 20) -> subprocess.CompletedProcess[str]:
    command = [sys.executable, str(VALIDATOR), "--implementation", str(implementation)]
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
        timeout=timeout,
    )


def load_report(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


class PlatformModelValidatorTests(unittest.TestCase):
    def test_reference_passes_all_public_checks(self) -> None:
        with tempfile.TemporaryDirectory(prefix="platform-model-reference-") as temporary:
            report_path = Path(temporary) / "report.json"
            result = invoke(REFERENCE, report_path)
            self.assertEqual(0, result.returncode, result.stdout + result.stderr)
            report = load_report(report_path)
        self.assertEqual("PASS", report["summary"]["result"])
        self.assertEqual(CONTRACT["check_ids"], [item["id"] for item in report["checks"]])
        self.assertEqual(CONTRACT["identifiers"], report["identifiers"])
        self.assertEqual(CONTRACT["identifiers"], report["checks"][0]["observed"]["identifiers"])
        self.assertEqual(CONTRACT["contract_code"], report["contract_code"])
        self.assertEqual([], report["summary"]["failed_ids"])
        self.assertEqual([], report["summary"]["error_ids"])

    def test_contract_code_tamper_is_a_harness_error(self) -> None:
        with tempfile.TemporaryDirectory(prefix="platform-model-contract-tamper-") as temporary:
            copied_root = Path(temporary) / "guide"
            shutil.copytree(
                ROOT,
                copied_root,
                ignore=shutil.ignore_patterns(".git", ".guide", ".workspace", "__pycache__"),
            )
            copied_contract_code = copied_root / "exercises/13-platform-control-plane/tests/contract.py"
            copied_contract_code.write_text(
                copied_contract_code.read_text(encoding="utf-8") + "\n# tampered contract code\n",
                encoding="utf-8",
            )
            result = subprocess.run(
                [
                    sys.executable,
                    str(copied_root / "scripts/verify_platform_model.py"),
                    "--implementation",
                    str(copied_root / "exercises/13-platform-control-plane/reference/platform_model.py"),
                ],
                cwd=copied_root,
                env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
                text=True,
                capture_output=True,
                check=False,
                timeout=20,
            )
        self.assertEqual(2, result.returncode, result.stdout + result.stderr)
        self.assertIn("[E_CONTRACT]", result.stderr)
        self.assertIn("contract_code SHA-256", result.stderr)

    def test_starter_fails_only_declared_checks_without_harness_errors(self) -> None:
        with tempfile.TemporaryDirectory(prefix="platform-model-starter-") as temporary:
            report_path = Path(temporary) / "report.json"
            result = invoke(SKELETON, report_path)
            self.assertEqual(1, result.returncode, result.stdout + result.stderr)
            report = load_report(report_path)
        self.assertEqual(CONTRACT["expected_starter_failures"], report["summary"]["failed_ids"])
        self.assertEqual([], report["summary"]["error_ids"])

    def test_single_defect_mutants_are_rejected(self) -> None:
        expected = {
            "pe_001_stale_generation_ready.py": "PE-001",
            "pe_001_unstructured_smoke_ready.py": "PE-001",
            "pe_002_idempotency_conflict.py": "PE-002",
            "pe_003_ready_without_evidence.py": "PE-003",
            "pe_003_hidden_partial_effect.py": "PE-003",
            "pe_004_global_queue_block.py": "PE-004",
            "pe_005_ignore_drift.py": "PE-005",
            "pe_005_missing_drift_transition.py": "PE-005",
            "pe_006_unbounded_break_glass.py": "PE-006",
            "pe_006_missing_break_glass_reason.py": "PE-006",
            "pe_007_static_credential_fallback.py": "PE-007",
            "pe_008_continue_after_failed_wave.py": "PE-008",
            "pe_008_missing_abort_evidence.py": "PE-008",
            "pe_009_retirement_leak.py": "PE-009",
            "pe_009_retirement_exception_leak.py": "PE-009",
            "pe_010_snapshot_alias.py": "PE-010",
        }
        with tempfile.TemporaryDirectory(prefix="platform-model-mutants-") as temporary:
            report_root = Path(temporary)
            for filename, expected_id in expected.items():
                with self.subTest(mutant=filename):
                    report_path = report_root / f"{filename}.json"
                    result = invoke(MUTANTS / filename, report_path)
                    self.assertEqual(1, result.returncode, result.stdout + result.stderr)
                    report = load_report(report_path)
                    self.assertIn(expected_id, report["summary"]["failed_ids"])
                    self.assertEqual([], report["summary"]["error_ids"])

    def test_path_import_api_timeout_and_network_errors_are_stable(self) -> None:
        cases = (
            (ROOT.parent / "outside.py", "E_PATH"),
            (FIXTURES / "import_error.py", "E_IMPORT"),
            (FIXTURES / "missing_api.py", "E_API"),
            (FIXTURES / "timeout.py", "E_TIMEOUT"),
            (FIXTURES / "network_import.py", "E_IMPORT"),
        )
        for implementation, marker in cases:
            with self.subTest(marker=marker):
                result = invoke(implementation, timeout=15)
                self.assertEqual(2, result.returncode, result.stdout + result.stderr)
                self.assertIn(f"[{marker}]", result.stderr)
        network = invoke(FIXTURES / "network_import.py")
        self.assertIn("network access is disabled", network.stderr)

    def test_learner_cannot_monkeypatch_the_executable_contract(self) -> None:
        result = invoke(FIXTURES / "contract_monkeypatch.py")
        self.assertEqual(1, result.returncode, result.stdout + result.stderr)
        self.assertIn("PLATFORM MODEL FAIL", result.stdout)
        self.assertNotIn("total=10 passed=10", result.stdout)
        self.assertNotIn("forged", result.stdout)

    def test_report_is_deterministic_private_and_create_only(self) -> None:
        with tempfile.TemporaryDirectory(prefix="platform-model-reports-") as temporary:
            root = Path(temporary)
            first_path = root / "first.json"
            second_path = root / "second.json"
            first = invoke(REFERENCE, first_path)
            second = invoke(REFERENCE, second_path)
            self.assertEqual(0, first.returncode, first.stdout + first.stderr)
            self.assertEqual(0, second.returncode, second.stdout + second.stderr)
            first_report = load_report(first_path)
            second_report = load_report(second_path)
            self.assertEqual(first_report, second_report)
            self.assertNotIn("must-not-appear", first_path.read_text(encoding="utf-8"))
            self.assertFalse(first_report["execution"]["network_required"])
            self.assertTrue(first_report["execution"]["network_denied_by_python_audit"])
            self.assertFalse(first_report["execution"]["external_resources_created"])
            self.assertFalse(first_report["execution"]["os_sandboxed"])
            overwrite = invoke(REFERENCE, first_path)
            self.assertEqual(2, overwrite.returncode, overwrite.stdout + overwrite.stderr)
            self.assertIn("[E_REPORT]", overwrite.stderr)


if __name__ == "__main__":
    unittest.main()
