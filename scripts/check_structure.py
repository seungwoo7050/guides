#!/usr/bin/env python3
"""Validate the guide's repository and learner-artifact structure."""

from __future__ import annotations

import json
import stat
import sys
from pathlib import Path, PurePosixPath
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
REQUIRED_FILES = (
    "README.md",
    "CONTRIBUTING.md",
    "LICENSE.md",
    "LICENSES/CC-BY-4.0.txt",
    "LICENSES/MIT.txt",
    "Makefile",
    "prepare.sh",
    "verify.sh",
    "docs/00-roadmap.md",
    "docs/01-cloud-state-responsibility-and-evidence.md",
    "docs/02-cloud-characteristics-service-and-deployment-models.md",
    "docs/03-control-plane-data-plane-and-identity.md",
    "docs/04-iaas-compute-network-and-storage.md",
    "docs/05-failure-domains-elasticity-and-recovery.md",
    "docs/06-paas-and-managed-service-contracts.md",
    "docs/07-serverless-and-faas-runtime.md",
    "docs/08-event-delivery-concurrency-and-idempotency.md",
    "docs/09-saas-tenancy-and-isolation.md",
    "docs/10-saas-entitlements-metering-and-billing.md",
    "docs/11-cloud-security-observability-and-incidents.md",
    "docs/12-cost-capacity-quotas-and-finops.md",
    "docs/13-portability-lock-in-and-exit.md",
    "docs/14-service-selection-and-architecture-review.md",
    "docs/15-capstone.md",
    "docs/90-standards-map.md",
    "exercises/README.md",
    "profiles/README.md",
    "profiles/provider-experiment-template.md",
    "projects/multitenant-document-processing-saas/README.md",
    "projects/multitenant-document-processing-saas/inputs/system-brief.md",
    "projects/multitenant-document-processing-saas/rubric.md",
    "reference/architecture-review-checklist.md",
    "reference/cloud-experiment-safety.md",
    "reference/command-reference.md",
    "reference/contract-evidence-map.md",
    "reference/glossary.md",
    "reference/manual-review-guide.md",
    "reference/provider-crosswalk.md",
    "reference/responsibility-matrix.md",
    "scripts/check_artifact.py",
    "scripts/check_links.py",
    "scripts/check_profiles.py",
    "scripts/check_structure.py",
    "scripts/check_workspace.sh",
    "scripts/new_workspace.sh",
    "scripts/source_fingerprint.py",
    "scripts/test_artifact_verifier.py",
    "scripts/test_links.py",
    "scripts/test_source_fingerprint.py",
    "scripts/test_verify_cloud_model.py",
    "scripts/test_workspace.py",
    "scripts/verify_cloud_model.py",
    "scripts/workspace.py",
)
DOCUMENT_EXERCISES = (
    "01-service-classification",
    "02-iaas-failure-domains",
    "03-managed-service-contract",
    "04-faas-event-lifecycle",
    "05-saas-tenant-isolation",
    "06-cost-and-exit",
)
MODEL_ID = "07-local-cloud-model"
CAPSTONE_ID = "multitenant-document-processing-saas"
CONTRACT_KEYS = {
    "schema_version",
    "workspace_source",
    "validator",
    "expected_starter_failures",
}


class StrictJSONError(ValueError):
    pass


def strict_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise StrictJSONError(f"duplicate key {key!r}")
        value[key] = item
    return value


def reject_constant(value: str) -> None:
    raise StrictJSONError(f"non-finite number {value!r}")


def strict_json(text: str) -> Any:
    return json.loads(text, object_pairs_hook=strict_object, parse_constant=reject_constant)


def metadata_matches(key: str, actual: object, expected: object) -> bool:
    return actual == expected and (key != "schema_version" or type(actual) is int)


def safe_relative(value: object) -> str | None:
    if not isinstance(value, str) or not value or "\\" in value:
        return None
    path = PurePosixPath(value)
    if (
        not path.parts
        or path.as_posix() != value
        or path.is_absolute()
        or any(part in ("", ".", "..") for part in path.parts)
    ):
        return None
    return path.as_posix()


def regular_file(relative: str, errors: list[str], label: str | None = None) -> bool:
    """Require a real in-tree regular file with no symlinked path component."""
    safe = safe_relative(relative)
    shown = label or relative
    if safe is None:
        errors.append(f"{shown}: unsafe relative path")
        return False
    current = ROOT
    for part in PurePosixPath(safe).parts:
        current = current / part
        try:
            mode = current.lstat().st_mode
        except OSError as exc:
            errors.append(f"{shown}: cannot inspect required file ({exc})")
            return False
        if stat.S_ISLNK(mode):
            errors.append(f"{shown}: symlink path components are forbidden")
            return False
    if not stat.S_ISREG(mode):
        errors.append(f"{shown}: expected a regular file")
        return False
    return True


