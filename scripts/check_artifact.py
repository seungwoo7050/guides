#!/usr/bin/env python3
"""Validate document exercises and the cumulative capstone artifact."""
from __future__ import annotations

import hashlib
import json
import os
import re
import stat
import sys
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, NoReturn, Sequence


ARTIFACT_EXIT = 1
HARNESS_EXIT = 2
COMMON_CONTENT_KEYS = {
    "required_files",
    "forbidden_tokens",
    "minimum_bytes",
    "required_headings",
    "required_phrases",
}
GENERIC_KEYS = COMMON_CONTENT_KEYS | {
    "schema_version",
    "artifact_id",
    "workspace_source",
    "validator",
    "expected_starter_failures",
}
CAPSTONE_KEYS = COMMON_CONTENT_KEYS | {
    "schema_version",
    "project_id",
    "workspace_source",
    "validator",
    "check_ids",
    "expected_starter_failures",
    "check_file_map",
    "json_required_keys",
}
CAPSTONE_ID = "multitenant-document-processing-saas"
CAPSTONE_CHECK_IDS = [f"CAP-{number:03d}" for number in range(1, 12)]
MODEL_CHECK_IDS = [f"CM-{number:03d}" for number in range(1, 14)]
STAGES = [
    ("iaas", 1, "## Stage 1 — IaaS"),
    ("managed-platform", 2, "## Stage 2 — Managed platform"),
    ("faas", 3, "## Stage 3 — FaaS"),
    ("saas", 4, "## Stage 4 — SaaS"),
]
STAGE_FILES = [
    "01-responsibility-matrix.md",
    "02-resource-and-state-inventory.md",
    "03-identity-network-and-tenant-boundaries.md",
    "04-failure-and-recovery-plan.md",
    "05-event-and-idempotency-contract.md",
    "06-cost-quota-and-metering.md",
    "07-portability-exit-and-deletion.md",
    "08-release-review.md",
    "09-isolated-experiment.md",
]
OWN_IDS = [f"OWN-{number}" for number in range(1, 7)]
EXIT_IDS = [f"EXIT-{number}" for number in range(1, 5)]
OWN_EVIDENCE = {
    "OWN-1": [
        ("01-responsibility-matrix.md", "## Stage 2 — Managed platform"),
        ("08-release-review.md", "## Evidence와 한계"),
    ],
    "OWN-2": [
        ("02-resource-and-state-inventory.md", "## Stage 1 — IaaS"),
        ("03-identity-network-and-tenant-boundaries.md", "## Stage 1 — IaaS"),
        ("04-failure-and-recovery-plan.md", "## Evidence와 한계"),
    ],
    "OWN-3": [
        ("01-responsibility-matrix.md", "## Stage 3 — FaaS"),
        ("08-release-review.md", "## Stage 4 — SaaS"),
    ],
    "OWN-4": [
        ("05-event-and-idempotency-contract.md", "## Stage 3 — FaaS"),
        ("04-failure-and-recovery-plan.md", "## Stage 3 — FaaS"),
        ("09-isolated-experiment.md", "## Evidence와 한계"),
    ],
    "OWN-5": [
        ("03-identity-network-and-tenant-boundaries.md", "## Stage 4 — SaaS"),
        ("05-event-and-idempotency-contract.md", "## Stage 4 — SaaS"),
        ("06-cost-quota-and-metering.md", "## Stage 4 — SaaS"),
        ("07-portability-exit-and-deletion.md", "## Stage 4 — SaaS"),
    ],
    "OWN-6": [
        ("04-failure-and-recovery-plan.md", "## Evidence와 한계"),
        ("06-cost-quota-and-metering.md", "## Evidence와 한계"),
        ("07-portability-exit-and-deletion.md", "## Evidence와 한계"),
        ("08-release-review.md", "## Evidence와 한계"),
    ],
}
EXIT_OWNS = {
    "EXIT-1": ["OWN-1", "OWN-3"],
    "EXIT-2": ["OWN-2", "OWN-3", "OWN-4", "OWN-6"],
    "EXIT-3": ["OWN-5"],
    "EXIT-4": ["OWN-1", "OWN-2", "OWN-6"],
}
EXIT_EVIDENCE: dict[str, list[tuple[str, str, str]]] = {
    "EXIT-1": [
        ("heading", "01-responsibility-matrix.md", "## Stage 4 — SaaS"),
        ("heading", "08-release-review.md", "## Scope"),
    ],
    "EXIT-2": [
        ("heading", "04-failure-and-recovery-plan.md", "## Stage 3 — FaaS"),
        ("heading", "05-event-and-idempotency-contract.md", "## Stage 3 — FaaS"),
        ("heading", "06-cost-quota-and-metering.md", "## Stage 3 — FaaS"),
        ("heading", "08-release-review.md", "## Open risks와 owner"),
    ],
    "EXIT-3": [
        ("heading", "03-identity-network-and-tenant-boundaries.md", "## Stage 4 — SaaS"),
        ("heading", "06-cost-quota-and-metering.md", "## Stage 4 — SaaS"),
        ("heading", "07-portability-exit-and-deletion.md", "## Stage 4 — SaaS"),
    ],
    "EXIT-4": [
        ("heading", "09-isolated-experiment.md", "## Evidence와 한계"),
        ("json_pointer", "evidence/local-model-report.json", "/summary"),
        ("json_pointer", "evidence-manifest.json", "/local_experiment"),
    ],
}
HANDOFF_BRANCHES = [
    "web-infra",
    "web-app",
    "database-systems",
    "distributed-services",
    "cybersecurity",
    "platform-engineering",
]
DOCUMENT_ARTIFACT_IDS = {
    "01-service-classification",
    "02-iaas-failure-domains",
    "03-managed-service-contract",
    "04-faas-event-lifecycle",
    "05-saas-tenant-isolation",
    "06-cost-and-exit",
}
SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
DECISION_PATTERN = re.compile(
    r"Decision: (?:APPROVE|APPROVE_WITH_CONDITIONS|DEFER|REJECT)"
)


