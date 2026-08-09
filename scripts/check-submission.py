#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONTRACTS = ROOT / "exercises/model-lifecycle/contracts/stages.json"
FIXTURES = ROOT / "exercises/model-lifecycle/fixtures"
HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
PLACEHOLDERS = {
    "...",
    "…",
    "fixme",
    "placeholder",
    "replace-me",
    "replace-with-immutable-id",
    "todo",
    "tbd",
}


def fail(message: str) -> None:
    raise AssertionError(message)


def safe_file(workspace: Path, relative_text: str) -> Path:
    relative = Path(relative_text)
    if relative.is_absolute() or ".." in relative.parts:
        fail(f"unsafe submission path: {relative_text}")
    candidate = workspace / relative
    component = workspace
    for part in relative.parts:
        component = component / part
        if component.is_symlink():
            fail(f"submission symlink is not allowed: {relative_text}")
    candidate = candidate.resolve()
    try:
        candidate.relative_to(workspace)
    except ValueError:
        fail(f"submission path escapes workspace: {relative_text}")
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
        if any(is_placeholder(line) for line in meaningful):
            fail(f"{path}: heading contains unresolved placeholder content: {heading}")


def normalized_text(value: str) -> str:
    return value.strip().strip("`'\"").strip().lower()


def is_placeholder(value: str) -> bool:
    normalized = normalized_text(value).lstrip("-*+ ").strip()
    return normalized in PLACEHOLDERS or bool(
        re.fullmatch(r"(?:replace|fill)[-_ ](?:me|this|with[-_ ].+)", normalized)
    )


def contains_placeholder(value: Any) -> bool:
    if isinstance(value, str):
        return is_placeholder(value)
    if isinstance(value, list):
        return any(contains_placeholder(item) for item in value)
    if isinstance(value, dict):
        return any(contains_placeholder(item) for item in value.values())
    return False


def validate_finite_tree(value: Any, *, name: str) -> None:
    if isinstance(value, float) and not math.isfinite(value):
        fail(f"{name} contains a non-finite number")
    if isinstance(value, list):
        for index, item in enumerate(value):
            validate_finite_tree(item, name=f"{name}[{index}]")
    elif isinstance(value, dict):
        for key, item in value.items():
            validate_finite_tree(item, name=f"{name}.{key}")


def validate_required_evidence(
    value: Any, *, name: str, nested: bool = False, allow_empty: bool = False
) -> None:
    if value is None:
        if nested:
            return
        fail(f"{name} must not be null")
    if isinstance(value, str):
        if not value.strip():
            fail(f"{name} must not be empty")
        if is_placeholder(value):
            fail(f"{name} contains an unresolved placeholder")
    elif isinstance(value, list):
        if not value and not nested and not allow_empty:
            fail(f"{name} must not be empty")
        for index, item in enumerate(value):
            validate_required_evidence(item, name=f"{name}[{index}]", nested=True)
    elif isinstance(value, dict):
        if not value and not nested and not allow_empty:
            fail(f"{name} must not be empty")
        for key, item in value.items():
            validate_required_evidence(item, name=f"{name}.{key}", nested=True)
    validate_finite_tree(value, name=name)


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
    validate_finite_tree(value, name=str(path))
    allowed_empty = {"entity_overlap", "duplicate_row_ids"} if path.name == "split-audit.json" else set()
    for key in keys:
        validate_required_evidence(value[key], name=f"{path}:{key}", allow_empty=key in allowed_empty)
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
        validate_finite_tree(value, name=f"{path}:{number}")
        for key in keys:
            validate_required_evidence(value[key], name=f"{path}:{number}:{key}")
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
    if not math.isfinite(numeric):
        fail(f"{name} must be finite")
    if minimum is not None and numeric < minimum:
        fail(f"{name} must be >= {minimum}")
    if maximum is not None and numeric > maximum:
        fail(f"{name} must be <= {maximum}")
    return numeric


def require_mapping(value: Any, *, name: str) -> dict[str, Any]:
    if not isinstance(value, dict) or not value:
        fail(f"{name} must be a non-empty object")
    return value


