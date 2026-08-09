#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONTRACTS = ROOT / "exercises/model-lifecycle/contracts/stages.json"
FIXTURES = ROOT / "exercises/model-lifecycle/fixtures"
HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
PLACEHOLDERS = {"replace-me", "replace-with-immutable-id", "todo", "tbd"}


def fail(message: str) -> None:
    raise AssertionError(message)


def safe_file(workspace: Path, relative_text: str) -> Path:
    relative = Path(relative_text)
    if relative.is_absolute() or ".." in relative.parts:
        fail(f"unsafe submission path: {relative_text}")
    candidate = (workspace / relative).resolve()
    try:
        candidate.relative_to(workspace)
    except ValueError:
        fail(f"submission path escapes workspace: {relative_text}")
    if candidate.is_symlink():
        fail(f"submission symlink is not allowed: {relative_text}")
    return candidate


def heading_sections(text: str) -> dict[str, str]:
    lines = text.splitlines()
    positions: list[tuple[int, int, str]] = []
    for index, line in enumerate(lines):
        match = HEADING_RE.match(line)
        if match:
            title = re.sub(r"\s+#+$", "", match.group(2)).strip()
            positions.append((index, len(match.group(1)), title))
    sections: dict[str, str] = {}
    for position, (start, level, title) in enumerate(positions):
        end = len(lines)
        for candidate_start, candidate_level, _ in positions[position + 1 :]:
            if candidate_level <= level:
                end = candidate_start
                break
        sections[title] = "\n".join(lines[start + 1 : end]).strip()
    return sections


def validate_markdown(path: Path, headings: list[str]) -> None:
    text = path.read_text(encoding="utf-8")
    sections = heading_sections(text)
    for heading in headings:
        if heading not in sections:
            fail(f"{path}: missing heading: {heading}")
        body = sections[heading]
        meaningful = [line.strip() for line in body.splitlines() if line.strip() and not line.strip().startswith("<!--")]
        if not meaningful:
            fail(f"{path}: heading has no content: {heading}")


def contains_placeholder(value: Any) -> bool:
    if isinstance(value, str):
        return value.strip().lower() in PLACEHOLDERS
    if isinstance(value, list):
        return any(contains_placeholder(item) for item in value)
    if isinstance(value, dict):
        return any(contains_placeholder(item) for item in value.values())
    return False


def validate_json(path: Path, keys: list[str]) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        fail(f"{path}: invalid JSON: {exc}")
    if not isinstance(value, dict):
        fail(f"{path}: top-level JSON must be an object")
    missing = [key for key in keys if key not in value]
    if missing:
        fail(f"{path}: missing keys: {missing}")
    if contains_placeholder(value):
        fail(f"{path}: unresolved placeholder value")
    return value


def validate_jsonl(path: Path, keys: list[str], minimum: int) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not raw.strip():
            continue
        try:
            value = json.loads(raw)
        except json.JSONDecodeError as exc:
            fail(f"{path}:{number}: invalid JSON: {exc}")
        if not isinstance(value, dict):
            fail(f"{path}:{number}: record must be an object")
        missing = [key for key in keys if key not in value]
        if missing:
            fail(f"{path}:{number}: missing keys: {missing}")
        if contains_placeholder(value):
            fail(f"{path}:{number}: unresolved placeholder value")
        records.append(value)
    if len(records) < minimum:
        fail(f"{path}: expected at least {minimum} records, found {len(records)}")
    return records


def actual_split_summary() -> dict[str, dict[str, int]]:
    with (FIXTURES / "dataset.csv").open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    with (FIXTURES / "split_manifest.csv").open(newline="", encoding="utf-8") as handle:
        manifest = list(csv.DictReader(handle))
    split_by_row = {entry["row_id"]: entry["split"] for entry in manifest}
    result = {
        "rows": {name: 0 for name in ("train", "validation", "test")},
        "entities": {name: set() for name in ("train", "validation", "test")},
        "positives": {name: 0 for name in ("train", "validation", "test")},
    }
    for row in rows:
        split = split_by_row[row["row_id"]]
        result["rows"][split] += 1
        result["entities"][split].add(row["entity_id"])
        result["positives"][split] += int(row["churn_30d"])
    return {
        "rows": result["rows"],
        "entities": {name: len(values) for name, values in result["entities"].items()},
        "positives": result["positives"],
    }


def require_number(value: Any, *, name: str, minimum: float | None = None, maximum: float | None = None) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        fail(f"{name} must be a number")
    numeric = float(value)
    if minimum is not None and numeric < minimum:
        fail(f"{name} must be >= {minimum}")
    if maximum is not None and numeric > maximum:
        fail(f"{name} must be <= {maximum}")
    return numeric