@dataclass(frozen=True)
class VerificationError(Exception):
    code: str
    message: str
    exit_code: int


@dataclass
class ArtifactData:
    root: Path
    paths: dict[str, Path]
    raw: dict[str, bytes]
    text: dict[str, str]
    json_values: dict[str, Any]


class StrictJSONError(ValueError):
    pass


def _problem(code: str, message: str, exit_code: int) -> NoReturn:
    raise VerificationError(code, message, exit_code)


def _strict_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise StrictJSONError(f"duplicate key {key!r}")
        result[key] = value
    return result


def _invalid_constant(value: str) -> NoReturn:
    raise StrictJSONError(f"non-finite number {value!r}")


def _parse_json(raw: bytes, label: str, *, contract: bool) -> Any:
    code = "E_CONTRACT_JSON" if contract else "E_JSON"
    exit_code = HARNESS_EXIT if contract else ARTIFACT_EXIT
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        _problem(code, f"{label}: UTF-8 JSON required ({exc.reason})", exit_code)
    try:
        return json.loads(
            text,
            object_pairs_hook=_strict_object,
            parse_constant=_invalid_constant,
        )
    except (json.JSONDecodeError, StrictJSONError) as exc:
        _problem(code, f"{label}: invalid JSON ({exc})", exit_code)


def _validate_cli_root(path: Path) -> Path:
    try:
        mode = path.lstat().st_mode
    except (OSError, ValueError) as exc:
        _problem("E_ROOT", f"artifact root is unavailable: {exc}", HARNESS_EXIT)
    if stat.S_ISLNK(mode):
        _problem("E_ROOT", "artifact root must not be a symbolic link", HARNESS_EXIT)
    if not stat.S_ISDIR(mode):
        _problem("E_ROOT", "artifact root must be a directory", HARNESS_EXIT)
    try:
        return path.resolve(strict=True)
    except (OSError, RuntimeError, ValueError) as exc:
        _problem("E_ROOT", f"artifact root cannot be resolved: {exc}", HARNESS_EXIT)


def _validate_contract_file(path: Path) -> Path:
    try:
        mode = path.lstat().st_mode
    except (OSError, ValueError) as exc:
        _problem("E_CONTRACT_PATH", f"contract is unavailable: {exc}", HARNESS_EXIT)
    if stat.S_ISLNK(mode):
        _problem("E_CONTRACT_PATH", "contract must not be a symbolic link", HARNESS_EXIT)
    if not stat.S_ISREG(mode):
        _problem("E_CONTRACT_PATH", "contract must be a regular file", HARNESS_EXIT)
    try:
        return path.resolve(strict=True)
    except (OSError, RuntimeError, ValueError) as exc:
        _problem("E_CONTRACT_PATH", f"contract cannot be resolved: {exc}", HARNESS_EXIT)


def _relative_path(
    value: Any,
    label: str,
    *,
    code: str,
    exit_code: int,
) -> str:
    if not isinstance(value, str) or not value:
        _problem(code, f"{label}: non-empty path string required", exit_code)
    if "\x00" in value:
        _problem(code, f"{label}: NUL is forbidden", exit_code)
    if "\\" in value:
        _problem(code, f"{label}: backslash is forbidden", exit_code)
    pure = PurePosixPath(value)
    if pure.is_absolute():
        _problem(code, f"{label}: absolute path is forbidden", exit_code)
    parts = value.split("/")
    if any(part in {"", ".", ".."} for part in parts):
        _problem(code, f"{label}: path traversal or non-canonical segment", exit_code)
    return value


def _contract_relative(value: Any, label: str) -> str:
    return _relative_path(
        value,
        label,
        code="E_CONTRACT_SCHEMA",
        exit_code=HARNESS_EXIT,
    )


def _expect_dict(value: Any, label: str, *, code: str, exit_code: int) -> dict[str, Any]:
    if not isinstance(value, dict):
        _problem(code, f"{label}: object required", exit_code)
    return value


def _expect_exact_keys(
    value: dict[str, Any],
    expected: set[str],
    label: str,
    *,
    code: str,
    exit_code: int,
) -> None:
    actual = set(value)
    if actual != expected:
        missing = sorted(expected - actual)
        extra = sorted(actual - expected)
        _problem(code, f"{label}: missing={missing}, extra={extra}", exit_code)


def _string_list(
    value: Any,
    label: str,
    *,
    code: str,
    exit_code: int,
    allow_empty: bool = False,
) -> list[str]:
    if not isinstance(value, list) or (not allow_empty and not value):
        _problem(code, f"{label}: {'possibly empty ' if allow_empty else 'non-empty '}array required", exit_code)
    if any(not isinstance(item, str) or not item for item in value):
        _problem(code, f"{label}: every item must be a non-empty string", exit_code)
    if len(value) != len(set(value)):
        _problem(code, f"{label}: duplicate values are forbidden", exit_code)
    return value


