#!/usr/bin/env python3
from __future__ import annotations

import contextlib
import hashlib
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator
from unittest import mock

import check_artifact
import check_profiles
import check_structure


ROOT = Path(__file__).resolve().parents[1]
CHECKER = ROOT / "scripts/check_artifact.py"
DOCUMENT_BASES = [
    ROOT / "exercises/01-service-classification",
    ROOT / "exercises/02-iaas-failure-domains",
    ROOT / "exercises/03-managed-service-contract",
    ROOT / "exercises/04-faas-event-lifecycle",
    ROOT / "exercises/05-saas-tenant-isolation",
    ROOT / "exercises/06-cost-and-exit",
]
CAPSTONE = ROOT / "projects/multitenant-document-processing-saas"


@dataclass(frozen=True)
class Case:
    temporary: Path
    artifact: Path
    contract: Path


def invoke(artifact: Path, contract: Path) -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy()
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    environment["PYTHONHASHSEED"] = "0"
    return subprocess.run(
        [sys.executable, str(CHECKER), str(artifact), str(contract)],
        cwd=ROOT,
        env=environment,
        text=True,
        capture_output=True,
        check=False,
        timeout=15,
    )


@contextlib.contextmanager
def copied_case(base: Path, profile: str = "reference") -> Iterator[Case]:
    with tempfile.TemporaryDirectory(prefix="artifact-verifier-") as temporary_text:
        temporary = Path(temporary_text)
        artifact = temporary / profile
        contract = temporary / "contract.json"
        shutil.copytree(base / profile, artifact)
        shutil.copy2(base / "contract.json", contract)
        yield Case(temporary, artifact, contract)


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise AssertionError(f"expected object fixture: {path}")
    return value


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def update_report_hash(case: Case) -> None:
    report = case.artifact / "evidence/local-model-report.json"
    manifest_path = case.artifact / "evidence-manifest.json"
    manifest = load_json(manifest_path)
    manifest["local_experiment"]["report_sha256"] = hashlib.sha256(report.read_bytes()).hexdigest()
    write_json(manifest_path, manifest)