def require_list(value: Any, *, name: str, minimum: int = 1) -> list[Any]:
    if not isinstance(value, list) or len(value) < minimum:
        fail(f"{name} must contain at least {minimum} item(s)")
    return value


def numeric_values(value: Any) -> list[float]:
    result: list[float] = []
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        result.append(float(value))
    elif isinstance(value, list):
        for item in value:
            result.extend(numeric_values(item))
    elif isinstance(value, dict):
        for item in value.values():
            result.extend(numeric_values(item))
    return result


def require_metric_evidence(value: Any, *, name: str, minimum_numbers: int = 1) -> None:
    if not isinstance(value, (dict, list)) or not value:
        fail(f"{name} must be non-empty structured evidence")
    numbers = numeric_values(value)
    if len(numbers) < minimum_numbers:
        fail(f"{name} must contain at least {minimum_numbers} numeric measurement(s)")
    if any(not math.isfinite(number) for number in numbers):
        fail(f"{name} contains a non-finite measurement")


def key_tokens(key: str) -> set[str]:
    return {token for token in re.split(r"[^a-z0-9]+", key.lower()) if token}


def reject_test_selection(value: Any, *, name: str) -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            if "test" in key_tokens(str(key)):
                fail(f"{name} must not contain test evidence during selection: {key}")
            if (
                {"split", "selection", "checkpoint"}.intersection(key_tokens(str(key)))
                and isinstance(item, str)
                and normalized_text(item) == "test"
            ):
                fail(f"{name} must not select on test data")
            reject_test_selection(item, name=name)
    elif isinstance(value, list):
        for item in value:
            reject_test_selection(item, name=name)


def fixture_versions() -> tuple[str, str]:
    schema = json.loads((FIXTURES / "schema.json").read_text(encoding="utf-8"))
    split_policy = json.loads((FIXTURES / "split-policy.json").read_text(encoding="utf-8"))
    return str(schema["schema_version"]), str(split_policy["policy_version"])


def require_identity(actual: Any, expected: str, *, name: str) -> None:
    if actual != expected:
        fail(f"{name} must be {expected!r}, found {actual!r}")


def baseline_identifier(value: dict[str, Any]) -> str:
    for key in ("baseline_id", "name", "id"):
        candidate = value.get(key)
        if isinstance(candidate, str) and candidate.strip() and not is_placeholder(candidate):
            return candidate
    fail("each baseline must have a non-empty baseline_id, name, or id")
    raise AssertionError("unreachable")


def is_linear_model(model: Any) -> bool:
    serialized = json.dumps(model, sort_keys=True).lower()
    return bool(re.search(r"(^|[^a-z])(linear|logistic)([^a-z]|$)", serialized))


def preprocessing_fit_values(value: Any) -> list[str]:
    result: list[str] = []
    if isinstance(value, dict):
        for key, item in value.items():
            normalized_key = re.sub(r"[^a-z0-9]+", "_", str(key).lower()).strip("_")
            if normalized_key in {"fit_data", "fit_on", "fit_split", "fitted_on", "fitted_split"}:
                if isinstance(item, str):
                    result.append(normalized_text(item))
            result.extend(preprocessing_fit_values(item))
    elif isinstance(value, list):
        for item in value:
            result.extend(preprocessing_fit_values(item))
    return result


def require_train_only_preprocessing(value: Any, *, name: str) -> None:
    fit_values = preprocessing_fit_values(value)
    if not fit_values:
        fail(f"{name} must state the preprocessing fit split")
    if any(item not in {"train", "training", "train-only", "training-only"} for item in fit_values):
        fail(f"{name} must fit preprocessing on train only")