def _validate_common_contract(contract: dict[str, Any], capstone: bool) -> None:
    code = "E_CONTRACT_SCHEMA"
    required_files = _string_list(
        contract["required_files"],
        "required_files",
        code=code,
        exit_code=HARNESS_EXIT,
    )
    for index, relative in enumerate(required_files):
        _contract_relative(relative, f"required_files[{index}]")

    forbidden = _string_list(
        contract["forbidden_tokens"],
        "forbidden_tokens",
        code=code,
        exit_code=HARNESS_EXIT,
    )
    if any("\x00" in token for token in forbidden):
        _problem(code, "forbidden_tokens: NUL is forbidden", HARNESS_EXIT)

    minimum = _expect_dict(
        contract["minimum_bytes"], "minimum_bytes", code=code, exit_code=HARNESS_EXIT
    )
    if set(minimum) != set(required_files):
        _problem(code, "minimum_bytes keys must exactly match required_files", HARNESS_EXIT)
    for relative, count in minimum.items():
        _contract_relative(relative, f"minimum_bytes[{relative!r}]")
        if type(count) is not int or count < 0:
            _problem(code, f"minimum_bytes[{relative!r}]: non-negative integer required", HARNESS_EXIT)

    headings = _expect_dict(
        contract["required_headings"], "required_headings", code=code, exit_code=HARNESS_EXIT
    )
    phrases = _expect_dict(
        contract["required_phrases"], "required_phrases", code=code, exit_code=HARNESS_EXIT
    )
    for mapping, label in ((headings, "required_headings"), (phrases, "required_phrases")):
        if not set(mapping).issubset(required_files):
            _problem(code, f"{label}: every key must be a required file", HARNESS_EXIT)
        for relative, values in mapping.items():
            _contract_relative(relative, f"{label} key")
            items = _string_list(values, f"{label}[{relative!r}]", code=code, exit_code=HARNESS_EXIT)
            if label == "required_headings":
                for heading in items:
                    if re.fullmatch(r"#{1,6}[ \t]+\S(?:.*\S)?", heading) is None:
                        _problem(code, f"invalid Markdown heading contract: {heading!r}", HARNESS_EXIT)

    if capstone:
        json_keys = _expect_dict(
            contract["json_required_keys"],
            "json_required_keys",
            code=code,
            exit_code=HARNESS_EXIT,
        )
        expected_json = {item for item in required_files if item.endswith(".json")}
        if set(json_keys) != expected_json:
            _problem(code, "json_required_keys must exactly cover required JSON files", HARNESS_EXIT)
        for relative, keys in json_keys.items():
            _string_list(keys, f"json_required_keys[{relative!r}]", code=code, exit_code=HARNESS_EXIT)


def _validate_contract_schema(value: Any) -> tuple[dict[str, Any], bool]:
    contract = _expect_dict(
        value, "contract", code="E_CONTRACT_SCHEMA", exit_code=HARNESS_EXIT
    )
    capstone = "project_id" in contract
    expected_keys = CAPSTONE_KEYS if capstone else GENERIC_KEYS
    _expect_exact_keys(
        contract,
        expected_keys,
        "contract",
        code="E_CONTRACT_SCHEMA",
        exit_code=HARNESS_EXIT,
    )
    _validate_common_contract(contract, capstone)
    if not capstone:
        if type(contract["schema_version"]) is not int or contract["schema_version"] != 1:
            _problem("E_CONTRACT_SCHEMA", "document schema_version must be 1", HARNESS_EXIT)
        if contract["artifact_id"] not in DOCUMENT_ARTIFACT_IDS:
            _problem("E_CONTRACT_SCHEMA", "unexpected document artifact_id", HARNESS_EXIT)
        if contract["workspace_source"] != "template":
            _problem("E_CONTRACT_SCHEMA", "workspace_source must be 'template'", HARNESS_EXIT)
        if contract["validator"] != "scripts/check_artifact.py":
            _problem("E_CONTRACT_SCHEMA", "unexpected document validator", HARNESS_EXIT)
        if contract["expected_starter_failures"] != ["E_UNFILLED"]:
            _problem("E_CONTRACT_SCHEMA", "starter failure must be exactly E_UNFILLED", HARNESS_EXIT)
        return contract, False

    if type(contract["schema_version"]) is not int or contract["schema_version"] != 2:
        _problem("E_CONTRACT_SCHEMA", "capstone schema_version must be 2", HARNESS_EXIT)
    if contract["project_id"] != CAPSTONE_ID:
        _problem("E_CONTRACT_SCHEMA", "unexpected capstone project_id", HARNESS_EXIT)
    if contract["workspace_source"] != "template":
        _problem("E_CONTRACT_SCHEMA", "workspace_source must be 'template'", HARNESS_EXIT)
    if contract["validator"] != "scripts/check_artifact.py":
        _problem("E_CONTRACT_SCHEMA", "unexpected capstone validator", HARNESS_EXIT)
    if contract["check_ids"] != CAPSTONE_CHECK_IDS:
        _problem("E_CONTRACT_SCHEMA", "capstone check_ids are not exact", HARNESS_EXIT)
    if contract["expected_starter_failures"] != ["E_UNFILLED"]:
        _problem("E_CONTRACT_SCHEMA", "starter failure must be exactly E_UNFILLED", HARNESS_EXIT)
    check_map = _expect_dict(
        contract["check_file_map"],
        "check_file_map",
        code="E_CONTRACT_SCHEMA",
        exit_code=HARNESS_EXIT,
    )
    if list(check_map) != CAPSTONE_CHECK_IDS:
        _problem("E_CONTRACT_SCHEMA", "check_file_map IDs and order are not exact", HARNESS_EXIT)
    mapped_files: list[str] = []
    for check_id, relative in check_map.items():
        mapped_files.append(_contract_relative(relative, f"check_file_map[{check_id!r}]"))
    if contract["required_files"] != mapped_files:
        _problem("E_CONTRACT_SCHEMA", "required_files must follow check_file_map order", HARNESS_EXIT)
    markdown_files = {item for item in mapped_files if item.endswith(".md")}
    if set(contract["required_headings"]) != markdown_files:
        _problem("E_CONTRACT_SCHEMA", "required_headings must exactly cover Markdown files", HARNESS_EXIT)
    if set(contract["required_phrases"]) != set(mapped_files):
        _problem("E_CONTRACT_SCHEMA", "required_phrases must exactly cover capstone files", HARNESS_EXIT)
    return contract, True


