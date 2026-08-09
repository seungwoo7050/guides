"""Strict clean-process inference for the JSON reference bundle."""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any

from .pipeline import digest_file, predict


class ContractError(ValueError):
    """An input or artifact violates the public inference contract."""


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ContractError(f"{path.name} must contain a JSON object")
    return value


def safe_member(bundle: Path, name: Any) -> Path:
    if not isinstance(name, str) or not name or Path(name).is_absolute() or ".." in Path(name).parts:
        raise ContractError("unsafe bundle member")
    path = (bundle / name).resolve()
    try:
        path.relative_to(bundle.resolve())
    except ValueError as exc:
        raise ContractError("bundle member escapes bundle") from exc
    if not path.is_file() or path.is_symlink():
        raise ContractError(f"missing regular bundle member: {name}")
    return path


def load_bundle(bundle: Path) -> dict[str, Any]:
    bundle = bundle.resolve()
    if not bundle.is_dir() or bundle.is_symlink():
        raise ContractError("bundle must be a real directory")
    manifest = read_json(safe_member(bundle, "manifest.json"))
    if manifest.get("model_artifact_status") != "included":
        raise ContractError("bundle has no included model")
    model_path = safe_member(bundle, manifest.get("model_file"))
    if digest_file(model_path) != manifest.get("model_sha256"):
        raise ContractError("model checksum mismatch")
    checksums = read_json(safe_member(bundle, manifest.get("checksums_file")))
    if checksums.get("algorithm") != "sha256" or not isinstance(checksums.get("files"), dict):
        raise ContractError("unsupported checksum manifest")
    for name, expected in checksums["files"].items():
        if not isinstance(expected, str) or len(expected) != 64 or digest_file(safe_member(bundle, name)) != expected:
            raise ContractError(f"checksum mismatch: {name}")
    model = read_json(model_path)
    preprocessing = read_json(safe_member(bundle, manifest.get("preprocessing_file")))
    schema = read_json(safe_member(bundle, manifest.get("input_schema_file")))
    policy = read_json(safe_member(bundle, manifest.get("decision_policy_file")))
    if model.get("model_version") != manifest.get("model_version"):
        raise ContractError("model version mismatch")
    if model.get("preprocessing_version") != preprocessing.get("preprocessing_version"):
        raise ContractError("preprocessing version mismatch")
    if model.get("feature_order") != preprocessing.get("feature_order"):
        raise ContractError("feature order mismatch")
    if policy.get("model_output", {}).get("model_version") != model.get("model_version"):
        raise ContractError("decision policy/model version mismatch")
    return {"manifest": manifest, "model": model, "preprocessing": preprocessing, "schema": schema, "policy": policy}


def validate_input(value: Any, schema: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ContractError("input must be a JSON object")
    definitions = {field["name"]: field for field in schema.get("fields", [])}
    if schema.get("unknown_field_policy") != "reject" or not definitions:
        raise ContractError("unsupported input schema")
    unknown = sorted(set(value) - set(definitions))
    if unknown:
        raise ContractError(f"unknown input fields: {unknown}")
    missing = sorted(name for name, field in definitions.items() if field.get("required") and name not in value)
    if missing:
        raise ContractError(f"missing required fields: {missing}")
    result: dict[str, Any] = {}
    for name, field in definitions.items():
        item = value[name]
        kind = field["type"]
        if kind == "integer":
            if isinstance(item, bool) or not isinstance(item, int):
                raise ContractError(f"{name} must be an integer")
        elif kind == "number":
            if isinstance(item, bool) or not isinstance(item, (int, float)) or not math.isfinite(float(item)):
                raise ContractError(f"{name} must be a finite number")
        elif kind == "category":
            if not isinstance(item, str) or item not in field.get("allowed_values", []):
                raise ContractError(f"{name} is not an allowed category")
        else:
            raise ContractError(f"unsupported schema type: {kind}")
        if "minimum" in field and item < field["minimum"]:
            raise ContractError(f"{name} is below minimum")
        result[name] = item
    return result


def infer(loaded: dict[str, Any], payload: Any, *, case_id: str | None = None) -> dict[str, Any]:
    row = validate_input(payload, loaded["schema"])
    probability = predict(loaded["model"], loaded["preprocessing"], row)
    threshold = loaded["policy"].get("threshold")
    if isinstance(threshold, bool) or not isinstance(threshold, (int, float)) or not 0 <= threshold <= 1:
        raise ContractError("invalid decision threshold")
    result = {
        "model_version": loaded["model"]["model_version"],
        "policy_version": loaded["policy"]["policy_version"],
        "probability": round(probability, 12),
        "decision": "manual_review" if probability >= threshold else "no_review",
    }
    if case_id is not None:
        result = {"case_id": case_id, **result}
    return result


def parse_inputs(path: Path) -> list[tuple[str | None, Any]]:
    text = path.read_text(encoding="utf-8")
    try:
        values = [json.loads(text)]
    except json.JSONDecodeError:
        values = [json.loads(line) for line in text.splitlines() if line.strip()]
    parsed: list[tuple[str | None, Any]] = []
    for value in values:
        if isinstance(value, dict) and set(value) == {"case_id", "input"} and isinstance(value["case_id"], str):
            parsed.append((value["case_id"], value["input"]))
        else:
            parsed.append((None, value))
    if not parsed:
        raise ContractError("input file is empty")
    return parsed


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle", type=Path, required=True)
    parser.add_argument("--input", type=Path, required=True)
    args = parser.parse_args()
    try:
        loaded = load_bundle(args.bundle)
        for case_id, payload in parse_inputs(args.input):
            print(json.dumps(infer(loaded, payload, case_id=case_id), sort_keys=True))
    except (ContractError, OSError, json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
        print(f"ERROR {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
