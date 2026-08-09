#!/usr/bin/env python3
"""Validate the internal developer platform capstone evidence dossier."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import stat
import subprocess
import sys
import tempfile
from pathlib import Path, PurePosixPath
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT / "projects/internal-developer-platform"
CONTRACT_PATH = PROJECT / "contract.json"
MANIFEST_NAME = "evidence-manifest.json"
HARNESS_EXIT = 2
HEADING = re.compile(r"^#{1,6}\s+(.+?)\s*#*\s*$")
FENCE = re.compile(r"^\s*(`{3,}|~{3,})")


class CapstoneError(RuntimeError):
    def __init__(self, code: str, message: str, harness: bool = False):
        super().__init__(message)
        self.code = code
        self.message = message
        self.harness = harness


def strict_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def reject_constant(value: str) -> None:
    raise ValueError(f"non-finite JSON value: {value}")


def parse_json(path: Path, code: str, harness: bool = False) -> dict[str, Any]:
    try:
        value = json.loads(
            path.read_text(encoding="utf-8"),
            object_pairs_hook=strict_object,
            parse_constant=reject_constant,
        )
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as error:
        raise CapstoneError(code, f"cannot parse {display(path)}: {error}", harness) from error
    if not isinstance(value, dict):
        raise CapstoneError(code, f"{display(path)} top level must be an object", harness)
    return value


def display(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def external_temp_root(candidates: Iterable[Path] | None = None) -> Path:
    choices = list(candidates) if candidates is not None else [
        Path(tempfile.gettempdir()), Path('/private/tmp'), Path('/tmp'),
    ]
    inspected: set[Path] = set()
    for candidate in choices:
        try:
            resolved = candidate.resolve(strict=True)
        except (OSError, RuntimeError):
            continue
        if resolved in inspected:
            continue
        inspected.add(resolved)
        if not resolved.is_dir():
            continue
        if resolved == ROOT or ROOT in resolved.parents:
            continue
        return resolved
    raise CapstoneError("E_MODEL_RUN", "no temporary directory outside the repository is available")


def digest(path: Path) -> str:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError as error:
        raise CapstoneError("E_PATH", f"cannot hash {display(path)}: {error}", True) from error


def inspect_no_symlink(base: Path, target: Path, code: str, harness: bool) -> None:
    try:
        relative = target.relative_to(base)
    except ValueError as error:
        raise CapstoneError(code, f"path escapes allowed root: {target}", harness) from error
    current = base
    for part in relative.parts:
        current = current / part
        try:
            metadata = current.lstat()
        except OSError as error:
            raise CapstoneError(code, f"cannot inspect {display(current)}: {error}", harness) from error
        if stat.S_ISLNK(metadata.st_mode):
            raise CapstoneError(code, f"symlink is not allowed: {display(current)}", harness)


def artifact_directory(raw: str) -> Path:
    candidate = Path(raw)
    if not candidate.is_absolute():
        candidate = ROOT / candidate
    absolute = candidate.absolute()
    try:
        resolved = absolute.resolve(strict=True)
    except (OSError, RuntimeError) as error:
        raise CapstoneError("E_PATH", f"artifact directory does not exist: {raw}", True) from error
    try:
        resolved.relative_to(ROOT)
    except ValueError as error:
        raise CapstoneError("E_PATH", "artifact directory must remain inside the repository", True) from error
    inspect_no_symlink(ROOT, absolute, "E_PATH", True)
    if not resolved.is_dir():
        raise CapstoneError("E_PATH", "artifact path must be a directory", True)
    return resolved


def submission_file(artifact: Path, raw: str) -> Path:
    pure = PurePosixPath(raw)
    if pure.is_absolute() or not pure.parts or any(part in {"", ".", ".."} for part in pure.parts):
        raise CapstoneError("E_REFERENCE", f"unsafe artifact-relative path: {raw}")
    candidate = artifact.joinpath(*pure.parts)
    try:
        resolved = candidate.resolve(strict=True)
    except (OSError, RuntimeError) as error:
        raise CapstoneError("E_REFERENCE", f"referenced file does not exist: {raw}") from error
    inspect_no_symlink(artifact, candidate, "E_REFERENCE", False)
    if not resolved.is_file():
        raise CapstoneError("E_REFERENCE", f"referenced path is not a regular file: {raw}")
    return resolved


def root_file(raw: str) -> Path:
    pure = PurePosixPath(raw)
    if pure.is_absolute() or not pure.parts or any(part in {"", ".", ".."} for part in pure.parts):
        raise CapstoneError("E_MODEL_PATH", f"unsafe repository-relative path: {raw}")
    candidate = ROOT.joinpath(*pure.parts)
    try:
        resolved = candidate.resolve(strict=True)
    except (OSError, RuntimeError) as error:
        raise CapstoneError("E_MODEL_PATH", f"model source does not exist: {raw}") from error
    inspect_no_symlink(ROOT, candidate, "E_MODEL_PATH", False)
    if not resolved.is_file():
        raise CapstoneError("E_MODEL_PATH", f"model source is not a regular file: {raw}")
    return resolved


def read_text(path: Path, code: str) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as error:
        raise CapstoneError(code, f"cannot read {display(path)}: {error}") from error


def headings(text: str) -> list[str]:
    found: list[str] = []
    fence_character: str | None = None
    fence_length = 0
    for line in text.splitlines():
        fence = FENCE.match(line)
        if fence:
            marker = fence.group(1)
            if fence_character is None:
                fence_character = marker[0]
                fence_length = len(marker)
            elif marker[0] == fence_character and len(marker) >= fence_length:
                fence_character = None
                fence_length = 0
            continue
        if fence_character is not None:
            continue
        match = HEADING.match(line)
        if match:
            found.append(match.group(1).strip())
    if fence_character is not None:
        raise CapstoneError("E_CONTENT", "Markdown contains an unclosed code fence")
    return found


def resolve_pointer(document: Any, pointer: str) -> Any:
    if pointer == "":
        return document
    if not isinstance(pointer, str) or not pointer.startswith("/"):
        raise KeyError("JSON pointer must start with /")
    current = document
    for encoded in pointer[1:].split("/"):
        token = encoded.replace("~1", "/").replace("~0", "~")
        if "~" in token and re.search(r"~(?![01])", encoded):
            raise KeyError("invalid JSON pointer escape")
        if isinstance(current, dict):
            if token not in current:
                raise KeyError(token)
            current = current[token]
        elif isinstance(current, list):
            if not token.isdigit() or (len(token) > 1 and token.startswith("0")):
                raise KeyError(token)
            index = int(token)
            if index >= len(current):
                raise KeyError(token)
            current = current[index]
        else:
            raise KeyError(token)
    return current


def validate_required_files(artifact: Path, contract: dict[str, Any]) -> dict[str, Path]:
    paths: dict[str, Path] = {}
    for raw in contract.get("required_files", []):
        try:
            paths[raw] = submission_file(artifact, raw)
        except CapstoneError as error:
            raise CapstoneError("E_REQUIRED", error.message) from error
    return paths


def validate_unfilled(paths: dict[str, Path], contract: dict[str, Any]) -> None:
    tokens = contract.get("forbidden_tokens", [])
    findings: list[str] = []
    for raw, path in paths.items():
        text = read_text(path, "E_CONTENT")
        for token in tokens:
            if token in text:
                findings.append(f"{raw}:{token}")
    if findings:
        raise CapstoneError("E_UNFILLED", "unfinished markers found: " + ", ".join(findings))


def validate_markdown(paths: dict[str, Path], contract: dict[str, Any]) -> None:
    identifiers = list(contract.get("identifiers", {}).values())
    for raw, expected in contract.get("required_headings", {}).items():
        text = read_text(paths[raw], "E_CONTENT")
        actual = headings(text)
        missing = [heading for heading in expected if actual.count(heading) != 1]
        if missing:
            raise CapstoneError(
                "E_HEADING", f"{raw} must contain each required heading exactly once: {', '.join(missing)}"
            )
        absent_ids = [identifier for identifier in identifiers if identifier not in text]
        if absent_ids:
            raise CapstoneError("E_IDENTIFIERS", f"{raw} is missing shared IDs: {', '.join(absent_ids)}")


def validate_evidence_ref(artifact: Path, item: Any, label: str) -> None:
    if not isinstance(item, dict) or not isinstance(item.get("file"), str):
        raise CapstoneError("E_REFERENCE", f"{label} must declare a file")
    has_heading = isinstance(item.get("heading"), str)
    has_pointer = isinstance(item.get("json_pointer"), str)
    if has_heading == has_pointer:
        raise CapstoneError("E_REFERENCE", f"{label} must declare exactly one heading or json_pointer")
    path = submission_file(artifact, item["file"])
    if has_heading:
        if path.suffix != ".md":
            raise CapstoneError("E_REFERENCE", f"{label} heading target must be Markdown")
        if headings(read_text(path, "E_REFERENCE")).count(item["heading"]) != 1:
            raise CapstoneError(
                "E_REFERENCE", f"{label} heading does not resolve: {item['file']}#{item['heading']}"
            )
    else:
        if path.suffix != ".json":
            raise CapstoneError("E_REFERENCE", f"{label} JSON pointer target must be JSON")
        document = parse_json(path, "E_REFERENCE")
        try:
            target = resolve_pointer(document, item["json_pointer"])
        except KeyError as error:
            raise CapstoneError(
                "E_REFERENCE", f"{label} JSON pointer does not resolve: {item['file']}{item['json_pointer']}"
            ) from error
        if item["file"] == contract_model_path() and (
            not isinstance(target, dict) or target.get("status") != "pass" or target.get("id") not in model_check_ids()
        ):
            raise CapstoneError("E_REFERENCE", f"{label} model pointer must resolve to a passing public check")


_CONTRACT: dict[str, Any] | None = None


def contract_model_path() -> str:
    assert _CONTRACT is not None
    return str(_CONTRACT["model"]["report_path"])


def model_check_ids() -> list[str]:
    assert _CONTRACT is not None
    return list(_CONTRACT["model"]["check_ids"])


def validate_trace_group(
    artifact: Path, manifest: dict[str, Any], contract: dict[str, Any], name: str
) -> None:
    expected = contract.get(name, {})
    actual = manifest.get(name)
    if not isinstance(actual, dict) or set(actual) != set(expected):
        raise CapstoneError("E_TRACE", f"manifest {name} keys must be exactly: {', '.join(expected)}")
    for identifier, catalog_text in expected.items():
        entry = actual[identifier]
        if not isinstance(entry, dict) or entry.get("catalog_text") != catalog_text:
            raise CapstoneError("E_TRACE", f"{identifier} must preserve the catalog contract text")
        evidence = entry.get("evidence")
        if not isinstance(evidence, list) or len(evidence) < 2:
            raise CapstoneError("E_TRACE", f"{identifier} needs heading and JSON-pointer evidence")
        kinds = {"heading": False, "json_pointer": False}
        for index, item in enumerate(evidence):
            validate_evidence_ref(artifact, item, f"{identifier}.evidence[{index}]")
            if isinstance(item, dict):
                for kind in kinds:
                    kinds[kind] = kinds[kind] or kind in item
        if not all(kinds.values()):
            raise CapstoneError("E_TRACE", f"{identifier} needs both file-heading and JSON-pointer evidence")


def validate_failure_scenarios(artifact: Path, manifest: dict[str, Any], contract: dict[str, Any]) -> None:
    expected_ids = contract.get("failure_scenarios", [])
    scenarios = manifest.get("failure_scenarios")
    if not isinstance(scenarios, list) or [item.get("id") for item in scenarios if isinstance(item, dict)] != expected_ids:
        raise CapstoneError("E_FAILURE_SCENARIOS", "manifest must contain FS-01..FS-08 exactly once and in order")
    heading_prefixes = {
        heading.split(" — ", 1)[0]: heading.split(" — ", 1)[1]
        for heading in contract["required_headings"]["09-evidence.md"]
        if heading.startswith("FS-") and " — " in heading
    }
    for scenario in scenarios:
        identifier = scenario["id"]
        if scenario.get("title") != heading_prefixes.get(identifier):
            raise CapstoneError("E_FAILURE_SCENARIOS", f"{identifier} title differs from the public contract")
        evidence = scenario.get("evidence")
        if not isinstance(evidence, list) or len(evidence) < 2:
            raise CapstoneError("E_FAILURE_SCENARIOS", f"{identifier} needs heading and model evidence")
        kinds = {"heading": False, "json_pointer": False}
        for index, item in enumerate(evidence):
            validate_evidence_ref(artifact, item, f"{identifier}.evidence[{index}]")
            if isinstance(item, dict):
                for kind in kinds:
                    kinds[kind] = kinds[kind] or kind in item
        if not all(kinds.values()):
            raise CapstoneError("E_FAILURE_SCENARIOS", f"{identifier} needs both evidence kinds")


def validate_model(artifact: Path, manifest: dict[str, Any], contract: dict[str, Any]) -> None:
    expected = contract.get("model", {})
    declared = manifest.get("model_report")
    if not isinstance(declared, dict):
        raise CapstoneError("E_MODEL", "manifest model_report is required")
    for key in ("path", "sha256", "check_ids"):
        expected_key = "report_path" if key == "path" else "report_sha256" if key == "sha256" else key
        if declared.get(key) != expected.get(expected_key):
            raise CapstoneError("E_MODEL_HASH", f"manifest model_report.{key} differs from contract")
    for group in ("implementation", "contract"):
        value = declared.get(group)
        if not isinstance(value, dict):
            raise CapstoneError("E_MODEL_HASH", f"manifest model_report.{group} is required")
        if value.get("path") != expected.get(f"{group}_path") or value.get("sha256") != expected.get(
            f"{group}_sha256"
        ):
            raise CapstoneError("E_MODEL_HASH", f"manifest {group} path/hash differs from contract")

    report_path = submission_file(artifact, expected["report_path"])
    if digest(report_path) != expected["report_sha256"]:
        raise CapstoneError("E_MODEL_HASH", "stored model report SHA-256 differs from contract")
    implementation_path = root_file(expected["implementation_path"])
    public_contract_path = root_file(expected["contract_path"])
    if digest(implementation_path) != expected["implementation_sha256"]:
        raise CapstoneError("E_MODEL_HASH", "model reference implementation SHA-256 differs from contract")
    if digest(public_contract_path) != expected["contract_sha256"]:
        raise CapstoneError("E_MODEL_HASH", "model public contract SHA-256 differs from contract")

    report = parse_json(report_path, "E_MODEL")
    if report.get("implementation") != {
        "path": expected["implementation_path"],
        "sha256": expected["implementation_sha256"],
    }:
        raise CapstoneError("E_MODEL", "stored report identifies a different implementation")
    report_contract = report.get("contract")
    if not isinstance(report_contract, dict) or report_contract.get("path") != expected["contract_path"] or report_contract.get(
        "sha256"
    ) != expected["contract_sha256"] or report_contract.get("check_ids") != expected["check_ids"]:
        raise CapstoneError("E_MODEL", "stored report identifies a different public contract")
    checks = report.get("checks")
    if not isinstance(checks, list) or [item.get("id") for item in checks if isinstance(item, dict)] != expected["check_ids"]:
        raise CapstoneError("E_MODEL", "stored report check IDs differ from PE-001..PE-010")
    if any(not isinstance(item, dict) or item.get("status") != "pass" for item in checks):
        raise CapstoneError("E_MODEL", "stored report contains a non-passing public check")
    summary = report.get("summary")
    if not isinstance(summary, dict) or summary.get("result") != "PASS" or summary.get("passed") != len(checks):
        raise CapstoneError("E_MODEL", "stored report summary is not a complete PASS")

    verifier = ROOT / "scripts/verify_platform_model.py"
    environment = os.environ.copy()
    for key in ("PYTHONHOME", "PYTHONPATH", "PYTHONSTARTUP", "PYTHONINSPECT"):
        environment.pop(key, None)
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    environment["PYTHONNOUSERSITE"] = "1"
    environment["PYTHONHASHSEED"] = "0"
    try:
        with tempfile.TemporaryDirectory(prefix="capstone-model-", dir=external_temp_root()) as directory:
            regenerated_path = Path(directory) / "report.json"
            completed = subprocess.run(
                [
                    sys.executable,
                    str(verifier),
                    "--implementation",
                    expected["implementation_path"],
                    "--report",
                    str(regenerated_path),
                ],
                cwd=ROOT,
                env=environment,
                text=True,
                capture_output=True,
                timeout=10,
                check=False,
            )
            if completed.returncode != 0:
                raise CapstoneError("E_MODEL_RUN", f"model validator exited {completed.returncode}")
            regenerated = parse_json(regenerated_path, "E_MODEL_RUN")
    except subprocess.TimeoutExpired as error:
        raise CapstoneError("E_MODEL_RUN", "model validator exceeded 10 seconds") from error
    except OSError as error:
        raise CapstoneError("E_MODEL_RUN", f"cannot execute model validator: {error}") from error
    if regenerated != report:
        raise CapstoneError("E_MODEL_HASH", "stored model report does not match a fresh deterministic run")


def validate(artifact: Path, contract: dict[str, Any]) -> None:
    paths = validate_required_files(artifact, contract)
    validate_unfilled(paths, contract)
    validate_markdown(paths, contract)
    manifest = parse_json(paths[MANIFEST_NAME], "E_MANIFEST")
    if manifest.get("schema_version") != 1:
        raise CapstoneError("E_MANIFEST", "manifest schema_version must be 1")
    if manifest.get("identifiers") != contract.get("identifiers"):
        raise CapstoneError("E_IDENTIFIERS", "manifest identifiers differ from the scenario contract")
    validate_trace_group(artifact, manifest, contract, "owns")
    validate_trace_group(artifact, manifest, contract, "exit_capabilities")
    validate_failure_scenarios(artifact, manifest, contract)
    human_review = manifest.get("human_review")
    if not isinstance(human_review, dict) or human_review.get("required_decisions") != list(
        contract.get("exit_capabilities", {})
    ):
        raise CapstoneError("E_HUMAN_REVIEW", "human review must retain explicit EXIT-1..EXIT-3 decisions")
    if human_review.get("rubric") != contract.get("rubric_path"):
        raise CapstoneError("E_HUMAN_REVIEW", "human review must identify the canonical rubric")
    root_file(str(contract.get("rubric_path", "")))
    validate_evidence_ref(artifact, human_review.get("limitations_heading"), "human_review.limitations_heading")
    validate_model(artifact, manifest, contract)


def validate_repository_contract(contract: dict[str, Any]) -> None:
    scenario_path = root_file(str(contract.get("scenario_identifiers_path", "")))
    scenario = parse_json(scenario_path, "E_CONTRACT", True)
    scenario.pop("schema_version", None)
    if scenario != contract.get("identifiers"):
        raise CapstoneError("E_CONTRACT", "scenario identifiers differ from capstone contract", True)
    root_file(str(contract.get("rubric_path", "")))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("artifact", help="capstone dossier directory inside this repository")
    arguments = parser.parse_args(argv)
    global _CONTRACT
    try:
        _CONTRACT = parse_json(CONTRACT_PATH, "E_CONTRACT", True)
        validate_repository_contract(_CONTRACT)
        artifact = artifact_directory(arguments.artifact)
        validate(artifact, _CONTRACT)
    except CapstoneError as error:
        label = "ERROR" if error.harness else "FAIL"
        print(f"CAPSTONE {label} [{error.code}] {error.message}", file=sys.stderr)
        return HARNESS_EXIT if error.harness else 1
    print(
        "CAPSTONE PASS owns=5 exit_capabilities=3 failure_scenarios=8 "
        "model_checks=10 human_review=required"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