def _artifact_regular(root: Path, relative: str, *, missing_code: str = "E_MISSING") -> Path:
    current = root
    parts = relative.split("/")
    for index, part in enumerate(parts):
        current = current / part
        try:
            mode = current.lstat().st_mode
        except FileNotFoundError:
            _problem(missing_code, f"missing artifact path: {relative}", ARTIFACT_EXIT)
        except (OSError, ValueError) as exc:
            _problem("E_READ", f"cannot inspect {relative}: {exc}", ARTIFACT_EXIT)
        if stat.S_ISLNK(mode):
            _problem("E_SYMLINK", f"symbolic link is forbidden: {relative}", ARTIFACT_EXIT)
        final = index == len(parts) - 1
        if final and not stat.S_ISREG(mode):
            _problem("E_NONREGULAR", f"regular file required: {relative}", ARTIFACT_EXIT)
        if not final and not stat.S_ISDIR(mode):
            _problem("E_NONREGULAR", f"directory path component required: {relative}", ARTIFACT_EXIT)
    try:
        current.resolve(strict=True).relative_to(root)
    except (OSError, RuntimeError, ValueError):
        _problem("E_ESCAPE", f"artifact path escapes root: {relative}", ARTIFACT_EXIT)
    return current


def _scan_artifact_tree(root: Path) -> None:
    def on_error(error: OSError) -> NoReturn:
        _problem("E_READ", f"cannot scan artifact tree: {error}", ARTIFACT_EXIT)

    for current_text, directory_names, file_names in os.walk(
        root, followlinks=False, onerror=on_error
    ):
        current = Path(current_text)
        directory_names.sort()
        file_names.sort()
        for name in [*directory_names, *file_names]:
            path = current / name
            relative = path.relative_to(root).as_posix()
            try:
                mode = path.lstat().st_mode
            except OSError as exc:
                _problem("E_READ", f"cannot inspect {relative}: {exc}", ARTIFACT_EXIT)
            if stat.S_ISLNK(mode):
                _problem("E_SYMLINK", f"symbolic link is forbidden: {relative}", ARTIFACT_EXIT)
            if not (stat.S_ISDIR(mode) or stat.S_ISREG(mode)):
                _problem("E_NONREGULAR", f"non-regular artifact entry: {relative}", ARTIFACT_EXIT)


def _markdown_active_lines(text: str) -> list[str]:
    """Return lines outside HTML comments and CommonMark fenced code blocks."""

    text = re.sub(r"<!--.*?(?:-->|$)", "", text, flags=re.DOTALL)
    active: list[str] = []
    fence_character: str | None = None
    fence_length = 0
    for line in text.splitlines():
        if fence_character is not None:
            closing = re.fullmatch(
                rf" {{0,3}}{re.escape(fence_character)}{{{fence_length},}}[ \t]*",
                line,
            )
            if closing:
                fence_character = None
                fence_length = 0
            continue
        opening = re.fullmatch(r" {0,3}(`{3,}|~{3,})(.*)", line)
        if opening:
            marker = opening.group(1)
            info = opening.group(2)
            if marker[0] == "`" and "`" in info:
                active.append(line)
                continue
            fence_character = marker[0]
            fence_length = len(marker)
            continue
        active.append(line)
    return active


def _markdown_headings(text: str) -> set[str]:
    headings: set[str] = set()
    for line in _markdown_active_lines(text):
        candidate = line.rstrip(" \t")
        if re.fullmatch(r" {0,3}#{1,6}[ \t]+\S(?:.*\S)?", candidate):
            headings.add(candidate.lstrip(" "))
    return headings


def _load_artifact(root: Path, contract: dict[str, Any]) -> ArtifactData:
    required_files: list[str] = contract["required_files"]
    paths = {relative: _artifact_regular(root, relative) for relative in required_files}
    _scan_artifact_tree(root)

    raw: dict[str, bytes] = {}
    text: dict[str, str] = {}
    json_values: dict[str, Any] = {}
    for relative in required_files:
        try:
            payload = paths[relative].read_bytes()
        except OSError as exc:
            _problem("E_READ", f"cannot read {relative}: {exc}", ARTIFACT_EXIT)
        raw[relative] = payload
        try:
            text[relative] = payload.decode("utf-8")
        except UnicodeDecodeError as exc:
            _problem("E_ENCODING", f"{relative}: UTF-8 required ({exc.reason})", ARTIFACT_EXIT)

    # Parse every required JSON before recognizing an intentional starter marker.
    for relative in required_files:
        if relative.endswith(".json"):
            json_values[relative] = _parse_json(raw[relative], relative, contract=False)

    for relative in required_files:
        for token in contract["forbidden_tokens"]:
            if token in text[relative]:
                _problem("E_UNFILLED", f"{relative}: unresolved marker {token!r}", ARTIFACT_EXIT)

    for relative in required_files:
        minimum = contract["minimum_bytes"][relative]
        if len(raw[relative]) < minimum:
            _problem(
                "E_MINIMUM",
                f"{relative}: {len(raw[relative])} bytes is below {minimum}",
                ARTIFACT_EXIT,
            )

    for relative, required in contract["required_headings"].items():
        actual = _markdown_headings(text[relative])
        for heading in required:
            if heading not in actual:
                _problem("E_HEADING", f"{relative}: missing heading line {heading!r}", ARTIFACT_EXIT)

    for relative, required in contract["required_phrases"].items():
        for phrase in required:
            if phrase not in text[relative]:
                _problem("E_PHRASE", f"{relative}: missing required phrase {phrase!r}", ARTIFACT_EXIT)

    for relative, required in contract.get("json_required_keys", {}).items():
        value = json_values[relative]
        if not isinstance(value, dict):
            _problem("E_JSON_SCHEMA", f"{relative}: top-level object required", ARTIFACT_EXIT)
        for key in required:
            if key not in value:
                _problem("E_JSON_SCHEMA", f"{relative}: missing JSON key {key!r}", ARTIFACT_EXIT)

    return ArtifactData(root, paths, raw, text, json_values)