def validate_training_trace(value: Any) -> None:
    trace = require_list(value, name="neural training_trace", minimum=2)
    progress: list[float] = []
    for index, entry in enumerate(trace):
        record = require_mapping(entry, name=f"training_trace[{index}]")
        progress_value = next((record[key] for key in ("epoch", "step", "iteration") if key in record), None)
        progress.append(require_number(progress_value, name=f"training_trace[{index}] progress", minimum=0))
        train_metrics = [
            item
            for key, item in record.items()
            if "train" in key.lower() and isinstance(item, (int, float)) and not isinstance(item, bool)
        ]
        validation_metrics = [
            item
            for key, item in record.items()
            if ("validation" in key.lower() or key.lower().startswith("val_"))
            and isinstance(item, (int, float))
            and not isinstance(item, bool)
        ]
        if not train_metrics or not validation_metrics:
            fail(f"training_trace[{index}] must contain train and validation measurements")
        for number in train_metrics + validation_metrics:
            require_number(number, name=f"training_trace[{index}] metric")
    if any(current <= previous for previous, current in zip(progress, progress[1:])):
        fail("neural training_trace progress must be strictly increasing")


def validate_failure_diagnoses(value: Any) -> None:
    diagnoses = require_list(value, name="neural failure_diagnoses", minimum=3)
    aliases = {
        "symptom": {"symptom"},
        "evidence": {"evidence", "observed_evidence", "trace"},
        "cause": {"cause", "diagnosis", "root_cause"},
        "fix": {"correction", "fix", "remediation"},
    }
    symptoms: set[str] = set()
    for index, diagnosis in enumerate(diagnoses):
        record = require_mapping(diagnosis, name=f"failure_diagnoses[{index}]")
        normalized_keys = {
            re.sub(r"[^a-z0-9]+", "_", str(key).lower()).strip("_") for key in record
        }
        for label, accepted in aliases.items():
            if not normalized_keys.intersection(accepted):
                fail(f"failure_diagnoses[{index}] must include structured {label}")
        symptom_key = next(key for key in record if str(key).lower() == "symptom")
        symptoms.add(str(record[symptom_key]).strip().lower())
    if len(symptoms) < 3:
        fail("failure diagnoses must describe at least three distinct symptoms")


def load_json_or_jsonl(path: Path, *, name: str) -> Any:
    text = path.read_text(encoding="utf-8")
    if path.suffix == ".jsonl":
        records: list[Any] = []
        for number, line in enumerate(text.splitlines(), 1):
            if not line.strip():
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError as exc:
                fail(f"{name}:{number} must be valid JSON: {exc}")
        if not records:
            fail(f"{name} must contain at least one record")
        return records
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        fail(f"{name} must be valid JSON: {exc}")


def checksum_entries(value: Any) -> dict[str, str]:
    entries: dict[str, str] = {}
    source = value.get("files", value) if isinstance(value, dict) else value
    if isinstance(source, dict):
        for path, digest in source.items():
            if isinstance(digest, str):
                entries[str(path)] = digest
            elif isinstance(digest, dict) and isinstance(digest.get("sha256"), str):
                entries[str(path)] = digest["sha256"]
    elif isinstance(source, list):
        for item in source:
            if not isinstance(item, dict):
                continue
            path = item.get("path") or item.get("file")
            digest = item.get("sha256")
            if isinstance(path, str) and isinstance(digest, str):
                entries[path] = digest
    return entries


