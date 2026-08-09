#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
import re
import tempfile
import sys
from pathlib import Path
from types import ModuleType

ROOT = Path(__file__).resolve().parents[1]
EXPECTED_FILES = {
    "dataset.csv",
    "schema.json",
    "split_manifest.csv",
    "split-policy.json",
    "dataset-card.md",
    "fixture-manifest.json",
}


def load_module(path: Path, name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise AssertionError(f"CSV has no header: {path}")
        return list(reader.fieldnames), list(reader)


def validate(fixtures: Path) -> dict[str, object]:
    fixtures = fixtures.resolve()
    missing = sorted(name for name in EXPECTED_FILES if not (fixtures / name).is_file())
    if missing:
        raise AssertionError(f"missing fixture files: {missing}")

    metadata = json.loads((fixtures / "fixture-manifest.json").read_text(encoding="utf-8"))
    if metadata.get("generator_version") != 1 or metadata.get("seed") != 7050:
        raise AssertionError("unexpected generator version or seed")

    for name, expected in metadata.get("files", {}).items():
        actual = sha256(fixtures / name)
        if actual != expected:
            raise AssertionError(f"checksum mismatch for {name}: {actual} != {expected}")

    schema = json.loads((fixtures / "schema.json").read_text(encoding="utf-8"))
    fieldnames, rows = read_csv(fixtures / "dataset.csv")
    manifest_fields, manifest_rows = read_csv(fixtures / "split_manifest.csv")
    schema_names = [column["name"] for column in schema.get("columns", [])]
    if fieldnames != schema_names:
        raise AssertionError("dataset header and schema column order differ")
    if manifest_fields != ["row_id", "entity_id", "split"]:
        raise AssertionError("unexpected split manifest header")
    if len(rows) != metadata.get("row_count"):
        raise AssertionError("row_count does not match fixture manifest")
    if len({row["entity_id"] for row in rows}) != metadata.get("entity_count"):
        raise AssertionError("entity_count does not match fixture manifest")

    row_pattern = re.compile(r"^customer-\d{4}-2025-0[1-3]$")
    for row in rows:
        if not row_pattern.fullmatch(row["row_id"]):
            raise AssertionError(f"invalid row_id: {row['row_id']}")
        if row["churn_30d"] not in {"0", "1"} or row["future_refund_30d"] not in {"0", "1"}:
            raise AssertionError(f"invalid binary value for {row['row_id']}")
        for key in ("monthly_usage_hours", "usage_change_90d"):
            value = float(row[key])
            if value != value or value in {float("inf"), float("-inf")}:
                raise AssertionError(f"non-finite value in {key}")

    manifest_entity = {entry["row_id"]: entry["entity_id"] for entry in manifest_rows}
    for row in rows:
        if manifest_entity.get(row["row_id"]) != row["entity_id"]:
            raise AssertionError(f"manifest entity mismatch for {row['row_id']}")

    forbidden = [
        column["name"]
        for column in schema["columns"]
        if column.get("role") == "forbidden-feature" or (
            column.get("role") == "feature" and not column.get("allowed_for_prediction", False)
        )
    ]
    if forbidden != ["future_refund_30d"]:
        raise AssertionError(f"unexpected forbidden features: {forbidden}")

    split_module = load_module(ROOT / "examples" / "split_audit.py", "guide_split_audit")
    result = split_module.audit_rows(rows, manifest_rows)
    if not result.valid:
        raise AssertionError(f"invalid split audit: {result.to_dict()}")
    if any(value <= 0 for value in result.rows.values()):
        raise AssertionError("all splits must contain rows")
    if any(value <= 0 for value in result.positives.values()):
        raise AssertionError("all splits must contain positive labels")

    policy = json.loads((fixtures / "split-policy.json").read_text(encoding="utf-8"))
    if policy.get("group_key") != "entity_id":
        raise AssertionError("split policy must group by entity_id")

    return {
        "rows": len(rows),
        "entities": len({row["entity_id"] for row in rows}),
        "split_rows": result.rows,
        "split_entities": result.entities,
        "positives": result.positives,
    }


def compare_regeneration(fixtures: Path) -> None:
    generator = load_module(ROOT / "scripts" / "generate-fixtures.py", "guide_generate_fixtures")
    with tempfile.TemporaryDirectory(prefix="ml-fixtures-") as temporary:
        regenerated = Path(temporary)
        generator.generate(regenerated)
        for name in sorted(EXPECTED_FILES):
            original = (fixtures / name).read_bytes()
            candidate = (regenerated / name).read_bytes()
            if original != candidate:
                raise AssertionError(f"fixture is not reproducible: {name}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fixtures-dir", type=Path, default=ROOT / "exercises/model-lifecycle/fixtures")
    parser.add_argument("--skip-regeneration", action="store_true")
    args = parser.parse_args()
    try:
        summary = validate(args.fixtures_dir)
        if not args.skip_regeneration:
            compare_regeneration(args.fixtures_dir.resolve())
    except (AssertionError, ValueError, KeyError, json.JSONDecodeError) as exc:
        print(f"ERROR {exc}")
        return 1
    print("FIXTURES OK " + json.dumps(summary, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