def stage_specific(stage: int, outputs: dict[str, Any], workspace: Path) -> None:
    if stage == 2:
        audit = outputs["reports/split-audit.json"]
        expected = actual_split_summary()
        for key in ("rows", "entities", "positives"):
            if audit.get(key) != expected[key]:
                fail(f"split audit {key} does not match fixture: {audit.get(key)} != {expected[key]}")
        if audit.get("entity_overlap") != [] or audit.get("duplicate_row_ids") != [] or audit.get("valid") is not True:
            fail("split audit must report no entity overlap or duplicate row IDs")
        if "future_refund_30d" not in audit.get("forbidden_features", []):
            fail("split audit must identify future_refund_30d as forbidden")
    elif stage == 3:
        baseline = outputs["reports/baseline.json"]
        if baseline.get("selection_split") != "validation":
            fail("baseline selection_split must be validation")
        if not isinstance(baseline.get("baselines"), list) or len(baseline["baselines"]) < 2:
            fail("baseline report must contain at least two baselines")
    elif stage == 4:
        records = outputs["reports/classical-experiments.jsonl"]
        run_ids = [record["run_id"] for record in records]
        if len(run_ids) != len(set(run_ids)):
            fail("classical experiment run_id values must be unique")
        if any("test" in record for record in records):
            fail("stage 4 experiment records must not contain final test results")
    elif stage == 5:
        evaluation = outputs["reports/evaluation.json"]
        if evaluation.get("threshold_selection_split") != "validation":
            fail("threshold_selection_split must be validation")
        require_number(evaluation.get("threshold"), name="threshold", minimum=0.0, maximum=1.0)
        experiment_path = workspace / "reports/classical-experiments.jsonl"
        records = [json.loads(line) for line in experiment_path.read_text(encoding="utf-8").splitlines() if line.strip()]
        if evaluation.get("selected_run_id") not in {record.get("run_id") for record in records}:
            fail("evaluation selected_run_id must reference a classical experiment")
    elif stage == 6:
        neural = outputs["reports/neural-experiment.json"]
        if not isinstance(neural.get("training_trace"), list) or not neural["training_trace"]:
            fail("neural training_trace must not be empty")
        if not isinstance(neural.get("failure_diagnoses"), list) or len(neural["failure_diagnoses"]) < 3:
            fail("neural report must include at least three failure diagnoses")
        require_number(neural.get("parameter_count"), name="parameter_count", minimum=1)
    elif stage == 7:
        bundle = workspace / "artifacts/model-bundle"
        manifest = outputs["artifacts/model-bundle/manifest.json"]
        status = manifest.get("model_artifact_status")
        if status not in {"included", "not-included"}:
            fail("model_artifact_status must be included or not-included")
        references = {
            "input_schema_file": "input-schema.json",
            "preprocessing_file": "preprocessing.json",
            "decision_policy_file": "decision-policy.json",
            "evaluation_file": "evaluation.json",
            "model_card_file": "model-card.md",
        }
        for key, expected in references.items():
            if manifest.get(key) != expected:
                fail(f"bundle manifest {key} must be {expected}")
        if status == "included":
            model_file = manifest.get("model_file")
            expected_hash = manifest.get("model_sha256")
            if not isinstance(model_file, str) or not model_file:
                fail("included model requires model_file")
            if not isinstance(expected_hash, str) or not re.fullmatch(r"[0-9a-f]{64}", expected_hash):
                fail("included model requires a lowercase SHA-256 digest")
            candidate = safe_file(bundle, model_file)
            if not candidate.is_file():
                fail(f"included model file does not exist: {model_file}")
            actual = hashlib.sha256(candidate.read_bytes()).hexdigest()
            if actual != expected_hash:
                fail("model artifact checksum mismatch")
        else:
            if manifest.get("model_file") not in {None, ""} or manifest.get("model_sha256") not in {None, ""}:
                fail("not-included model must not claim a file or checksum")
        preprocessing = outputs["artifacts/model-bundle/preprocessing.json"]
        if preprocessing.get("fit_split") != "train":
            fail("preprocessing fit_split must be train")
        if not isinstance(preprocessing.get("feature_order"), list) or not preprocessing["feature_order"]:
            fail("preprocessing feature_order must not be empty")
        if "future_refund_30d" in preprocessing["feature_order"]:
            fail("forbidden future_refund_30d cannot be in feature_order")
        decision = outputs["artifacts/model-bundle/decision-policy.json"]
        require_number(decision.get("threshold"), name="decision threshold", minimum=0.0, maximum=1.0)
    elif stage == 8:
        decision_path = workspace / "reports/release-decision.md"
        decision_text = heading_sections(decision_path.read_text(encoding="utf-8")).get("Decision", "")
        accepted = {"APPROVE", "APPROVE WITH CONDITIONS", "DEFER", "REJECT"}
        tokens = {line.strip().strip("`") for line in decision_text.splitlines() if line.strip()}
        if not tokens.intersection(accepted):
            fail(f"release decision must contain one of {sorted(accepted)}")
        report_card = (workspace / "reports/model-card.md").read_bytes()
        bundle_card = (workspace / "artifacts/model-bundle/model-card.md").read_bytes()
        if report_card != bundle_card:
            fail("stage 8 report model-card.md must match the bundle model-card.md")


def validate(workspace: Path, requested_stage: int) -> dict[str, int]:
    workspace = workspace.resolve()
    if not workspace.is_dir() or workspace.is_symlink():
        fail(f"workspace must be a real directory: {workspace}")
    if requested_stage < 1 or requested_stage > 8:
        fail("stage must be between 1 and 8")
    contracts = json.loads(CONTRACTS.read_text(encoding="utf-8"))
    checked_files = 0
    outputs: dict[str, Any] = {}
    for contract in contracts["stages"]:
        stage = int(contract["stage"])
        if stage > requested_stage:
            break
        stage_outputs: dict[str, Any] = {}
        for item in contract["files"]:
            relative = item["path"]
            path = safe_file(workspace, relative)
            if not path.is_file():
                fail(f"stage {stage}: missing file: {relative}")
            if item["type"] == "markdown":
                validate_markdown(path, item["headings"])
                value: Any = path.read_text(encoding="utf-8")
            elif item["type"] == "json":
                value = validate_json(path, item["required_keys"])
            else:
                value = validate_jsonl(path, item["required_keys"], int(item.get("minimum_records", 1)))
            outputs[relative] = value
            stage_outputs[relative] = value
            checked_files += 1
        stage_specific(stage, outputs, workspace)
    return {"stage": requested_stage, "files": checked_files}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--stage", type=int, required=True)
    args = parser.parse_args()
    try:
        result = validate(args.workspace, args.stage)
    except (AssertionError, KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        print(f"ERROR {exc}")
        return 1
    print("SUBMISSION OK " + json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