def _manifest_dict(value: Any, label: str) -> dict[str, Any]:
    return _expect_dict(value, label, code="E_MANIFEST_SCHEMA", exit_code=ARTIFACT_EXIT)


def _manifest_string(value: Any, label: str, *, code: str = "E_MANIFEST_SCHEMA") -> str:
    if not isinstance(value, str) or not value.strip():
        _problem(code, f"{label}: non-empty string required", ARTIFACT_EXIT)
    return value


def _manifest_list(
    value: Any,
    label: str,
    *,
    allow_empty: bool = False,
    code: str = "E_MANIFEST_SCHEMA",
) -> list[Any]:
    if not isinstance(value, list) or (not allow_empty and not value):
        _problem(code, f"{label}: non-empty array required", ARTIFACT_EXIT)
    return value


def _artifact_json(artifact: ArtifactData, relative: str) -> Any:
    if relative in artifact.json_values:
        return artifact.json_values[relative]
    path = _artifact_regular(artifact.root, relative, missing_code="E_REFERENCE")
    try:
        raw = path.read_bytes()
    except OSError as exc:
        _problem("E_REFERENCE", f"cannot read referenced file {relative}: {exc}", ARTIFACT_EXIT)
    value = _parse_json(raw, relative, contract=False)
    artifact.json_values[relative] = value
    return value


def _json_pointer(value: Any, pointer: str, label: str) -> Any:
    if not isinstance(pointer, str) or not pointer.startswith("/"):
        _problem("E_REFERENCE", f"{label}: absolute JSON pointer required", ARTIFACT_EXIT)
    current = value
    for raw_token in pointer[1:].split("/"):
        if re.search(r"~(?:[^01]|$)", raw_token):
            _problem("E_REFERENCE", f"{label}: invalid JSON pointer escape", ARTIFACT_EXIT)
        token = raw_token.replace("~1", "/").replace("~0", "~")
        if isinstance(current, dict):
            if token not in current:
                _problem("E_REFERENCE", f"{label}: dangling JSON pointer", ARTIFACT_EXIT)
            current = current[token]
        elif isinstance(current, list):
            if re.fullmatch(r"0|[1-9][0-9]*", token) is None:
                _problem("E_REFERENCE", f"{label}: invalid array index", ARTIFACT_EXIT)
            index = int(token)
            if index >= len(current):
                _problem("E_REFERENCE", f"{label}: dangling JSON pointer", ARTIFACT_EXIT)
            current = current[index]
        else:
            _problem("E_REFERENCE", f"{label}: JSON pointer crosses a scalar", ARTIFACT_EXIT)
    return current


def _resolve_evidence_ref(artifact: ArtifactData, ref: Any, label: str) -> None:
    item = _manifest_dict(ref, label)
    keys = set(item)
    if keys not in ({"file", "heading"}, {"file", "json_pointer"}):
        _problem("E_REFERENCE", f"{label}: file plus heading or json_pointer required", ARTIFACT_EXIT)
    relative = _relative_path(
        item["file"], label + ".file", code="E_REFERENCE", exit_code=ARTIFACT_EXIT
    )
    if relative not in artifact.paths:
        _problem("E_REFERENCE", f"{label}: referenced file is not contract-required", ARTIFACT_EXIT)
    _artifact_regular(artifact.root, relative, missing_code="E_REFERENCE")
    if "heading" in item:
        heading = _manifest_string(item["heading"], label + ".heading")
        if heading not in _markdown_headings(artifact.text[relative]):
            _problem("E_REFERENCE", f"{label}: dangling heading {heading!r}", ARTIFACT_EXIT)
    else:
        pointer = _manifest_string(item["json_pointer"], label + ".json_pointer")
        _json_pointer(_artifact_json(artifact, relative), pointer, label)


def _sha256_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _sha256_file(path: Path, label: str) -> str:
    try:
        return _sha256_bytes(path.read_bytes())
    except OSError as exc:
        _problem("E_LOCAL_REPORT", f"cannot hash {label}: {exc}", ARTIFACT_EXIT)


def _hash_string(value: Any, label: str) -> str:
    if not isinstance(value, str) or SHA256_PATTERN.fullmatch(value) is None:
        _problem("E_HASH", f"{label}: lowercase SHA-256 required", ARTIFACT_EXIT)
    return value


