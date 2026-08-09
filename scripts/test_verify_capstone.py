#!/usr/bin/env python3
"""Meta-tests for the internal developer platform capstone validator."""

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
SCRIPT = ROOT / "scripts/verify_capstone.py"
PROJECT = ROOT / "projects/internal-developer-platform"
REFERENCE = PROJECT / "reference"
TEMPLATE = PROJECT / "template"


def run_validator(artifact: Path) -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy()
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    environment["PYTHONHASHSEED"] = "0"
    return subprocess.run(
        [sys.executable, str(SCRIPT), str(artifact)],
        cwd=ROOT,
        env=environment,
        text=True,
        capture_output=True,
        check=False,
        timeout=15,
    )


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
        path.write_text(json.dumps(document, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")

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
                document["exit_capabilities"]["EXIT-2"]["evidence"][1]["json_pointer"] = "/checks/99"

            self.update_manifest(artifact, mutate)
            result = run_validator(artifact)
        self.assertEqual(result.returncode, 1)
        self.assertIn("CAPSTONE FAIL [E_REFERENCE]", result.stderr)
        self.assertIn("JSON pointer does not resolve", result.stderr)

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
            report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            result = run_validator(artifact)
        self.assertEqual(result.returncode, 1)
        self.assertIn("CAPSTONE FAIL [E_MODEL_HASH]", result.stderr)


if __name__ == "__main__":
    unittest.main()