def load_contract(relative: str, errors: list[str]) -> dict[str, Any] | None:
    if not regular_file(relative, errors):
        return None
    try:
        value = strict_json((ROOT / relative).read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError, StrictJSONError) as exc:
        errors.append(f"{relative}: invalid JSON ({exc})")
        return None
    if not isinstance(value, dict):
        errors.append(f"{relative}: top level must be an object")
        return None
    missing = sorted(CONTRACT_KEYS - value.keys())
    if missing:
        errors.append(f"{relative}: missing metadata keys {', '.join(missing)}")
    failures = value.get("expected_starter_failures")
    if (
        not isinstance(failures, list)
        or not failures
        or any(not isinstance(item, str) or not item for item in failures)
        or len(failures) != len(set(failures))
    ):
        errors.append(f"{relative}: expected_starter_failures must be non-empty and unique")
    return value


def profile_files(root: Path, errors: list[str], label: str) -> set[str]:
    if not root.is_dir() or root.is_symlink():
        errors.append(f"{label}: missing regular profile directory")
        return set()
    found: set[str] = set()
    for entry in sorted(root.rglob("*")):
        relative = entry.relative_to(ROOT).as_posix()
        if entry.is_symlink():
            errors.append(f"{relative}: profile symlinks are forbidden")
        elif entry.is_file():
            found.add(entry.relative_to(root).as_posix())
        elif not entry.is_dir():
            errors.append(f"{relative}: non-regular profile entry")
    return found


def validate_template_markers(
    root: Path,
    required_files: set[str],
    forbidden_tokens: object,
    errors: list[str],
    label: str,
) -> None:
    if (
        not isinstance(forbidden_tokens, list)
        or not forbidden_tokens
        or any(not isinstance(token, str) or not token for token in forbidden_tokens)
    ):
        errors.append(f"{label}: contract forbidden_tokens must be non-empty strings")
        return
    for relative in sorted(required_files):
        path = root / relative
        if not path.is_file() or path.is_symlink():
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as exc:
            errors.append(f"{label}/{relative}: cannot inspect starter marker ({exc})")
            continue
        if not any(token in text for token in forbidden_tokens):
            errors.append(f"{label}/{relative}: every starter artifact must remain explicitly unfilled")


def validate_document_exercise(exercise: str, errors: list[str]) -> None:
    base = f"exercises/{exercise}"
    regular_file(f"{base}/README.md", errors)
    contract_path = f"{base}/contract.json"
    contract = load_contract(contract_path, errors)
    if contract is None:
        return
    expected_metadata = {
        "schema_version": 1,
        "artifact_id": exercise,
        "workspace_source": "template",
        "validator": "scripts/check_artifact.py",
    }
    for key, expected in expected_metadata.items():
        actual = contract.get(key)
        if not metadata_matches(key, actual, expected):
            errors.append(f"{contract_path}: {key} must equal {expected!r}")
    required = contract.get("required_files")
    if (
        not isinstance(required, list)
        or not required
        or any(safe_relative(item) is None for item in required)
        or len(required) != len(set(required))
    ):
        errors.append(f"{contract_path}: required_files must be safe, non-empty, and unique")
        return
    expected_files = set(required)
    for profile in ("template", "reference"):
        root = ROOT / base / profile
        actual = profile_files(root, errors, f"{base}/{profile}")
        missing = sorted(expected_files - actual)
        unexpected = sorted(actual - expected_files)
        if missing:
            errors.append(f"{base}/{profile}: missing contract files {', '.join(missing)}")
        if unexpected:
            errors.append(f"{base}/{profile}: unexpected files {', '.join(unexpected)}")
    validate_template_markers(
        ROOT / base / "template",
        expected_files,
        contract.get("forbidden_tokens"),
        errors,
        f"{base}/template",
    )


