#!/usr/bin/env python3
"""Meta-tests for the internal developer platform capstone validator."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/verify_capstone.py"
MODEL_VALIDATOR = ROOT / "scripts/verify_platform_model.py"
PROJECT = ROOT / "projects/internal-developer-platform"
REFERENCE = PROJECT / "reference"
TEMPLATE = PROJECT / "template"


def run_validator(
    artifact: Path,
    extra_environment: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy()
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    environment["PYTHONHASHSEED"] = "0"
    if extra_environment:
        environment.update(extra_environment)
    return subprocess.run(
        [sys.executable, str(SCRIPT), str(artifact)],
        cwd=ROOT,
        env=environment,
        text=True,
        capture_output=True,
        check=False,
        timeout=15,
    )


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class CapstoneValidatorTests(unittest.TestCase):
    maxDiff = None

    def copied_reference(self, parent: Path) -> Path:
        artifact = parent / "artifact"
        shutil.copytree(REFERENCE, artifact)
        return artifact

    def update_manifest(self, artifact: Path, mutate) -> None:
        path = artifact / "evidence-manifest.json"
        document = json.loads(path.read_text(encoding="utf-8"))
        mutate(document)
        path.write_text(
            json.dumps(document, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    def test_reference_passes(self) -> None:
        result = run_validator(REFERENCE)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("CAPSTONE PASS", result.stdout)
        self.assertIn("failure_scenarios=8", result.stdout)
        self.assertIn("model_checks=10", result.stdout)

    def test_template_is_rejected_as_unfinished(self) -> None:
        result = run_validator(TEMPLATE)
        self.assertEqual(result.returncode, 1)
        self.assertIn("CAPSTONE FAIL [E_UNFILLED]", result.stderr)

    def test_copied_reference_cannot_claim_builtin_model_evidence(self) -> None:
        with tempfile.TemporaryDirectory(prefix=".capstone-test-", dir=ROOT) as directory:
            artifact = self.copied_reference(Path(directory))
            result = run_validator(artifact)
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("CAPSTONE FAIL [E_MODEL_ORIGIN]", result.stderr)
        self.assertIn("learner-specific", result.stderr)

    def test_fenced_required_heading_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory(prefix=".capstone-test-", dir=ROOT) as directory:
            artifact = self.copied_reference(Path(directory))
            product_path = artifact / "01-product.md"
            product = product_path.read_text(encoding="utf-8")
            product = product.replace("## Golden path", "## Golden path omitted", 1)
            product += "\n```markdown\n## Golden path\n```\n"
            product_path.write_text(product, encoding="utf-8")
            result = run_validator(artifact)
        self.assertEqual(result.returncode, 1)
        self.assertIn("CAPSTONE FAIL [E_HEADING]", result.stderr)
        self.assertIn("Golden path", result.stderr)

    def test_repository_local_learner_implementation_report_passes(self) -> None:
        with tempfile.TemporaryDirectory(prefix=".capstone-test-", dir=ROOT) as directory:
            test_root = Path(directory)
            artifact = self.copied_reference(test_root)
            learner_dir = test_root / "learner-model"
            learner_dir.mkdir()
            learner_implementation = learner_dir / "platform_model.py"
            shutil.copy2(
                ROOT / "exercises/13-platform-control-plane/reference/platform_model.py",
                learner_implementation,
            )
            learner_implementation.write_text(
                learner_implementation.read_text(encoding="utf-8")
                + "\n# learner-specific passing implementation\n",
                encoding="utf-8",
            )
            with tempfile.TemporaryDirectory(prefix="capstone-learner-report-") as report_directory:
                generated_report = Path(report_directory) / "platform-model-report.json"
                generated = subprocess.run(
                    [
                        sys.executable,
                        str(MODEL_VALIDATOR),
                        "--implementation",
                        str(learner_implementation),
                        "--report",
                        str(generated_report),
                    ],
                    cwd=ROOT,
                    env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1", "PYTHONHASHSEED": "0"},
                    text=True,
                    capture_output=True,
                    check=False,
                    timeout=15,
                )
                self.assertEqual(generated.returncode, 0, generated.stdout + generated.stderr)
                stored_report = artifact / "evidence/platform-model-report.json"
                shutil.copy2(generated_report, stored_report)
            report = json.loads(stored_report.read_text(encoding="utf-8"))

            def mutate(document):
                document["model_report"]["sha256"] = digest(stored_report)
                document["model_report"]["implementation"] = report["implementation"]
                document["model_report"]["contract"] = report["contract"]
                document["model_report"]["contract_code"] = report["contract_code"]
                document["model_report"]["identifiers"] = report["identifiers"]

            self.update_manifest(artifact, mutate)
            result = run_validator(artifact)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("CAPSTONE PASS", result.stdout)

    def test_dangling_heading_reference_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory(prefix=".capstone-test-", dir=ROOT) as directory:
            artifact = self.copied_reference(Path(directory))

            def mutate(document):
                document["owns"]["OWN-1"]["evidence"][0]["heading"] = "Missing heading"

            self.update_manifest(artifact, mutate)
            result = run_validator(artifact)
        self.assertEqual(result.returncode, 1)
        self.assertIn("CAPSTONE FAIL [E_REFERENCE]", result.stderr)
        self.assertIn("heading does not resolve", result.stderr)

    def test_required_heading_inside_code_fence_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory(prefix=".capstone-test-", dir=ROOT) as directory:
            artifact = self.copied_reference(Path(directory))
            path = artifact / "01-product.md"
            text = path.read_text(encoding="utf-8")
            path.write_text(
                text.replace("## Golden path", "```text\n## Golden path\n```", 1),
                encoding="utf-8",
            )
            result = run_validator(artifact)
        self.assertEqual(result.returncode, 1)
        self.assertIn("CAPSTONE FAIL [E_HEADING]", result.stderr)

    def test_dangling_json_pointer_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory(prefix=".capstone-test-", dir=ROOT) as directory:
            artifact = self.copied_reference(Path(directory))

            def mutate(document):
                document["exit_capabilities"]["EXIT-2"]["evidence"][5]["json_pointer"] = "/checks/99"

            self.update_manifest(artifact, mutate)
            result = run_validator(artifact)
        self.assertEqual(result.returncode, 1)
        self.assertIn("CAPSTONE FAIL [E_REFERENCE]", result.stderr)
        self.assertIn("JSON pointer does not resolve", result.stderr)

    def test_semantically_wrong_passing_pointer_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory(prefix=".capstone-test-", dir=ROOT) as directory:
            artifact = self.copied_reference(Path(directory))

            def mutate(document):
                document["owns"]["OWN-4"]["evidence"][2]["json_pointer"] = "/checks/2"

            self.update_manifest(artifact, mutate)
            result = run_validator(artifact)
        self.assertEqual(result.returncode, 1)
        self.assertIn("CAPSTONE FAIL [E_TRACE_COVERAGE]", result.stderr)
        self.assertIn("OWN-4", result.stderr)

    def test_missing_exit_check_coverage_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory(prefix=".capstone-test-", dir=ROOT) as directory:
            artifact = self.copied_reference(Path(directory))

            def mutate(document):
                document["exit_capabilities"]["EXIT-3"]["evidence"].pop()

            self.update_manifest(artifact, mutate)
            result = run_validator(artifact)
        self.assertEqual(result.returncode, 1)
        self.assertIn("CAPSTONE FAIL [E_TRACE_COVERAGE]", result.stderr)
        self.assertIn("EXIT-3", result.stderr)

    def test_report_identifier_mismatch_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory(prefix=".capstone-test-", dir=ROOT) as directory:
            artifact = self.copied_reference(Path(directory))
            report_path = artifact / "evidence/platform-model-report.json"
            report = json.loads(report_path.read_text(encoding="utf-8"))
            report["identifiers"]["tenant_id"] = "tenant-unrelated"
            report_path.write_text(
                json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )

            def mutate(document):
                document["model_report"]["sha256"] = digest(report_path)

            self.update_manifest(artifact, mutate)
            result = run_validator(artifact)
        self.assertEqual(result.returncode, 1)
        self.assertIn("CAPSTONE FAIL [E_IDENTIFIERS]", result.stderr)

    def test_repository_local_tmpdir_falls_back_to_external_temp(self) -> None:
        result = run_validator(REFERENCE, {"TMPDIR": str(ROOT)})
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("CAPSTONE PASS", result.stdout)

    def test_manifest_model_hash_mismatch_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory(prefix=".capstone-test-", dir=ROOT) as directory:
            artifact = self.copied_reference(Path(directory))

            def mutate(document):
                document["model_report"]["sha256"] = "0" * 64

            self.update_manifest(artifact, mutate)
            result = run_validator(artifact)
        self.assertEqual(result.returncode, 1)
        self.assertIn("CAPSTONE FAIL [E_MODEL_HASH]", result.stderr)

    def test_tampered_model_report_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory(prefix=".capstone-test-", dir=ROOT) as directory:
            artifact = self.copied_reference(Path(directory))
            report_path = artifact / "evidence/platform-model-report.json"
            report = json.loads(report_path.read_text(encoding="utf-8"))
            report["checks"][0]["observed"]["condition"] = "Progressing"
            report_path.write_text(
                json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
            result = run_validator(artifact)
        self.assertEqual(result.returncode, 1)
        self.assertIn("CAPSTONE FAIL [E_MODEL_HASH]", result.stderr)


if __name__ == "__main__":
    unittest.main()