def _guide_file(guide_root: Path, value: Any, label: str) -> tuple[str, Path]:
    relative = _relative_path(value, label, code="E_LOCAL_REPORT", exit_code=ARTIFACT_EXIT)
    return relative, _artifact_regular(guide_root, relative, missing_code="E_LOCAL_REPORT")


def _validate_local_report(
    artifact: ArtifactData,
    local: dict[str, Any],
    guide_root: Path,
) -> None:
    expected_local_keys = {
        "budget",
        "credential_required",
        "network_required",
        "external_resources_created",
        "report",
        "report_sha256",
        "implementation_sha256",
        "contract_sha256",
    }
    _expect_exact_keys(
        local,
        expected_local_keys,
        "local_experiment",
        code="E_LOCAL_REPORT",
        exit_code=ARTIFACT_EXIT,
    )
    if type(local["budget"]) is not int or local["budget"] != 0:
        _problem("E_BUDGET", "local experiment budget must be exactly 0", ARTIFACT_EXIT)
    for key in ("credential_required", "network_required", "external_resources_created"):
        if local[key] is not False:
            _problem("E_CREDENTIAL", f"local_experiment.{key} must be false", ARTIFACT_EXIT)

    report_relative = _relative_path(
        local["report"],
        "local_experiment.report",
        code="E_LOCAL_REPORT",
        exit_code=ARTIFACT_EXIT,
    )
    if report_relative != "evidence/local-model-report.json":
        _problem("E_LOCAL_REPORT", "unexpected local report path", ARTIFACT_EXIT)
    report = _manifest_dict(_artifact_json(artifact, report_relative), "local report")
    report_hash = _hash_string(local["report_sha256"], "local_experiment.report_sha256")
    if _sha256_bytes(artifact.raw[report_relative]) != report_hash:
        _problem("E_HASH", "local report file hash is stale", ARTIFACT_EXIT)

    expected_report_keys = {
        "schema_version",
        "guide_id",
        "exercise_id",
        "implementation",
        "contract",
        "execution",
        "checks",
        "summary",
        "limitations",
    }
    _expect_exact_keys(
        report,
        expected_report_keys,
        "local report",
        code="E_LOCAL_REPORT",
        exit_code=ARTIFACT_EXIT,
    )
    if (
        type(report["schema_version"]) is not int
        or report["schema_version"] != 1
        or report["guide_id"] != "cloud-computing"
    ):
        _problem("E_LOCAL_REPORT", "unexpected local report guide schema", ARTIFACT_EXIT)
    if report["exercise_id"] != "07-local-cloud-model":
        _problem("E_LOCAL_REPORT", "unexpected local report exercise", ARTIFACT_EXIT)

    implementation = _manifest_dict(report["implementation"], "report.implementation")
    _expect_exact_keys(
        implementation,
        {"path", "sha256"},
        "report.implementation",
        code="E_LOCAL_REPORT",
        exit_code=ARTIFACT_EXIT,
    )
    expected_implementation = "exercises/07-local-cloud-model/reference/cloud_model.py"
    if implementation.get("path") != expected_implementation:
        _problem(
            "E_LOCAL_REPORT",
            f"report implementation path must be {expected_implementation}",
            ARTIFACT_EXIT,
        )
    implementation_relative, implementation_path = _guide_file(
        guide_root, implementation["path"], "report.implementation.path"
    )
    implementation_hash = _hash_string(implementation["sha256"], "report implementation hash")
    if _sha256_file(implementation_path, implementation_relative) != implementation_hash:
        _problem("E_HASH", "report implementation hash does not match current file", ARTIFACT_EXIT)
    if _hash_string(local["implementation_sha256"], "local implementation hash") != implementation_hash:
        _problem("E_HASH", "manifest and report implementation hashes differ", ARTIFACT_EXIT)

    report_contract = _manifest_dict(report["contract"], "report.contract")
    _expect_exact_keys(
        report_contract,
        {"path", "sha256", "check_ids"},
        "report.contract",
        code="E_LOCAL_REPORT",
        exit_code=ARTIFACT_EXIT,
    )
    expected_contract = "exercises/07-local-cloud-model/tests/contract.py"
    if report_contract.get("path") != expected_contract:
        _problem(
            "E_LOCAL_REPORT",
            f"report contract path must be {expected_contract}",
            ARTIFACT_EXIT,
        )
    contract_relative, model_contract_path = _guide_file(
        guide_root, report_contract["path"], "report.contract.path"
    )
    contract_hash = _hash_string(report_contract["sha256"], "report contract hash")
    if _sha256_file(model_contract_path, contract_relative) != contract_hash:
        _problem("E_HASH", "report contract hash does not match current file", ARTIFACT_EXIT)
    if _hash_string(local["contract_sha256"], "local contract hash") != contract_hash:
        _problem("E_HASH", "manifest and report contract hashes differ", ARTIFACT_EXIT)
    if report_contract["check_ids"] != MODEL_CHECK_IDS:
        _problem("E_CHECKS", "local report contract must list CM-001 through CM-013", ARTIFACT_EXIT)

    checks = _manifest_list(report["checks"], "report.checks", code="E_CHECKS")
    ids: list[str] = []
    cleanup_found = False
    for index, value in enumerate(checks):
        item = _manifest_dict(value, f"report.checks[{index}]")
        check_id = _manifest_string(
            item.get("id"), f"report.checks[{index}].id", code="E_CHECKS"
        )
        status_value = _manifest_string(
            item.get("status"), f"report.checks[{index}].status", code="E_CHECKS"
        )
        ids.append(check_id)
        if status_value.lower() != "pass":
            _problem("E_CHECKS", f"{check_id} did not PASS", ARTIFACT_EXIT)
        if check_id == "CM-011" and item.get("kind") == "cleanup":
            cleanup_found = True
    if ids != MODEL_CHECK_IDS:
        _problem("E_CHECKS", "local report checks must be exact and ordered CM-001..CM-013", ARTIFACT_EXIT)
    if not cleanup_found:
        _problem("E_CLEANUP", "CM-011 cleanup PASS evidence is required", ARTIFACT_EXIT)

    summary = _manifest_dict(report["summary"], "report.summary")
    expected_summary = {
        "total": 13,
        "passed": 13,
        "failed": 0,
        "errors": 0,
        "failed_ids": [],
        "result": "PASS",
    }
    for key, expected in expected_summary.items():
        if summary.get(key) != expected or (isinstance(expected, int) and type(summary.get(key)) is not int):
            _problem("E_CHECKS", f"report.summary.{key} is inconsistent", ARTIFACT_EXIT)

    execution = _manifest_dict(report["execution"], "report.execution")
    for key in ("network_required", "external_resources_created"):
        if execution.get(key) is not False:
            _problem("E_CREDENTIAL", f"report.execution.{key} must be false", ARTIFACT_EXIT)
    limitations = report["limitations"]
    if not isinstance(limitations, list) or not limitations or any(
        not isinstance(item, str) or not item.strip() for item in limitations
    ):
        _problem("E_LIMITATIONS", "non-empty local report limitations are required", ARTIFACT_EXIT)