def validate_checksum_file(manifest: dict[str, Any], bundle: Path) -> None:
    reference = manifest.get("checksums_file")
    if not isinstance(reference, str) or not reference.strip():
        fail("included bundle manifest must reference checksums_file")
    path = safe_file(bundle, reference)
    if not path.is_file():
        fail(f"bundle checksums file does not exist: {reference}")
    checksum_document = load_json_or_jsonl(path, name="bundle checksums")
    if not isinstance(checksum_document, dict) or checksum_document.get("algorithm") != "sha256":
        fail("bundle checksums algorithm must be sha256")
    entries = checksum_entries(checksum_document)
    if not entries:
        fail("bundle checksums file must contain file-to-SHA-256 entries")
    reference_keys = [
        "model_file",
        "input_schema_file",
        "preprocessing_file",
        "decision_policy_file",
        "evaluation_file",
        "model_card_file",
    ]
    for aliases in (("golden_input_file", "golden_inputs_file"), ("golden_output_file", "golden_predictions_file")):
        selected = next((key for key in aliases if key in manifest), None)
        if selected is not None:
            reference_keys.append(selected)
    reproduction_key = next(
        (key for key in ("reproduction_file", "reproduction_evidence_file") if key in manifest),
        None,
    )
    if reproduction_key is not None:
        reference_keys.append(reproduction_key)
    for key in reference_keys:
        referenced = manifest.get(key)
        if referenced not in entries:
            fail(f"bundle checksums must include manifest reference {key}: {referenced}")
    for relative, expected in entries.items():
        if not re.fullmatch(r"[0-9a-f]{64}", expected):
            fail(f"bundle checksum for {relative} must be lowercase SHA-256")
        candidate = safe_file(bundle, relative)
        if not candidate.is_file():
            fail(f"bundle checksum references a missing file: {relative}")
        if hashlib.sha256(candidate.read_bytes()).hexdigest() != expected:
            fail(f"bundle checksum mismatch: {relative}")


def validate_golden_and_reproduction(manifest: dict[str, Any], bundle: Path) -> None:
    reference_groups = {
        "golden input": ("golden_input_file", "golden_inputs_file"),
        "golden output": ("golden_output_file", "golden_predictions_file"),
        "reproduction evidence": ("reproduction_file", "reproduction_evidence_file"),
    }
    loaded: dict[str, Any] = {}
    paths: dict[str, Path] = {}
    for label, keys in reference_groups.items():
        selected_key = next((key for key in keys if key in manifest), None)
        if selected_key is None:
            fail(f"stage 8 manifest must reference {label}")
        relative = manifest[selected_key]
        validate_required_evidence(relative, name=f"manifest {selected_key}")
        candidate = safe_file(bundle, str(relative))
        if not candidate.is_file() or candidate.stat().st_size == 0:
            fail(f"stage 8 {label} file does not exist or is empty: {relative}")
        evidence = load_json_or_jsonl(candidate, name=f"stage 8 {label}")
        validate_required_evidence(evidence, name=f"stage 8 {label}")
        loaded[label] = evidence
        paths[label] = candidate

    inputs = loaded["golden input"]
    predictions = loaded["golden output"]
    if not isinstance(inputs, list):
        inputs = [inputs]
    if not isinstance(predictions, list):
        predictions = [predictions]
    input_ids = {
        record.get("case_id") for record in inputs if isinstance(record, dict) and isinstance(record.get("case_id"), str)
    }
    prediction_ids = {
        record.get("case_id")
        for record in predictions
        if isinstance(record, dict) and isinstance(record.get("case_id"), str)
    }
    if len(input_ids) != len(inputs) or input_ids != prediction_ids:
        fail("golden inputs and predictions must have matching unique case_id values")
    policy = load_json_or_jsonl(bundle / "decision-policy.json", name="decision policy")
    threshold = require_number(policy.get("threshold"), name="golden decision threshold", minimum=0, maximum=1)
    actions = require_mapping(policy.get("actions"), name="decision policy actions")
    positive_action = actions.get("at_or_above_threshold", actions.get("positive"))
    negative_action = actions.get("below_threshold", actions.get("negative"))
    if positive_action is None or negative_action is None:
        fail("decision policy actions must define positive/negative threshold outcomes")
    for index, prediction in enumerate(predictions):
        record = require_mapping(prediction, name=f"golden prediction[{index}]")
        for key in ("model_version", "probability", "decision", "policy_version"):
            if key not in record:
                fail(f"golden prediction[{index}] is missing {key}")
            validate_required_evidence(record[key], name=f"golden prediction[{index}].{key}")
        probability = require_number(
            record["probability"], name=f"golden prediction[{index}].probability", minimum=0, maximum=1
        )
        expected_decision = positive_action if probability >= threshold else negative_action
        if record["decision"] != expected_decision:
            fail(f"golden prediction[{index}] decision disagrees with decision threshold")
        if record["policy_version"] != policy.get("policy_version"):
            fail(f"golden prediction[{index}] policy_version disagrees with decision policy")
        if "model_version" in manifest and record["model_version"] != manifest["model_version"]:
            fail(f"golden prediction[{index}] model_version disagrees with bundle manifest")

    reproduction = require_mapping(loaded["reproduction evidence"], name="reproduction evidence")
    for key in ("source_revision", "python_requirement", "command", "fixture_digests", "determinism", "expected_files"):
        if key not in reproduction:
            fail(f"reproduction evidence is missing {key}")
        validate_required_evidence(reproduction[key], name=f"reproduction evidence.{key}")
    fixture_manifest_path = FIXTURES / "fixture-manifest.json"
    fixture_manifest = json.loads(fixture_manifest_path.read_text(encoding="utf-8"))["files"]
    fixture_digests = require_mapping(reproduction["fixture_digests"], name="reproduction fixture_digests")
    for name in ("dataset.csv", "schema.json", "split-policy.json", "split_manifest.csv"):
        expected = fixture_manifest[name]
        if fixture_digests.get(name) != expected:
            fail(f"reproduction fixture digest does not match {name}")
    if "fixture-manifest.json" in fixture_digests:
        expected_manifest_digest = hashlib.sha256(fixture_manifest_path.read_bytes()).hexdigest()
        if fixture_digests["fixture-manifest.json"] != expected_manifest_digest:
            fail("reproduction fixture digest does not match fixture-manifest.json")

    expected_files = require_list(reproduction["expected_files"], name="reproduction expected_files")
    normalized_expected: list[str] = []
    for index, relative in enumerate(expected_files):
        if not isinstance(relative, str) or not relative.strip():
            fail(f"reproduction expected_files[{index}] must be a non-empty relative path")
        path = Path(relative)
        if path.is_absolute() or ".." in path.parts:
            fail(f"reproduction expected_files[{index}] must be a safe relative path")
        if not safe_file(bundle, relative).is_file():
            fail(f"reproduction expected file does not exist: {relative}")
        normalized_expected.append(relative)
    if len(normalized_expected) != len(set(normalized_expected)):
        fail("reproduction expected_files must not contain duplicates")
    required_expected = {
        str(manifest[key])
        for key in ("model_file", "golden_inputs_file", "golden_predictions_file", "reproduction_file")
    }
    missing_expected = sorted(required_expected - set(normalized_expected))
    if missing_expected:
        fail(f"reproduction expected_files omits manifest references: {missing_expected}")

    report_reproduction = bundle.parents[1] / "reports/reproduction.json"
    if report_reproduction.is_file() and report_reproduction.read_bytes() != paths["reproduction evidence"].read_bytes():
        fail("report and bundle reproduction evidence must match byte-for-byte")