class ArtifactVerifierMetaTests(unittest.TestCase):
    def assert_error(
        self,
        completed: subprocess.CompletedProcess[str],
        code: str,
        exit_code: int = 1,
    ) -> None:
        self.assertEqual(exit_code, completed.returncode, completed.stdout + completed.stderr)
        self.assertEqual("", completed.stdout)
        lines = completed.stderr.splitlines()
        self.assertEqual(1, len(lines), completed.stderr)
        self.assertTrue(lines[0].startswith(f"ARTIFACT ERROR [{code}] "), completed.stderr)

    def test_all_current_references_pass(self) -> None:
        for base in [*DOCUMENT_BASES, CAPSTONE]:
            with self.subTest(artifact=base.name):
                completed = invoke(base / "reference", base / "contract.json")
                self.assertEqual(0, completed.returncode, completed.stdout + completed.stderr)
                self.assertEqual("ARTIFACT RESULT: PASS\n", completed.stdout)
                self.assertEqual("", completed.stderr)

    def test_all_templates_fail_only_as_unfilled(self) -> None:
        for base in [*DOCUMENT_BASES, CAPSTONE]:
            with self.subTest(artifact=base.name):
                self.assert_error(
                    invoke(base / "template", base / "contract.json"),
                    "E_UNFILLED",
                )

    def test_missing_file_precedes_intended_starter_failure(self) -> None:
        with copied_case(DOCUMENT_BASES[0], "template") as case:
            (case.artifact / "assessment.md").unlink()
            self.assert_error(invoke(case.artifact, case.contract), "E_MISSING")

    def test_invalid_contract_and_manifest_json_are_not_starter_failures(self) -> None:
        with copied_case(DOCUMENT_BASES[0], "template") as case:
            case.contract.write_text("{ invalid", encoding="utf-8")
            self.assert_error(invoke(case.artifact, case.contract), "E_CONTRACT_JSON", 2)

        with copied_case(CAPSTONE, "template") as case:
            (case.artifact / "evidence-manifest.json").write_text("{ invalid", encoding="utf-8")
            self.assert_error(invoke(case.artifact, case.contract), "E_JSON")

    def test_contract_schema_is_strict(self) -> None:
        with copied_case(DOCUMENT_BASES[0]) as case:
            contract = load_json(case.contract)
            contract["unexpected"] = True
            write_json(case.contract, contract)
            self.assert_error(invoke(case.artifact, case.contract), "E_CONTRACT_SCHEMA", 2)

        with copied_case(DOCUMENT_BASES[0]) as case:
            case.contract.write_text('{"schema_version": 1, "schema_version": 1}\n')
            self.assert_error(invoke(case.artifact, case.contract), "E_CONTRACT_JSON", 2)

        with copied_case(DOCUMENT_BASES[0]) as case:
            contract = load_json(case.contract)
            contract["schema_version"] = True
            write_json(case.contract, contract)
            self.assert_error(invoke(case.artifact, case.contract), "E_CONTRACT_SCHEMA", 2)

    def test_repository_contract_loaders_reject_duplicate_and_nonfinite_json(self) -> None:
        for label, text in (
            ("duplicate", '{"schema_version": 1, "schema_version": 1}'),
            ("nonfinite", '{"schema_version": NaN}'),
        ):
            with self.subTest(loader="structure", case=label):
                with self.assertRaises((json.JSONDecodeError, check_structure.StrictJSONError)):
                    check_structure.strict_json(text)
            with self.subTest(loader="profiles", case=label):
                with self.assertRaises((json.JSONDecodeError, check_profiles.StrictJSONError)):
                    json.loads(
                        text,
                        object_pairs_hook=check_profiles.strict_object,
                        parse_constant=check_profiles.reject_constant,
                    )
        self.assertFalse(check_structure.metadata_matches("schema_version", True, 1))
        self.assertTrue(check_structure.metadata_matches("schema_version", 1, 1))

    def test_every_capstone_starter_file_keeps_an_explicit_unfilled_marker(self) -> None:
        with copied_case(CAPSTONE, "template") as case:
            contract = load_json(case.contract)
            errors: list[str] = []
            check_structure.validate_template_markers(
                case.artifact,
                set(contract["required_files"]),
                contract["forbidden_tokens"],
                errors,
                "capstone/template",
            )
            self.assertEqual([], errors)

            relative = "02-resource-and-state-inventory.md"
            path = case.artifact / relative
            path.write_text(path.read_text(encoding="utf-8").replace("TODO", "DONE"), encoding="utf-8")
            errors = []
            check_structure.validate_template_markers(
                case.artifact,
                set(contract["required_files"]),
                contract["forbidden_tokens"],
                errors,
                "capstone/template",
            )
            self.assertTrue(any(relative in error for error in errors), errors)

    def test_unsafe_contract_paths_are_rejected(self) -> None:
        unsafe = (
            "../assessment.md",
            "/tmp/assessment.md",
            "nested\\assessment.md",
            "assessment.md\x00suffix",
        )
        for relative in unsafe:
            with self.subTest(relative=repr(relative)), copied_case(DOCUMENT_BASES[0]) as case:
                contract = load_json(case.contract)
                contract["required_files"] = [relative]
                write_json(case.contract, contract)
                self.assert_error(invoke(case.artifact, case.contract), "E_CONTRACT_SCHEMA", 2)

    def test_root_contract_and_artifact_symlinks_are_rejected(self) -> None:
        with copied_case(DOCUMENT_BASES[0]) as case:
            root_link = case.temporary / "root-link"
            root_link.symlink_to(case.artifact, target_is_directory=True)
            self.assert_error(invoke(root_link, case.contract), "E_ROOT", 2)

        with copied_case(DOCUMENT_BASES[0]) as case:
            contract_link = case.temporary / "contract-link.json"
            contract_link.symlink_to(case.contract)
            self.assert_error(invoke(case.artifact, contract_link), "E_CONTRACT_PATH", 2)

        with copied_case(DOCUMENT_BASES[0]) as case:
            external = case.temporary / "external.md"
            external.write_bytes(b"outside bytes stay unchanged\n")
            source = case.artifact / "assessment.md"
            source.unlink()
            source.symlink_to(external)
            before = external.read_bytes()
            self.assert_error(invoke(case.artifact, case.contract), "E_SYMLINK")
            self.assertEqual(before, external.read_bytes())

    def test_nonregular_required_entry_is_rejected(self) -> None:
        with copied_case(DOCUMENT_BASES[0]) as case:
            source = case.artifact / "assessment.md"
            source.unlink()
            source.mkdir()
            self.assert_error(invoke(case.artifact, case.contract), "E_NONREGULAR")

    def test_markdown_headings_must_be_real_lines_and_stage2_cannot_disappear(self) -> None:
        with copied_case(CAPSTONE) as case:
            path = case.artifact / "01-responsibility-matrix.md"
            text = path.read_text(encoding="utf-8")
            heading = "## Stage 2 — Managed platform"
            path.write_text(text.replace(heading, f"```text\n{heading}\n```", 1), encoding="utf-8")
            self.assert_error(invoke(case.artifact, case.contract), "E_HEADING")

        with copied_case(CAPSTONE) as case:
            path = case.artifact / "01-responsibility-matrix.md"
            text = path.read_text(encoding="utf-8")
            heading = "## Open risks와 owner"
            replacement = f"```text\n{heading}\n```not-a-close\n```"
            path.write_text(text.replace(heading, replacement, 1), encoding="utf-8")
            self.assert_error(invoke(case.artifact, case.contract), "E_HEADING")

    def test_release_decision_must_be_single_valid_anchored_line(self) -> None:
        with copied_case(CAPSTONE) as case:
            path = case.artifact / "08-release-review.md"
            text = path.read_text(encoding="utf-8")
            path.write_text(
                text.replace(
                    "Decision: APPROVE_WITH_CONDITIONS",
                    "Decision: APPROVE_WITH_CONDITIONS extra",
                ),
                encoding="utf-8",
            )
            self.assert_error(invoke(case.artifact, case.contract), "E_DECISION")

        for replacement in (
            "Decision: APPROVE\n<!-- APPROVE_WITH_CONDITIONS -->",
            "```text\nDecision: APPROVE_WITH_CONDITIONS\n```",
            "<!-- Decision: APPROVE_WITH_CONDITIONS -->\nDecision: APPROVE",
        ):
            with self.subTest(replacement=replacement), copied_case(CAPSTONE) as case:
                path = case.artifact / "08-release-review.md"
                text = path.read_text(encoding="utf-8")
                path.write_text(
                    text.replace("Decision: APPROVE_WITH_CONDITIONS", replacement, 1),
                    encoding="utf-8",
                )
                self.assert_error(invoke(case.artifact, case.contract), "E_DECISION")

    def test_stage_order_is_exact(self) -> None:
        with copied_case(CAPSTONE) as case:
            manifest_path = case.artifact / "evidence-manifest.json"
            manifest = load_json(manifest_path)
            manifest["ordered_stages"][1]["order"] = 3
            write_json(manifest_path, manifest)
            self.assert_error(invoke(case.artifact, case.contract), "E_STAGE")

        with copied_case(CAPSTONE) as case:
            manifest_path = case.artifact / "evidence-manifest.json"
            manifest = load_json(manifest_path)
            manifest["ordered_stages"][0]["evidence_refs"] = manifest["ordered_stages"][0][
                "evidence_refs"
            ][:1]
            write_json(manifest_path, manifest)
            self.assert_error(invoke(case.artifact, case.contract), "E_STAGE")

    def test_owns_and_exit_mappings_are_exact(self) -> None:
        with copied_case(CAPSTONE) as case:
            manifest_path = case.artifact / "evidence-manifest.json"
            manifest = load_json(manifest_path)
            shared = manifest["owns"][0]["evidence_refs"]
            for item in manifest["owns"]:
                item["evidence_refs"] = shared
            write_json(manifest_path, manifest)
            self.assert_error(invoke(case.artifact, case.contract), "E_OWN")

        with copied_case(CAPSTONE) as case:
            manifest_path = case.artifact / "evidence-manifest.json"
            manifest = load_json(manifest_path)
            for item in manifest["exit_capabilities"]:
                item["owns"] = ["OWN-1"]
            write_json(manifest_path, manifest)
            self.assert_error(invoke(case.artifact, case.contract), "E_EXIT")

    def test_dangling_file_heading_and_json_pointer_references_are_rejected(self) -> None:
        mutations = ("file", "heading", "json_pointer")
        for mutation in mutations:
            with self.subTest(mutation=mutation), copied_case(CAPSTONE) as case:
                manifest_path = case.artifact / "evidence-manifest.json"
                manifest = load_json(manifest_path)
                if mutation == "file":
                    manifest["owns"][0]["evidence_refs"][0]["file"] = "missing.md"
                elif mutation == "heading":
                    manifest["owns"][0]["evidence_refs"][0]["heading"] = "## Missing"
                else:
                    manifest["exit_capabilities"][3]["evidence_refs"][1][
                        "json_pointer"
                    ] = "/missing"
                write_json(manifest_path, manifest)
                self.assert_error(invoke(case.artifact, case.contract), "E_REFERENCE")

    def test_report_and_current_implementation_hashes_must_be_exact(self) -> None:
        with copied_case(CAPSTONE) as case:
            report_path = case.artifact / "evidence/local-model-report.json"
            report = load_json(report_path)
            report["summary"]["note"] = "changes current report bytes"
            write_json(report_path, report)
            self.assert_error(invoke(case.artifact, case.contract), "E_HASH")

        with copied_case(CAPSTONE) as case:
            report_path = case.artifact / "evidence/local-model-report.json"
            report = load_json(report_path)
            fake_hash = "0" * 64
            report["limitations"].append(report["implementation"]["sha256"])
            report["implementation"]["sha256"] = fake_hash
            write_json(report_path, report)
            manifest_path = case.artifact / "evidence-manifest.json"
            manifest = load_json(manifest_path)
            manifest["local_experiment"]["implementation_sha256"] = fake_hash
            write_json(manifest_path, manifest)
            update_report_hash(case)
            self.assert_error(invoke(case.artifact, case.contract), "E_HASH")

    def test_local_report_source_paths_are_exact(self) -> None:
        mutations = (
            ("implementation", "scripts/check_profiles.py", "implementation_sha256"),
            ("contract", "README.md", "contract_sha256"),
        )
        for report_field, replacement, manifest_hash_field in mutations:
            with self.subTest(report_field=report_field), copied_case(CAPSTONE) as case:
                report_path = case.artifact / "evidence/local-model-report.json"
                report = load_json(report_path)
                original_hash = report[report_field]["sha256"]
                report["limitations"].append(original_hash)
                replacement_hash = hashlib.sha256((ROOT / replacement).read_bytes()).hexdigest()
                report[report_field]["path"] = replacement
                report[report_field]["sha256"] = replacement_hash
                write_json(report_path, report)

                manifest_path = case.artifact / "evidence-manifest.json"
                manifest = load_json(manifest_path)
                manifest["local_experiment"][manifest_hash_field] = replacement_hash
                write_json(manifest_path, manifest)
                update_report_hash(case)
                self.assert_error(invoke(case.artifact, case.contract), "E_LOCAL_REPORT")

    def test_thirteen_model_checks_must_pass_and_include_cleanup(self) -> None:
        cases = (("status", "E_CHECKS"), ("cleanup", "E_CLEANUP"))
        for mutation, code in cases:
            with self.subTest(mutation=mutation), copied_case(CAPSTONE) as case:
                report_path = case.artifact / "evidence/local-model-report.json"
                report = load_json(report_path)
                if mutation == "status":
                    report["checks"][0]["status"] = "fail"
                else:
                    report["checks"][10]["kind"] = "not-cleanup"
                write_json(report_path, report)
                update_report_hash(case)
                self.assert_error(invoke(case.artifact, case.contract), code)

    def test_budget_credential_and_limitations_are_required(self) -> None:
        for field, value, code in (
            ("budget", 1, "E_BUDGET"),
            ("credential_required", True, "E_CREDENTIAL"),
        ):
            with self.subTest(field=field), copied_case(CAPSTONE) as case:
                manifest_path = case.artifact / "evidence-manifest.json"
                manifest = load_json(manifest_path)
                manifest["local_experiment"][field] = value
                write_json(manifest_path, manifest)
                self.assert_error(invoke(case.artifact, case.contract), code)

        with copied_case(CAPSTONE) as case:
            report_path = case.artifact / "evidence/local-model-report.json"
            report = load_json(report_path)
            report["limitations"] = []
            write_json(report_path, report)
            update_report_hash(case)
            self.assert_error(invoke(case.artifact, case.contract), "E_LIMITATIONS")

    def test_release_conditions_and_handoffs_cannot_be_empty(self) -> None:
        for field, code in (
            ("release_conditions", "E_RELEASE"),
            ("implementation_owner_handoffs", "E_HANDOFF"),
        ):
            with self.subTest(field=field), copied_case(CAPSTONE) as case:
                manifest_path = case.artifact / "evidence-manifest.json"
                manifest = load_json(manifest_path)
                manifest[field] = []
                write_json(manifest_path, manifest)
                self.assert_error(invoke(case.artifact, case.contract), code)

        with copied_case(CAPSTONE) as case:
            manifest_path = case.artifact / "evidence-manifest.json"
            manifest = load_json(manifest_path)
            manifest["release_conditions"] = manifest["release_conditions"][:1]
            write_json(manifest_path, manifest)
            self.assert_error(invoke(case.artifact, case.contract), "E_RELEASE")

        with copied_case(CAPSTONE) as case:
            manifest_path = case.artifact / "evidence-manifest.json"
            manifest = load_json(manifest_path)
            manifest["release_conditions"][0]["status"] = "maybe"
            write_json(manifest_path, manifest)
            self.assert_error(invoke(case.artifact, case.contract), "E_RELEASE")

        for field in ("owner", "due", "verification", "rollback"):
            with self.subTest(release_field=field), copied_case(CAPSTONE) as case:
                manifest_path = case.artifact / "evidence-manifest.json"
                manifest = load_json(manifest_path)
                manifest["release_conditions"][0][field] = "   "
                write_json(manifest_path, manifest)
                self.assert_error(invoke(case.artifact, case.contract), "E_RELEASE")

    def test_cli_and_unexpected_checker_failure_use_harness_exit(self) -> None:
        completed = subprocess.run(
            [sys.executable, str(CHECKER)],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assert_error(completed, "E_CLI", 2)

        stderr = io.StringIO()
        with mock.patch.object(check_artifact, "verify", side_effect=RuntimeError("boom")):
            with contextlib.redirect_stderr(stderr):
                exit_code = check_artifact.run(["artifact", "contract"])
        self.assertEqual(2, exit_code)
        self.assertEqual(
            "ARTIFACT ERROR [E_INTERNAL] unexpected verifier failure\n",
            stderr.getvalue(),
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