def _validate_capstone(artifact: ArtifactData, guide_root: Path) -> None:
    manifest = _manifest_dict(artifact.json_values["evidence-manifest.json"], "manifest")
    expected_keys = {
        "schema_version",
        "project_id",
        "workload",
        "ordered_stages",
        "owns",
        "exit_capabilities",
        "local_experiment",
        "release_conditions",
        "implementation_owner_handoffs",
    }
    _expect_exact_keys(
        manifest,
        expected_keys,
        "manifest",
        code="E_MANIFEST_SCHEMA",
        exit_code=ARTIFACT_EXIT,
    )
    if (
        type(manifest["schema_version"]) is not int
        or manifest["schema_version"] != 1
        or manifest["project_id"] != CAPSTONE_ID
    ):
        _problem("E_MANIFEST_SCHEMA", "unexpected manifest schema or project_id", ARTIFACT_EXIT)
    _manifest_string(manifest["workload"], "manifest.workload")

    stages = _manifest_list(manifest["ordered_stages"], "ordered_stages")
    if len(stages) != len(STAGES):
        _problem("E_STAGE", "ordered_stages must contain exactly four stages", ARTIFACT_EXIT)
    for index, expected in enumerate(STAGES):
        item = _manifest_dict(stages[index], f"ordered_stages[{index}]")
        _expect_exact_keys(
            item,
            {"id", "order", "heading", "focus", "evidence_refs"},
            f"ordered_stages[{index}]",
            code="E_STAGE",
            exit_code=ARTIFACT_EXIT,
        )
        if type(item["order"]) is not int or (item["id"], item["order"], item["heading"]) != expected:
            _problem("E_STAGE", "stage order/id/heading must be exact", ARTIFACT_EXIT)
        _manifest_string(item["focus"], f"ordered_stages[{index}].focus")
        refs = _manifest_list(
            item["evidence_refs"], f"ordered_stages[{index}].evidence_refs", code="E_STAGE"
        )
        for ref_index, ref in enumerate(refs):
            _resolve_evidence_ref(artifact, ref, f"ordered_stages[{index}].evidence_refs[{ref_index}]")
        expected_refs = [
            {"file": relative, "heading": expected[2]} for relative in STAGE_FILES
        ]
        if refs != expected_refs:
            _problem(
                "E_STAGE",
                f"{expected[0]} must reference all nine stage headings in contract order",
                ARTIFACT_EXIT,
            )

    owns = _manifest_list(manifest["owns"], "owns")
    if [item.get("id") if isinstance(item, dict) else None for item in owns] != OWN_IDS:
        _problem("E_OWN", "owns must be exact and ordered OWN-1..OWN-6", ARTIFACT_EXIT)
    for index, value in enumerate(owns):
        item = _manifest_dict(value, f"owns[{index}]")
        _expect_exact_keys(
            item,
            {"id", "evidence_refs"},
            f"owns[{index}]",
            code="E_OWN",
            exit_code=ARTIFACT_EXIT,
        )
        refs = _manifest_list(item["evidence_refs"], f"owns[{index}].evidence_refs", code="E_OWN")
        for ref_index, ref in enumerate(refs):
            _resolve_evidence_ref(artifact, ref, f"owns[{index}].evidence_refs[{ref_index}]")
        expected_refs = [
            {"file": relative, "heading": heading}
            for relative, heading in OWN_EVIDENCE[item["id"]]
        ]
        if refs != expected_refs:
            _problem(
                "E_OWN",
                f"{item['id']} evidence mapping is incomplete or out of order",
                ARTIFACT_EXIT,
            )

    exits = _manifest_list(manifest["exit_capabilities"], "exit_capabilities")
    if [item.get("id") if isinstance(item, dict) else None for item in exits] != EXIT_IDS:
        _problem("E_EXIT", "exit_capabilities must be exact and ordered EXIT-1..EXIT-4", ARTIFACT_EXIT)
    for index, value in enumerate(exits):
        item = _manifest_dict(value, f"exit_capabilities[{index}]")
        _expect_exact_keys(
            item,
            {"id", "owns", "evidence_refs"},
            f"exit_capabilities[{index}]",
            code="E_EXIT",
            exit_code=ARTIFACT_EXIT,
        )
        linked_owns = _string_list(
            item["owns"],
            f"exit_capabilities[{index}].owns",
            code="E_EXIT",
            exit_code=ARTIFACT_EXIT,
        )
        if linked_owns != EXIT_OWNS[item["id"]]:
            _problem("E_EXIT", f"{item['id']} must map to its exact OWN set", ARTIFACT_EXIT)
        refs = _manifest_list(
            item["evidence_refs"], f"exit_capabilities[{index}].evidence_refs", code="E_EXIT"
        )
        for ref_index, ref in enumerate(refs):
            _resolve_evidence_ref(
                artifact, ref, f"exit_capabilities[{index}].evidence_refs[{ref_index}]"
            )
        expected_refs = [
            {"file": relative, reference_kind: target}
            for reference_kind, relative, target in EXIT_EVIDENCE[item["id"]]
        ]
        if refs != expected_refs:
            _problem(
                "E_EXIT",
                f"{item['id']} evidence mapping is incomplete or out of order",
                ARTIFACT_EXIT,
            )

    local = _manifest_dict(manifest["local_experiment"], "local_experiment")
    _validate_local_report(artifact, local, guide_root)

    conditions = _manifest_list(
        manifest["release_conditions"], "release_conditions", code="E_RELEASE"
    )
    condition_ids: list[str] = []
    condition_statuses: list[str] = []
    for index, value in enumerate(conditions):
        item = _manifest_dict(value, f"release_conditions[{index}]")
        _expect_exact_keys(
            item,
            {"id", "status", "owner", "due", "verification", "rollback"},
            f"release_conditions[{index}]",
            code="E_RELEASE",
            exit_code=ARTIFACT_EXIT,
        )
        for field in ("id", "status", "owner", "due", "verification", "rollback"):
            _manifest_string(
                item[field], f"release_conditions[{index}].{field}", code="E_RELEASE"
            )
        condition_ids.append(item["id"])
        condition_statuses.append(item["status"])
    if condition_ids != [f"RC-{number}" for number in range(1, 5)]:
        _problem("E_RELEASE", "release conditions must be exact and ordered RC-1..RC-4", ARTIFACT_EXIT)
    if any(status not in {"open", "closed"} for status in condition_statuses):
        _problem("E_RELEASE", "release condition status must be open or closed", ARTIFACT_EXIT)

    handoffs = _manifest_list(
        manifest["implementation_owner_handoffs"],
        "implementation_owner_handoffs",
        code="E_HANDOFF",
    )
    branches: list[str] = []
    for index, value in enumerate(handoffs):
        item = _manifest_dict(value, f"implementation_owner_handoffs[{index}]")
        _expect_exact_keys(
            item,
            {"branch", "owns"},
            f"implementation_owner_handoffs[{index}]",
            code="E_HANDOFF",
            exit_code=ARTIFACT_EXIT,
        )
        branches.append(
            _manifest_string(item["branch"], f"handoff[{index}].branch", code="E_HANDOFF")
        )
        _manifest_string(item["owns"], f"handoff[{index}].owns", code="E_HANDOFF")
    if branches != HANDOFF_BRANCHES:
        _problem("E_HANDOFF", "implementation handoffs are incomplete or out of order", ARTIFACT_EXIT)

    release_lines = _markdown_active_lines(artifact.text["08-release-review.md"])
    decisions = [line for line in release_lines if DECISION_PATTERN.fullmatch(line)]
    decision_prefix_lines = [line for line in release_lines if line.startswith("Decision:")]
    if len(decisions) != 1 or len(decision_prefix_lines) != 1:
        _problem("E_DECISION", "exactly one anchored valid release Decision is required", ARTIFACT_EXIT)
    if "open" in condition_statuses and decisions[0] != "Decision: APPROVE_WITH_CONDITIONS":
        _problem(
            "E_DECISION",
            "open release conditions require APPROVE_WITH_CONDITIONS",
            ARTIFACT_EXIT,
        )


