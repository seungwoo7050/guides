#!/usr/bin/env python3
"""Check a learner's deterministic firmware image audit submission."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
FIXTURES = ROOT / "fixtures"
BASE_FIXTURE = FIXTURES / "firmware-image.json"
FAILURE_FIXTURES = (
    FIXTURES / "image-overflow.json",
    FIXTURES / "vector-mismatch.json",
    FIXTURES / "ram-overflow.json",
)


class CheckError(RuntimeError):
    """The checker or input files could not be evaluated."""


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise CheckError(f"file does not exist: {path}") from exc
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise CheckError(f"cannot read JSON {path}: {exc}") from exc


def integer(value: Any, label: str) -> int:
    if isinstance(value, bool):
        raise CheckError(f"{label} must be an integer or 0x string")
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        try:
            return int(value, 0)
        except ValueError as exc:
            raise CheckError(f"{label} is not an integer: {value!r}") from exc
    raise CheckError(f"{label} must be an integer or 0x string")


def section_index(artifact: dict[str, Any]) -> dict[str, dict[str, Any]]:
    try:
        raw_sections = artifact["image"]["sections"]
    except (KeyError, TypeError) as exc:
        raise CheckError("fixture has no image.sections array") from exc
    if not isinstance(raw_sections, list):
        raise CheckError("fixture image.sections must be an array")
    sections: dict[str, dict[str, Any]] = {}
    for raw in raw_sections:
        if not isinstance(raw, dict) or not isinstance(raw.get("name"), str):
            raise CheckError("each fixture section needs a string name")
        sections[raw["name"]] = raw
    return sections


def analyze(artifact: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(artifact, dict):
        raise CheckError("artifact fixture must be an object")
    try:
        regions = artifact["memory_regions"]
        image = artifact["image"]
        reservations = artifact["runtime_reservations"]
        primary = regions["PRIMARY_SLOT"]
        sram = regions["SRAM"]
    except (KeyError, TypeError) as exc:
        raise CheckError(f"fixture contract is incomplete: {exc}") from exc
    if not all(isinstance(item, dict) for item in (regions, image, reservations, primary, sram)):
        raise CheckError("fixture regions, image, and reservations must be objects")

    sections = section_index(artifact)
    required = (".isr_vector", ".text", ".rodata", ".data", ".bss", ".noinit")
    missing = [name for name in required if name not in sections]
    if missing:
        raise CheckError(f"fixture is missing sections: {', '.join(missing)}")

    slot_origin = integer(primary.get("origin"), "PRIMARY_SLOT.origin")
    slot_size = integer(primary.get("length"), "PRIMARY_SLOT.length")
    flash_ends: list[int] = []
    normalized_sections: dict[str, dict[str, Any]] = {}
    for name, raw in sections.items():
        vma = integer(raw.get("vma"), f"{name}.vma")
        size = integer(raw.get("size"), f"{name}.size")
        lma_raw = raw.get("lma")
        lma = None if lma_raw is None else integer(lma_raw, f"{name}.lma")
        loadable = raw.get("loadable") is True
        if loadable and lma is None:
            raise CheckError(f"loadable section {name} needs an LMA")
        if loadable and lma is not None:
            flash_ends.append(lma + size)
        normalized_sections[name] = {
            "vma": vma,
            "lma": lma,
            "size": size,
            "initialization": raw.get("initialization"),
        }

    trailer = integer(image.get("trailer_bytes"), "image.trailer_bytes")
    flash_used = max(flash_ends) - slot_origin + trailer
    static_ram = sum(normalized_sections[name]["size"] for name in (".data", ".bss", ".noinit"))
    runtime_reserved = sum(integer(value, f"runtime_reservations.{name}") for name, value in reservations.items())
    ram_total = static_ram + runtime_reserved
    ram_size = integer(sram.get("length"), "SRAM.length")

    vector = image.get("vector")
    if not isinstance(vector, dict):
        raise CheckError("fixture image.vector must be an object")
    vector_vma = integer(vector.get("vma"), "image.vector.vma")
    initial_sp = integer(vector.get("initial_sp"), "image.vector.initial_sp")
    reset_handler = integer(vector.get("reset_handler"), "image.vector.reset_handler")
    entry_address = integer(image.get("entry_address"), "image.entry_address")
    sram_origin = integer(sram.get("origin"), "SRAM.origin")

    errors: list[str] = []
    vector_section = normalized_sections[".isr_vector"]
    if (
        vector_vma != slot_origin
        or vector_section["vma"] != vector_vma
        or vector_section["lma"] != vector_vma
        or reset_handler != entry_address
    ):
        errors.append("VECTOR_ADDRESS_MISMATCH")
    if flash_used > slot_size:
        errors.append("IMAGE_SLOT_OVERFLOW")
    if ram_total > ram_size or not (sram_origin < initial_sp <= sram_origin + ram_size):
        errors.append("RAM_BUDGET_OVERFLOW")

    data = normalized_sections[".data"]
    bss = normalized_sections[".bss"]
    return {
        "profile": artifact.get("profile", {}),
        "entry": {
            "vector_vma": vector_vma,
            "initial_sp": initial_sp,
            "entry_symbol": image.get("entry_symbol"),
            "entry_address": entry_address,
        },
        "sections": normalized_sections,
        "reset": {
            "data_copy": {"source": data["lma"], "destination": data["vma"], "size": data["size"]},
            "bss_zero": {"start": bss["vma"], "end": bss["vma"] + bss["size"]},
        },
        "budgets": {
            "flash": {
                "slot_origin": slot_origin,
                "slot_size": slot_size,
                "used": flash_used,
                "free": slot_size - flash_used,
            },
            "ram": {
                "region_size": ram_size,
                "static": static_ram,
                "runtime_reserved": runtime_reserved,
                "total": ram_total,
                "free": ram_size - ram_total,
            },
        },
        "errors": errors,
    }


def merge_patch(base: dict[str, Any], patch: dict[str, Any]) -> dict[str, Any]:
    result = copy.deepcopy(base)
    for key, value in patch.items():
        if key == "sections":
            if not isinstance(value, dict):
                raise CheckError("fixture sections patch must be an object")
            raw_sections = result.get(key)
            if not isinstance(raw_sections, list):
                raise CheckError("sections patch applied outside an array")
            indexed = {
                item.get("name"): item
                for item in raw_sections
                if isinstance(item, dict) and isinstance(item.get("name"), str)
            }
            for section_name, section_patch in value.items():
                if section_name not in indexed or not isinstance(section_patch, dict):
                    raise CheckError(f"invalid section patch: {section_name}")
                indexed[section_name].update(copy.deepcopy(section_patch))
        elif isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = merge_patch(result[key], value)
        else:
            result[key] = copy.deepcopy(value)
    return result


def load_failure(path: Path, base: dict[str, Any]) -> tuple[str, str]:
    scenario = load_json(path)
    if not isinstance(scenario, dict) or not isinstance(scenario.get("patch"), dict):
        raise CheckError(f"failure fixture must contain an object patch: {path}")
    if scenario.get("base") != BASE_FIXTURE.name:
        raise CheckError(f"failure fixture points to an unknown base: {path}")
    expected = scenario.get("expected_error")
    if not isinstance(expected, str):
        raise CheckError(f"failure fixture needs expected_error: {path}")
    actual_errors = analyze(merge_patch(base, scenario["patch"]))["errors"]
    if expected not in actual_errors:
        raise CheckError(f"failure fixture {path.name} does not produce {expected}: {actual_errors}")
    return path.name, expected


def nested(value: Any, *keys: str) -> Any:
    current = value
    for key in keys:
        if not isinstance(current, dict) or key not in current:
            return None
        current = current[key]
    return current


def run_checks(submission: dict[str, Any]) -> list[dict[str, Any]]:
    base = load_json(BASE_FIXTURE)
    if not isinstance(base, dict):
        raise CheckError("base fixture must be an object")
    oracle = analyze(base)
    if oracle["errors"]:
        raise CheckError(f"base fixture is invalid: {oracle['errors']}")
    failure_oracle = dict(load_failure(path, base) for path in FAILURE_FIXTURES)
    checks: list[dict[str, Any]] = []

    def record(check_id: str, passed: bool, expected: Any, actual: Any, message: str) -> None:
        checks.append({
            "id": check_id,
            "passed": passed,
            "expected": expected,
            "actual": actual,
            "message": message,
        })

    def equal(check_id: str, actual: Any, expected: Any, message: str) -> None:
        record(check_id, actual == expected, expected, actual, message)

    def address(check_id: str, actual: Any, expected: int, message: str) -> None:
        try:
            parsed = integer(actual, f"submission.{check_id}") if actual is not None else None
        except CheckError:
            parsed = None
        record(check_id, parsed == expected, f"0x{expected:08x}", actual, message)

    profile = oracle["profile"]
    equal("trace.source_revision", submission.get("source_revision"), profile.get("source_revision"), "audit identifies exact source")
    equal("trace.build_id", submission.get("build_id"), profile.get("build_id"), "audit identifies exact image")
    expected_hash = hashlib.sha256(BASE_FIXTURE.read_bytes()).hexdigest()
    equal("trace.artifact_sha256", submission.get("artifact_sha256"), expected_hash, "audit is tied to the supplied artifact manifest")

    for key in ("vector_vma", "initial_sp", "entry_address"):
        address(f"entry.{key}", nested(submission, "entry", key), oracle["entry"][key], f"entry field {key} matches vector/ELF evidence")
    equal("entry.entry_symbol", nested(submission, "entry", "entry_symbol"), oracle["entry"]["entry_symbol"], "entry symbol is exact")

    raw_sections = submission.get("sections")
    submitted_sections = {
        item.get("name"): item
        for item in raw_sections
        if isinstance(raw_sections, list) and isinstance(item, dict) and isinstance(item.get("name"), str)
    } if isinstance(raw_sections, list) else {}
    for name, expected_section in oracle["sections"].items():
        actual_section = submitted_sections.get(name, {})
        for field in ("vma", "size"):
            address(f"section.{name}.{field}", actual_section.get(field), expected_section[field], f"{name} {field} matches the artifact")
        expected_lma = expected_section["lma"]
        if expected_lma is None:
            equal(f"section.{name}.lma", actual_section.get("lma"), None, f"{name} has no load image bytes")
        else:
            address(f"section.{name}.lma", actual_section.get("lma"), expected_lma, f"{name} LMA matches the artifact")
        equal(
            f"section.{name}.initialization",
            actual_section.get("initialization"),
            expected_section["initialization"],
            f"{name} initialization owner/policy is explicit",
        )

    for phase, fields in oracle["reset"].items():
        for field, expected in fields.items():
            address(f"reset.{phase}.{field}", nested(submission, "reset", phase, field), expected, f"startup {phase} {field} matches linker boundaries")
    for memory_kind, fields in oracle["budgets"].items():
        for field, expected in fields.items():
            address(f"budget.{memory_kind}.{field}", nested(submission, "budgets", memory_kind, field), expected, f"{memory_kind} {field} includes all declared consumers")

    submitted_failures = submission.get("failure_expectations")
    submitted_failures = submitted_failures if isinstance(submitted_failures, dict) else {}
    for fixture_name, expected_error in failure_oracle.items():
        equal(
            f"failure.{fixture_name}",
            submitted_failures.get(fixture_name),
            expected_error,
            "mutated artifact must fail with the representative public error",
        )

    limitations = submission.get("limitations")
    joined = " ".join(str(item).lower() for item in limitations) if isinstance(limitations, list) else ""
    record("limitations.runtime-stack", "stack" in joined and ("watermark" in joined or "runtime" in joined), "runtime stack limitation", limitations, "static image audit does not prove runtime stack use")
    record("limitations.target-behavior", "timing" in joined and "electrical" in joined, "timing and electrical limitation", limitations, "artifact audit does not prove target timing/electrical behavior")
    return checks


def emit(result: dict[str, Any], as_json: bool) -> None:
    if as_json:
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
        return
    if result["status"] == "error":
        print(f"ERROR: {result['error']}", file=sys.stderr)
        return
    for check in result["checks"]:
        if not check["passed"]:
            print(f"FAIL {check['id']}: {check['message']}")
            print(f"  expected: {check['expected']!r}")
            print(f"  actual:   {check['actual']!r}")
    summary = result["summary"]
    print(f"{result['status'].upper()} {result['exercise']} passed={summary['passed']} failed={summary['failed']}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--submission", required=True, type=Path)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    try:
        submission = load_json(args.submission)
        if not isinstance(submission, dict):
            raise CheckError("submission must be a JSON object")
        checks = run_checks(submission)
    except CheckError as exc:
        result = {"exercise": "01-image-and-memory-audit", "status": "error", "error": str(exc)}
        emit(result, args.json)
        return 2
    failed = sum(not item["passed"] for item in checks)
    result = {
        "exercise": "01-image-and-memory-audit",
        "submission": str(args.submission),
        "status": "pass" if failed == 0 else "fail",
        "checks": checks,
        "summary": {"passed": len(checks) - failed, "failed": failed},
    }
    emit(result, args.json)
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