def stage_specific(stage: int, outputs: dict[str, Any], workspace: Path) -> None:
    if stage == 2:
        audit = outputs["reports/split-audit.json"]
        dataset_version, split_policy_version = fixture_versions()
        require_identity(audit.get("dataset_version"), dataset_version, name="split audit dataset_version")
        require_identity(audit.get("split_policy_version"), split_policy_version, name="split audit split_policy_version")
        expected = actual_split_summary()
        for key in ("rows", "entities", "positives"):
            if audit.get(key) != expected[key]:
                fail(f"split audit {key} does not match fixture: {audit.get(key)} != {expected[key]}")
        if audit.get("entity_overlap") != [] or audit.get("duplicate_row_ids") != [] or audit.get("valid") is not True:
            fail("split audit must report no entity overlap or duplicate row IDs")
        if "future_refund_30d" not in audit.get("forbidden_features", []):
            fail("split audit must identify future_refund_30d as forbidden")
        require_list(audit.get("limitations"), name="split audit limitations")
    elif stage == 3:
        baseline = outputs["reports/baseline.json"]
        audit = outputs["reports/split-audit.json"]
        require_identity(baseline.get("dataset_version"), audit["dataset_version"], name="baseline dataset_version")
        if baseline.get("selection_split") != "validation":
            fail("baseline selection_split must be validation")
        baselines = require_list(baseline.get("baselines"), name="baselines", minimum=2)
        identifiers: list[str] = []
        for index, item in enumerate(baselines):
            record = require_mapping(item, name=f"baselines[{index}]")
            identifiers.append(baseline_identifier(record))
            require_metric_evidence(record.get("validation"), name=f"baselines[{index}].validation")
            reject_test_selection(record, name=f"baselines[{index}]")
        if len(set(identifiers)) != len(identifiers):
            fail("baseline identifiers must be unique")
        if baseline.get("chosen_baseline") not in identifiers:
            fail("chosen_baseline must reference a reported baseline")
        require_mapping(baseline.get("decision_context"), name="baseline decision_context")
        require_list(baseline.get("known_limitations"), name="baseline known_limitations")
        reject_test_selection(baseline, name="baseline selection")
    elif stage == 4:
        records = outputs["reports/classical-experiments.jsonl"]
        run_ids = [record["run_id"] for record in records]
        if len(run_ids) != len(set(run_ids)):
            fail("classical experiment run_id values must be unique")
        audit = outputs["reports/split-audit.json"]
        feature_versions: set[str] = set()
        for index, record in enumerate(records):
            require_identity(record.get("dataset_version"), audit["dataset_version"], name=f"run {run_ids[index]} dataset_version")
            require_identity(
                record.get("split_policy_version"), audit["split_policy_version"], name=f"run {run_ids[index]} split_policy_version"
            )
            feature_versions.add(str(record["feature_schema_version"]))
            require_mapping(record.get("model"), name=f"run {run_ids[index]} model")
            preprocessing = require_mapping(record.get("preprocessing"), name=f"run {run_ids[index]} preprocessing")
            require_train_only_preprocessing(preprocessing, name=f"run {run_ids[index]} preprocessing")
            require_metric_evidence(record.get("validation"), name=f"run {run_ids[index]} validation")
            seed = require_number(record.get("seed"), name=f"run {run_ids[index]} seed")
            if not seed.is_integer():
                fail(f"run {run_ids[index]} seed must be an integer")
            reject_test_selection(record, name=f"classical run {run_ids[index]}")
        if len(feature_versions) != 1:
            fail("classical runs must use one feature_schema_version")
        if not any(is_linear_model(record["model"]) for record in records):
            fail("classical experiments must include at least one linear or logistic model")
    elif stage == 5:
        evaluation = outputs["reports/evaluation.json"]
        if evaluation.get("threshold_selection_split") != "validation":
            fail("threshold_selection_split must be validation")
        require_number(evaluation.get("threshold"), name="threshold", minimum=0.0, maximum=1.0)
        records = outputs["reports/classical-experiments.jsonl"]
        if evaluation.get("selected_run_id") not in {record.get("run_id") for record in records}:
            fail("evaluation selected_run_id must reference a classical experiment")
        require_metric_evidence(evaluation.get("test"), name="final test")
        require_metric_evidence(evaluation.get("calibration"), name="calibration")
        require_metric_evidence(evaluation.get("slices"), name="slice evaluation")
        require_mapping(evaluation.get("error_analysis"), name="error_analysis")
    elif stage == 6:
        neural = outputs["reports/neural-experiment.json"]
        parameter_count = require_number(neural.get("parameter_count"), name="parameter_count", minimum=1)
        if not parameter_count.is_integer():
            fail("parameter_count must be an integer")
        require_mapping(neural.get("shapes"), name="neural shapes")
        require_mapping(neural.get("optimizer"), name="neural optimizer")
        require_metric_evidence(neural.get("small_batch_overfit"), name="small_batch_overfit")
        validate_training_trace(neural.get("training_trace"))
        require_metric_evidence(neural.get("seed_variation"), name="seed_variation", minimum_numbers=2)
        validate_failure_diagnoses(neural.get("failure_diagnoses"))
        require_mapping(neural.get("comparison"), name="neural comparison")
        reject_test_selection(neural.get("checkpoint_rule"), name="neural checkpoint rule")
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
        audit = outputs["reports/split-audit.json"]
        records = outputs["reports/classical-experiments.jsonl"]
        evaluation = outputs["reports/evaluation.json"]
        bundle_evaluation = outputs["artifacts/model-bundle/evaluation.json"]
        feature_version = records[0]["feature_schema_version"]
        require_identity(manifest.get("dataset_version"), audit["dataset_version"], name="bundle dataset_version")
        require_identity(
            manifest.get("split_policy_version"), audit["split_policy_version"], name="bundle split_policy_version"
        )
        require_identity(manifest.get("feature_schema_version"), feature_version, name="bundle feature_schema_version")
        require_identity(
            bundle_evaluation.get("selected_run_id"), evaluation["selected_run_id"], name="bundle selected_run_id"
        )
        require_identity(
            bundle_evaluation.get("dataset_version"), manifest["dataset_version"], name="bundle evaluation dataset_version"
        )
        require_identity(
            bundle_evaluation.get("split_policy_version"),
            manifest["split_policy_version"],
            name="bundle evaluation split_policy_version",
        )
        if bundle_evaluation.get("test") != evaluation.get("test") or bundle_evaluation.get("slices") != evaluation.get("slices"):
            fail("bundle evaluation test and slices must match the final evaluation")
        if bundle_evaluation.get("threshold") != evaluation.get("threshold"):
            fail("bundle evaluation threshold must match the final evaluation")
        if bundle_evaluation.get("threshold_selection_split") != "validation":
            fail("bundle evaluation threshold_selection_split must be validation")
        require_metric_evidence(bundle_evaluation.get("test"), name="bundle test")
        require_metric_evidence(bundle_evaluation.get("slices"), name="bundle slices")
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
            validate_checksum_file(manifest, bundle)
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
        decision_threshold = require_number(decision.get("threshold"), name="decision threshold", minimum=0.0, maximum=1.0)
        if decision_threshold != float(evaluation["threshold"]):
            fail("bundle decision threshold must match the final evaluation")
        input_schema = outputs["artifacts/model-bundle/input-schema.json"]
        fields = require_list(input_schema.get("fields"), name="bundle input fields")
        field_names = [field.get("name") for field in fields if isinstance(field, dict)]
        if len(field_names) != len(fields) or any(not isinstance(name, str) or not name for name in field_names):
            fail("every bundle input field must have a non-empty name")
        if len(set(field_names)) != len(field_names):
            fail("bundle input field names must be unique")
        require_mapping(manifest.get("runtime"), name="bundle runtime")
        require_list(manifest.get("known_limitations"), name="bundle known_limitations")
    elif stage == 8:
        bundle = workspace / "artifacts/model-bundle"
        manifest = outputs["artifacts/model-bundle/manifest.json"]
        if manifest.get("model_artifact_status") != "included":
            fail("stage 8 requires an included model artifact")
        model = outputs["artifacts/model-bundle/model.json"]
        preprocessing = outputs["artifacts/model-bundle/preprocessing.json"]
        require_identity(model.get("model_version"), manifest["model_version"], name="model artifact model_version")
        require_identity(
            model.get("feature_schema_version"), manifest["feature_schema_version"], name="model artifact feature_schema_version"
        )
        require_identity(
            model.get("preprocessing_version"),
            preprocessing["preprocessing_version"],
            name="model artifact preprocessing_version",
        )
        if model.get("feature_order") != preprocessing.get("feature_order"):
            fail("model artifact feature_order must match preprocessing")
        training = require_mapping(model.get("training"), name="model artifact training")
        if training.get("split") != "train":
            fail("model artifact training split must be train")
        validate_golden_and_reproduction(manifest, bundle)
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
    if not workspace.is_dir() or workspace.is_symlink():
        fail(f"workspace must be a real directory: {workspace}")
    workspace = workspace.resolve()
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