def verify(root_path: Path, contract_path: Path) -> None:
    root = _validate_cli_root(root_path)
    contract_file = _validate_contract_file(contract_path)
    try:
        contract_raw = contract_file.read_bytes()
    except OSError as exc:
        _problem("E_CONTRACT_PATH", f"contract cannot be read: {exc}", HARNESS_EXIT)
    contract, capstone = _validate_contract_schema(
        _parse_json(contract_raw, "contract", contract=True)
    )
    artifact = _load_artifact(root, contract)
    if capstone:
        guide_root = Path(__file__).resolve().parents[1]
        _validate_capstone(artifact, guide_root)


def run(argv: Sequence[str]) -> int:
    if len(argv) != 2:
        print(
            "ARTIFACT ERROR [E_CLI] usage: check_artifact.py ROOT CONTRACT",
            file=sys.stderr,
        )
        return HARNESS_EXIT
    try:
        verify(Path(argv[0]), Path(argv[1]))
    except VerificationError as exc:
        print(f"ARTIFACT ERROR [{exc.code}] {exc.message}", file=sys.stderr)
        return exc.exit_code
    except Exception:
        print(
            "ARTIFACT ERROR [E_INTERNAL] unexpected verifier failure",
            file=sys.stderr,
        )
        return HARNESS_EXIT
    print("ARTIFACT RESULT: PASS")
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    return run(sys.argv[1:] if argv is None else argv)


if __name__ == "__main__":
    raise SystemExit(main())