def validate_model(errors: list[str]) -> None:
    base = f"exercises/{MODEL_ID}"
    required = (
        "README.md",
        "contract.json",
        "skeleton/cloud_model.py",
        "reference/cloud_model.py",
        "tests/contract.py",
        "tests/test_cloud_model.py",
        "tests/fixtures/import_error.py",
        "tests/fixtures/missing_api.py",
        "tests/fixtures/timeout.py",
        "tests/mutants/_reference_loader.py",
        "tests/mutants/cm_001_public_state.py",
        "tests/mutants/cm_002_accept_unknown_plan.py",
        "tests/mutants/cm_003_deny_owner.py",
        "tests/mutants/cm_004_cross_tenant_read.py",
        "tests/mutants/cm_005_write_before_quota.py",
        "tests/mutants/cm_006_duplicate_effect.py",
        "tests/mutants/cm_007_event_id_alias.py",
        "tests/mutants/cm_008_retry_off_by_one.py",
        "tests/mutants/cm_009_cross_tenant_event.py",
        "tests/mutants/cm_010_silent_drain.py",
        "tests/mutants/cm_011_partial_cleanup.py",
        "tests/mutants/cm_012_tenant_resurrection.py",
        "tests/mutants/cm_013_content_evidence.py",
    )
    for relative in required:
        regular_file(f"{base}/{relative}", errors)
    contract_path = f"{base}/contract.json"
    contract = load_contract(contract_path, errors)
    if contract is None:
        return
    expected_metadata = {
        "schema_version": 1,
        "exercise_id": MODEL_ID,
        "workspace_source": "skeleton",
        "validator": "scripts/verify_cloud_model.py",
        "implementation_file": "cloud_model.py",
    }
    for key, expected in expected_metadata.items():
        actual = contract.get(key)
        if not metadata_matches(key, actual, expected):
            errors.append(f"{contract_path}: {key} must equal {expected!r}")
    check_ids = contract.get("check_ids")
    failures = contract.get("expected_starter_failures")
    expected_checks = [f"CM-{number:03d}" for number in range(1, 14)]
    if check_ids != expected_checks:
        errors.append(f"{contract_path}: check_ids must be the ordered CM-001..CM-013 contract")
    elif (
        isinstance(failures, list)
        and all(isinstance(item, str) for item in failures)
        and not set(failures) < set(check_ids)
    ):
        errors.append(f"{contract_path}: starter failures must be a proper subset of check_ids")


def validate_capstone(errors: list[str]) -> None:
    base = f"projects/{CAPSTONE_ID}"
    for relative in ("README.md", "inputs/system-brief.md", "rubric.md"):
        regular_file(f"{base}/{relative}", errors)
    contract_path = f"{base}/contract.json"
    contract = load_contract(contract_path, errors)
    if contract is None:
        return
    expected_metadata = {
        "schema_version": 2,
        "project_id": CAPSTONE_ID,
        "workspace_source": "template",
        "validator": "scripts/check_artifact.py",
    }
    for key, expected in expected_metadata.items():
        actual = contract.get(key)
        if not metadata_matches(key, actual, expected):
            errors.append(f"{contract_path}: {key} must equal {expected!r}")
    required = contract.get("required_files")
    if (
        not isinstance(required, list)
        or not required
        or any(safe_relative(item) is None for item in required)
        or len(required) != len(set(required))
    ):
        errors.append(f"{contract_path}: required_files must be safe, non-empty, and unique")
        return
    expected_files = set(required)
    for profile in ("template", "reference"):
        actual = profile_files(ROOT / base / profile, errors, f"{base}/{profile}")
        missing = sorted(expected_files - actual)
        unexpected = sorted(actual - expected_files)
        if missing:
            errors.append(f"{base}/{profile}: missing contract files {', '.join(missing)}")
        if unexpected:
            errors.append(f"{base}/{profile}: unexpected files {', '.join(unexpected)}")
    validate_template_markers(
        ROOT / base / "template",
        expected_files,
        contract.get("forbidden_tokens"),
        errors,
        f"{base}/template",
    )


def main() -> int:
    errors: list[str] = []
    for relative in REQUIRED_FILES:
        regular_file(relative, errors)
    for exercise in DOCUMENT_EXERCISES:
        validate_document_exercise(exercise, errors)
    validate_model(errors)
    validate_capstone(errors)
    if errors:
        for error in errors:
            print(f"STRUCTURE ERROR [E_STRUCTURE]: {error}", file=sys.stderr)
        print(f"STRUCTURE FAIL: {len(errors)} error(s)", file=sys.stderr)
        return 1
    print(
        "STRUCTURE PASS: "
        f"{len(REQUIRED_FILES)} repository files, {len(DOCUMENT_EXERCISES)} document exercises, "
        "1 executable model, and 1 staged capstone"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
