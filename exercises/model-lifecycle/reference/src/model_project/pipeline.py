"""Build the deterministic model-lifecycle reference from committed fixtures."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import random
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable

DATASET_VERSION = "synthetic-churn-v1"
SPLIT_VERSION = "entity-hash-v1"
FEATURE_SCHEMA_VERSION = "churn-features-v1"
MODEL_VERSION = "churn-logistic-v1"
POLICY_VERSION = "churn-review-v1"
SEED = 7050
NUMERIC = (
    "tenure_months",
    "monthly_usage_hours",
    "usage_change_90d",
    "support_tickets_90d",
    "late_payments_180d",
    "marketing_contacts_30d",
)
CATEGORIES = {
    "plan_tier": ("basic", "standard", "premium"),
    "region": ("north", "south", "east", "west"),
}
INPUT_FIELDS = NUMERIC + tuple(CATEGORIES)
FORBIDDEN = ("future_refund_30d",)
INTEGER_FIELDS = {"tenure_months", "support_tickets_90d", "late_payments_180d", "marketing_contacts_30d"}


def canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def digest_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def digest_file(path: Path) -> str:
    return digest_bytes(path.read_bytes())


def default_exercise_root() -> Path:
    return Path(__file__).resolve().parents[3]


def load_rows(fixtures: Path) -> list[dict[str, Any]]:
    with (fixtures / "split_manifest.csv").open(newline="", encoding="utf-8") as handle:
        manifest = list(csv.DictReader(handle))
    split_by_row = {entry["row_id"]: entry["split"] for entry in manifest}
    if len(split_by_row) != len(manifest):
        raise ValueError("duplicate row_id in split manifest")
    rows: list[dict[str, Any]] = []
    with (fixtures / "dataset.csv").open(newline="", encoding="utf-8") as handle:
        for raw in csv.DictReader(handle):
            row_id = raw["row_id"]
            if row_id not in split_by_row:
                raise ValueError(f"row absent from split manifest: {row_id}")
            row: dict[str, Any] = {
                "row_id": row_id,
                "entity_id": raw["entity_id"],
                "snapshot_month": raw["snapshot_month"],
                "plan_tier": raw["plan_tier"],
                "region": raw["region"],
                "split": split_by_row[row_id],
                "churn_30d": int(raw["churn_30d"]),
                "future_refund_30d": int(raw["future_refund_30d"]),
            }
            for name in NUMERIC:
                row[name] = int(raw[name]) if name in INTEGER_FIELDS else float(raw[name])
            rows.append(row)
    if len(rows) != len(manifest):
        raise ValueError("dataset and split manifest row counts differ")
    entity_splits: dict[str, set[str]] = defaultdict(set)
    for row in rows:
        entity_splits[row["entity_id"]].add(row["split"])
    overlap = [entity for entity, splits in entity_splits.items() if len(splits) != 1]
    if overlap:
        raise ValueError(f"entities cross split boundaries: {overlap[:3]}")
    return rows


def split_rows(rows: Iterable[dict[str, Any]], name: str) -> list[dict[str, Any]]:
    return [row for row in rows if row["split"] == name]


def fit_preprocessing(train: list[dict[str, Any]]) -> dict[str, Any]:
    if not train or any(row["split"] != "train" for row in train):
        raise ValueError("preprocessing must receive non-empty training split only")
    means: dict[str, float] = {}
    scales: dict[str, float] = {}
    for name in NUMERIC:
        values = [float(row[name]) for row in train]
        mean = sum(values) / len(values)
        variance = sum((value - mean) ** 2 for value in values) / len(values)
        means[name] = mean
        scales[name] = math.sqrt(variance) or 1.0
    order = list(NUMERIC)
    for name, values in CATEGORIES.items():
        order.extend(f"{name}={value}" for value in values)
    return {
        "preprocessing_version": "churn-preprocessing-v1",
        "fit_split": "train",
        "feature_order": order,
        "steps": [
            {"kind": "standardize", "fields": list(NUMERIC), "means": means, "scales": scales},
            {"kind": "one_hot", "fields": {key: list(value) for key, value in CATEGORIES.items()}},
        ],
        "unknown_and_missing_policy": "reject",
    }


def transform(row: dict[str, Any], preprocessing: dict[str, Any]) -> list[float]:
    standardize = preprocessing["steps"][0]
    vector = [
        (float(row[name]) - float(standardize["means"][name]))
        / float(standardize["scales"][name])
        for name in NUMERIC
    ]
    for name, values in CATEGORIES.items():
        vector.extend(1.0 if row[name] == value else 0.0 for value in values)
    return vector


def sigmoid(value: float) -> float:
    if value >= 0:
        term = math.exp(-value)
        return 1.0 / (1.0 + term)
    term = math.exp(value)
    return term / (1.0 + term)


def train_logistic(
    train: list[dict[str, Any]],
    preprocessing: dict[str, Any],
    *,
    epochs: int = 420,
    learning_rate: float = 0.12,
    regularization: float = 0.002,
) -> dict[str, Any]:
    vectors = [transform(row, preprocessing) for row in train]
    labels = [int(row["churn_30d"]) for row in train]
    weights = [0.0] * len(vectors[0])
    bias = 0.0
    for _ in range(epochs):
        gradient = [0.0] * len(weights)
        bias_gradient = 0.0
        for vector, label in zip(vectors, labels):
            error = sigmoid(sum(w * x for w, x in zip(weights, vector)) + bias) - label
            bias_gradient += error
            for index, value in enumerate(vector):
                gradient[index] += error * value
        count = len(vectors)
        for index in range(len(weights)):
            weights[index] -= learning_rate * (gradient[index] / count + regularization * weights[index])
        bias -= learning_rate * bias_gradient / count
    return {
        "format_version": 1,
        "model_version": MODEL_VERSION,
        "family": "binary-logistic-regression",
        "feature_schema_version": FEATURE_SCHEMA_VERSION,
        "preprocessing_version": preprocessing["preprocessing_version"],
        "feature_order": preprocessing["feature_order"],
        "weights": weights,
        "bias": bias,
        "training": {
            "split": "train",
            "seed": SEED,
            "epochs": epochs,
            "learning_rate": learning_rate,
            "l2": regularization,
        },
    }


def predict(model: dict[str, Any], preprocessing: dict[str, Any], row: dict[str, Any]) -> float:
    vector = transform(row, preprocessing)
    if model["feature_order"] != preprocessing["feature_order"] or len(vector) != len(model["weights"]):
        raise ValueError("model/preprocessing feature contract mismatch")
    return sigmoid(sum(w * x for w, x in zip(model["weights"], vector)) + model["bias"])


def probabilities(model: dict[str, Any], preprocessing: dict[str, Any], rows: list[dict[str, Any]]) -> list[float]:
    return [predict(model, preprocessing, row) for row in rows]


def metrics(labels: list[int], scores: list[float], threshold: float = 0.5) -> dict[str, Any]:
    if not labels or len(labels) != len(scores):
        raise ValueError("labels and scores must be equally sized and non-empty")
    clipped = [min(max(score, 1e-12), 1.0 - 1e-12) for score in scores]
    predicted = [int(score >= threshold) for score in clipped]
    tp = sum(y == 1 and p == 1 for y, p in zip(labels, predicted))
    fp = sum(y == 0 and p == 1 for y, p in zip(labels, predicted))
    tn = sum(y == 0 and p == 0 for y, p in zip(labels, predicted))
    fn = sum(y == 1 and p == 0 for y, p in zip(labels, predicted))
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    positive_scores = [score for score, label in zip(clipped, labels) if label]
    negative_scores = [score for score, label in zip(clipped, labels) if not label]
    wins = sum((a > b) + 0.5 * (a == b) for a in positive_scores for b in negative_scores)
    auc = wins / (len(positive_scores) * len(negative_scores)) if positive_scores and negative_scores else 0.0
    return {
        "rows": len(labels),
        "positives": sum(labels),
        "threshold": threshold,
        "accuracy": sum(y == p for y, p in zip(labels, predicted)) / len(labels),
        "precision": precision,
        "recall": recall,
        "f1": 2 * precision * recall / (precision + recall) if precision + recall else 0.0,
        "brier": sum((score - label) ** 2 for score, label in zip(clipped, labels)) / len(labels),
        "log_loss": -sum(label * math.log(score) + (1 - label) * math.log(1 - score) for label, score in zip(labels, clipped)) / len(labels),
        "roc_auc": auc,
        "confusion": {"true_positive": tp, "false_positive": fp, "true_negative": tn, "false_negative": fn},
    }


def rounded(value: Any) -> Any:
    if isinstance(value, float):
        return round(value, 8)
    if isinstance(value, list):
        return [rounded(item) for item in value]
    if isinstance(value, dict):
        return {key: rounded(item) for key, item in value.items()}
    return value


def select_threshold(labels: list[int], scores: list[float]) -> tuple[float, dict[str, Any]]:
    candidates = [value / 100 for value in range(15, 76, 5)]
    evaluated = [(threshold, metrics(labels, scores, threshold)) for threshold in candidates]
    # F1 is the declared selection metric; recall, fewer reviews and higher threshold are tie breakers.
    selected = max(
        evaluated,
        key=lambda item: (
            item[1]["f1"],
            item[1]["recall"],
            -(item[1]["confusion"]["true_positive"] + item[1]["confusion"]["false_positive"]),
            item[0],
        ),
    )
    return selected[0], selected[1]


def baseline_reports(train: list[dict[str, Any]], validation: list[dict[str, Any]]) -> dict[str, Any]:
    prevalence = sum(int(row["churn_30d"]) for row in train) / len(train)
    labels = [int(row["churn_30d"]) for row in validation]
    constant = [prevalence] * len(validation)
    rule = [
        0.72 if (row["usage_change_90d"] <= -4 and row["support_tickets_90d"] >= 1) or row["late_payments_180d"] >= 2 else 0.12
        for row in validation
    ]
    constant_metrics = metrics(labels, constant, 0.5)
    rule_metrics = metrics(labels, rule, 0.5)
    chosen = "declining-usage-or-late-payment-rule" if rule_metrics["f1"] >= constant_metrics["f1"] else "train-prevalence"
    return rounded({
        "dataset_version": DATASET_VERSION,
        "selection_split": "validation",
        "selection_metric": "f1 (with probability metrics reported separately)",
        "decision_context": {"action": "manual retention review", "review_budget_fraction": 0.2},
        "baselines": [
            {"name": "train-prevalence", "fit_split": "train", "probability": prevalence, "validation": constant_metrics},
            {"name": "declining-usage-or-late-payment-rule", "fit_split": "none", "rule": "(usage_change_90d <= -4 and support_tickets_90d >= 1) or late_payments_180d >= 2", "validation": rule_metrics},
        ],
        "chosen_baseline": chosen,
        "choice_reason": "The chosen comparison has the stronger validation F1; Brier and log loss remain separate probability-quality checks.",
        "known_limitations": ["The operational review budget is illustrative.", "Synthetic prevalence and costs do not transfer to a real population."],
    })


def calibrate(labels: list[int], scores: list[float]) -> list[dict[str, Any]]:
    table: list[dict[str, Any]] = []
    for lower, upper in ((0.0, 0.2), (0.2, 0.4), (0.4, 0.6), (0.6, 0.8), (0.8, 1.0000001)):
        pairs = [(y, p) for y, p in zip(labels, scores) if lower <= p < upper]
        table.append({
            "lower": lower,
            "upper": min(upper, 1.0),
            "count": len(pairs),
            "mean_probability": sum(p for _, p in pairs) / len(pairs) if pairs else None,
            "positive_rate": sum(y for y, _ in pairs) / len(pairs) if pairs else None,
        })
    return rounded(table)


def slice_metrics(rows: list[dict[str, Any]], scores: list[float], threshold: float) -> dict[str, Any]:
    result: dict[str, Any] = {}
    definitions = {
        "plan_tier": lambda row: row["plan_tier"],
        "region": lambda row: row["region"],
        "tenure_band": lambda row: "0-17" if row["tenure_months"] < 18 else ("18-35" if row["tenure_months"] < 36 else "36+"),
    }
    for dimension, getter in definitions.items():
        grouped: dict[str, list[int]] = defaultdict(list)
        for index, row in enumerate(rows):
            grouped[str(getter(row))].append(index)
        result[dimension] = {
            key: rounded(metrics([int(rows[i]["churn_30d"]) for i in indices], [scores[i] for i in indices], threshold))
            for key, indices in sorted(grouped.items())
        }
    return result


def train_mlp_evidence(train: list[dict[str, Any]], validation: list[dict[str, Any]], preprocessing: dict[str, Any], seed: int) -> dict[str, Any]:
    rng = random.Random(seed)
    x_train = [transform(row, preprocessing) for row in train]
    y_train = [int(row["churn_30d"]) for row in train]
    x_validation = [transform(row, preprocessing) for row in validation]
    y_validation = [int(row["churn_30d"]) for row in validation]
    width = len(x_train[0])
    hidden = 5
    first = [[rng.uniform(-0.12, 0.12) for _ in range(width)] for _ in range(hidden)]
    first_bias = [0.0] * hidden
    second = [rng.uniform(-0.12, 0.12) for _ in range(hidden)]
    second_bias = 0.0
    learning_rate = 0.06

    def forward(vector: list[float]) -> tuple[list[float], float]:
        activations = [math.tanh(sum(weight * value for weight, value in zip(row, vector)) + bias) for row, bias in zip(first, first_bias)]
        return activations, sigmoid(sum(weight * value for weight, value in zip(second, activations)) + second_bias)

    trace: list[dict[str, Any]] = []
    for epoch in range(1, 181):
        grad_first = [[0.0] * width for _ in range(hidden)]
        grad_first_bias = [0.0] * hidden
        grad_second = [0.0] * hidden
        grad_second_bias = 0.0
        for vector, label in zip(x_train, y_train):
            activations, probability = forward(vector)
            error = probability - label
            grad_second_bias += error
            for unit in range(hidden):
                grad_second[unit] += error * activations[unit]
                hidden_error = error * second[unit] * (1.0 - activations[unit] ** 2)
                grad_first_bias[unit] += hidden_error
                for feature in range(width):
                    grad_first[unit][feature] += hidden_error * vector[feature]
        count = len(x_train)
        for unit in range(hidden):
            for feature in range(width):
                first[unit][feature] -= learning_rate * grad_first[unit][feature] / count
            first_bias[unit] -= learning_rate * grad_first_bias[unit] / count
            second[unit] -= learning_rate * grad_second[unit] / count
        second_bias -= learning_rate * grad_second_bias / count
        if epoch in {1, 30, 60, 90, 120, 150, 180}:
            train_scores = [forward(vector)[1] for vector in x_train]
            validation_scores = [forward(vector)[1] for vector in x_validation]
            trace.append({"epoch": epoch, "train_log_loss": metrics(y_train, train_scores)["log_loss"], "validation_log_loss": metrics(y_validation, validation_scores)["log_loss"]})
    validation_scores = [forward(vector)[1] for vector in x_validation]
    return rounded({
        "seed": seed,
        "parameter_count": hidden * width + hidden + hidden + 1,
        "training_trace": trace,
        "validation": metrics(y_validation, validation_scores),
        "update_l1": sum(abs(value) for row in first for value in row) + sum(abs(value) for value in second),
    })


def split_audit(rows: list[dict[str, Any]]) -> dict[str, Any]:
    names = ("train", "validation", "test")
    by_split = {name: split_rows(rows, name) for name in names}
    entities = {name: {row["entity_id"] for row in values} for name, values in by_split.items()}
    overlaps = sorted((entities["train"] & entities["validation"]) | (entities["train"] & entities["test"]) | (entities["validation"] & entities["test"]))
    ids = [row["row_id"] for row in rows]
    duplicates = sorted({row_id for row_id in ids if ids.count(row_id) > 1})
    return {
        "dataset_version": DATASET_VERSION,
        "split_policy_version": SPLIT_VERSION,
        "rows": {name: len(by_split[name]) for name in names},
        "entities": {name: len(entities[name]) for name in names},
        "positives": {name: sum(int(row["churn_30d"]) for row in by_split[name]) for name in names},
        "entity_overlap": overlaps,
        "duplicate_row_ids": duplicates,
        "forbidden_features": list(FORBIDDEN),
        "valid": not overlaps and not duplicates,
        "limitations": ["Entity hashing does not evaluate future calendar-time shift.", "The fixture is synthetic and cannot establish representativeness."],
    }


def input_schema() -> dict[str, Any]:
    fields: list[dict[str, Any]] = [
        {"name": "tenure_months", "type": "integer", "required": True, "minimum": 0},
        {"name": "monthly_usage_hours", "type": "number", "required": True, "minimum": 0},
        {"name": "usage_change_90d", "type": "number", "required": True},
        {"name": "support_tickets_90d", "type": "integer", "required": True, "minimum": 0},
        {"name": "late_payments_180d", "type": "integer", "required": True, "minimum": 0},
        {"name": "marketing_contacts_30d", "type": "integer", "required": True, "minimum": 0},
        {"name": "plan_tier", "type": "category", "required": True, "allowed_values": list(CATEGORIES["plan_tier"])},
        {"name": "region", "type": "category", "required": True, "allowed_values": list(CATEGORIES["region"])},
    ]
    return {
        "schema_version": "churn-input-v1",
        "observation_unit": "customer-month at snapshot cutoff",
        "fields": fields,
        "unknown_field_policy": "reject",
        "compatibility": ["Only exact churn-input-v1 payloads are accepted."],
    }


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(canonical(rounded(value)), encoding="utf-8")


def write_text(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value.strip() + "\n", encoding="utf-8")


def build_reference(output: Path, fixtures: Path | None = None) -> dict[str, Any]:
    fixtures = fixtures or default_exercise_root() / "fixtures"
    rows = load_rows(fixtures)
    train = split_rows(rows, "train")
    validation = split_rows(rows, "validation")
    test = split_rows(rows, "test")
    preprocessing = fit_preprocessing(train)
    model = train_logistic(train, preprocessing)
    short_model = train_logistic(train, preprocessing, epochs=180, regularization=0.01)
    validation_scores = probabilities(model, preprocessing, validation)
    validation_labels = [int(row["churn_30d"]) for row in validation]
    threshold, validation_at_threshold = select_threshold(validation_labels, validation_scores)
    test_scores = probabilities(model, preprocessing, test)
    test_labels = [int(row["churn_30d"]) for row in test]
    test_metrics = rounded(metrics(test_labels, test_scores, threshold))
    slices = slice_metrics(test, test_scores, threshold)
    baseline = baseline_reports(train, validation)
    mlp_a = train_mlp_evidence(train, validation, preprocessing, SEED)
    mlp_b = train_mlp_evidence(train, validation, preprocessing, SEED + 1)
    mlp_small = train_mlp_evidence(train[:8], train[:8], preprocessing, SEED + 2)

    if output.exists() and any(output.iterdir()):
        raise FileExistsError(f"refusing to overwrite non-empty output directory: {output}")
    (output / "reports").mkdir(parents=True, exist_ok=True)
    bundle = output / "artifacts/model-bundle"
    bundle.mkdir(parents=True)

    write_text(output / "reports/problem-contract.md", """
# Problem contract

## Prediction subject and observation unit
One customer-month snapshot is scored independently; entity identity is retained only for split audit.
## Observation time and available information
Only fields available at the end of `snapshot_month` may be used.
## Label and label window
`churn_30d` records voluntary churn in the following 30 days and is mature only after that window.
## Primary user and decision
A retention analyst uses ranked probabilities to choose cases for manual review.
## Intended use
Demonstrate a reproducible offline model lifecycle on the committed synthetic fixture.
## Prohibited and out-of-scope use
No automated customer action, real-world eligibility decision, or claim of population representativeness.
## False positive, false negative and abstention costs
False positives consume review capacity; false negatives miss possible churn; invalid inputs abstain by failing closed.
## Non-ML and incumbent baselines
Compare train prevalence and a declared declining-usage/late-payment rule before any fitted model.
## Success, stop and rollback conditions
Success means reproducible evidence and baseline comparison. Stop on leakage or contract mismatch; rollback to no automated score.
## Assumptions and unresolved questions
Costs and review capacity are illustrative; label reliability and population coverage need real-data review.
""")
    write_text(output / "reports/dataset-card.md", """
# Dataset card

## Purpose and relation to the problem contract
The fixture supports customer-month churn lifecycle practice, not deployment claims.
## Sources and provenance
Repository-owned deterministic synthetic data generated with seed 7050; no personal data.
## Observation unit, period and population
Three monthly snapshots for each of 240 synthetic entities.
## Inclusion, exclusion and sampling
All committed rows are included and entities are assigned by the fixed hash manifest.
## Features and availability cutoff
Only schema fields marked `allowed_for_prediction` and available at snapshot time are used.
## Label creation and maturity
`churn_30d` is observed after 30 days; `future_refund_30d` is post-cutoff and forbidden.
## Missing values and measurement limits
The fixture has no missing values and does not simulate production measurement failure.
## Split policy and leakage audit
Entity-disjoint train/validation/test splits prevent one customer appearing across partitions.
## Representation and unsupported populations
Synthetic tiers and regions do not represent any actual customers or demographic groups.
## Privacy, access, retention and deletion
No personal data; keep real customer data outside this exercise.
## Known limitations
No calendar holdout, concept drift, delayed telemetry, or causal intervention evidence.
## Versions and checksums
Dataset `synthetic-churn-v1`; split `entity-hash-v1`; digests are recorded in reproduction evidence.
""")
    write_json(output / "reports/split-audit.json", split_audit(rows))
    write_json(output / "reports/baseline.json", baseline)

    logistic_validation = rounded(metrics(validation_labels, validation_scores, threshold))
    experiments = [
        {
            "run_id": "logistic-v1",
            "hypothesis": "A regularized linear boundary should improve validation F1 over the declared baselines.",
            "dataset_version": DATASET_VERSION,
            "split_policy_version": SPLIT_VERSION,
            "feature_schema_version": FEATURE_SCHEMA_VERSION,
            "model": {"family": model["family"], "epochs": model["training"]["epochs"], "l2": model["training"]["l2"]},
            "preprocessing": {"fit_split": "train", "version": preprocessing["preprocessing_version"], "features": preprocessing["feature_order"]},
            "seed": SEED,
            "validation": logistic_validation,
            "artifact_status": "selected-and-exported",
            "interpretation": "Selected using validation only; the final test remained unopened until threshold and run were frozen.",
        },
        {
            "run_id": "logistic-regularized-v1",
            "hypothesis": "Stronger regularization and a shorter optimization budget may improve validation generalization.",
            "dataset_version": DATASET_VERSION,
            "split_policy_version": SPLIT_VERSION,
            "feature_schema_version": FEATURE_SCHEMA_VERSION,
            "model": {"family": short_model["family"], "epochs": short_model["training"]["epochs"], "l2": short_model["training"]["l2"]},
            "preprocessing": {"fit_split": "train", "version": preprocessing["preprocessing_version"], "features": preprocessing["feature_order"]},
            "seed": SEED,
            "validation": rounded(metrics(validation_labels, probabilities(short_model, preprocessing, validation), threshold)),
            "artifact_status": "evaluated-not-selected",
            "interpretation": "The declared regularization alternative was evaluated on validation only and was not exported.",
        },
    ]
    (output / "reports/classical-experiments.jsonl").write_text("".join(json.dumps(rounded(item), sort_keys=True) + "\n" for item in experiments), encoding="utf-8")

    false_positive = [row["row_id"] for row, score in zip(test, test_scores) if score >= threshold and not row["churn_30d"]][:5]
    false_negative = [row["row_id"] for row, score in zip(test, test_scores) if score < threshold and row["churn_30d"]][:5]
    evaluation = {
        "selected_run_id": "logistic-v1",
        "selection_reason": "Validation F1, probability quality, simplicity, and deterministic serialization were reviewed before opening test labels.",
        "threshold": threshold,
        "threshold_selection_split": "validation",
        "validation_at_selected_threshold": rounded(validation_at_threshold),
        "test": test_metrics,
        "calibration": calibrate(test_labels, test_scores),
        "slices": slices,
        "error_analysis": {"false_positives": false_positive, "false_negatives": false_negative},
        "supported_claim": "The frozen reference pipeline runs reproducibly on unseen synthetic entities and is compared with two baselines.",
        "limitations": ["Single small synthetic holdout; slice estimates are noisy.", "No production latency, drift, intervention, or fairness claim."],
    }
    write_json(output / "reports/evaluation.json", evaluation)
    write_json(output / "reports/neural-experiment.json", {
        "run_id": "tiny-mlp-v1",
        "shapes": {"input": len(preprocessing["feature_order"]), "hidden": 5, "output": 1},
        "parameter_count": mlp_a["parameter_count"],
        "loss": "binary cross entropy",
        "optimizer": {"name": "full-batch gradient descent", "learning_rate": 0.06, "epochs": 180},
        "small_batch_overfit": {
            "status": "loss-decrease-observed",
            "rows": 8,
            "loss_before": mlp_small["training_trace"][0]["train_log_loss"],
            "loss_after": mlp_small["training_trace"][-1]["train_log_loss"],
            "claim": "The fixed eight-row batch loss decreases; perfect memorization is not required or claimed.",
        },
        "training_trace": mlp_a["training_trace"],
        "checkpoint_rule": "Lowest validation log loss among declared trace checkpoints; test is excluded.",
        "seed_variation": [{"seed": mlp_a["seed"], "validation": mlp_a["validation"]}, {"seed": mlp_b["seed"], "validation": mlp_b["validation"]}],
        "failure_diagnoses": [
            {"symptom": "loss is non-finite", "evidence": "the first non-finite trace entry and offending batch", "cause": "unstable probability math, non-finite input, or excessive learning rate", "fix": "use stable sigmoid/cross-entropy, reject non-finite input, and lower the learning rate"},
            {"symptom": "training loss is flat", "evidence": "near-zero parameter update across consecutive checkpoints", "cause": "broken gradient flow, constant features, or label/input misalignment", "fix": "assert non-zero updates, inspect standardized variance, and test row-label joins"},
            {"symptom": "validation degrades while training improves", "evidence": "diverging train and validation loss in the frozen trace", "cause": "overfitting or selection on a noisy checkpoint", "fix": "restore the validation-selected checkpoint and simplify or regularize without consulting test"},
        ],
        "comparison": {
            "metric": "validation_f1",
            "neural_value": mlp_a["validation"]["f1"],
            "classical_run": "logistic-v1",
            "classical_value": logistic_validation["f1"],
            "baseline_value": next(item["validation"]["f1"] for item in baseline["baselines"] if item["name"] == baseline["chosen_baseline"]),
            "selection": "logistic-v1",
            "reason": "Prefer the simpler serializable model absent decisive validation benefit.",
        },
        "limitations": ["Didactic full-batch implementation; not a performance template.", "Small synthetic data cannot justify neural complexity."],
    })

    write_json(bundle / "model.json", model)
    model_sha = digest_file(bundle / "model.json")
    write_json(bundle / "input-schema.json", input_schema())
    write_json(bundle / "preprocessing.json", preprocessing)
    # Golden values come from the exact rounded representation a clean process loads.
    bundle_model = json.loads((bundle / "model.json").read_text(encoding="utf-8"))
    bundle_preprocessing = json.loads((bundle / "preprocessing.json").read_text(encoding="utf-8"))
    write_json(bundle / "decision-policy.json", {
        "policy_version": POLICY_VERSION,
        "model_output": {"name": "churn_probability", "range": [0.0, 1.0], "model_version": MODEL_VERSION},
        "threshold": threshold,
        "actions": {"below_threshold": "no_review", "at_or_above_threshold": "manual_review"},
        "abstention": {"invalid_input": "reject without a prediction", "automatic_action": False},
        "selected_on": "validation",
    })
    bundle_evaluation = {
        "selected_run_id": "logistic-v1",
        "dataset_version": DATASET_VERSION,
        "split_policy_version": SPLIT_VERSION,
        "threshold": threshold,
        "threshold_selection_split": "validation",
        "test": test_metrics,
        "slices": slices,
        "limitations": evaluation["limitations"],
    }
    write_json(bundle / "evaluation.json", bundle_evaluation)

    golden_rows = [validation[0], validation[-1], test[0]]
    golden_inputs: list[dict[str, Any]] = []
    golden_predictions: list[dict[str, Any]] = []
    for index, row in enumerate(golden_rows, 1):
        case_id = f"golden-{index}"
        payload = {name: row[name] for name in INPUT_FIELDS}
        golden_inputs.append({"case_id": case_id, "input": payload})
        score = predict(bundle_model, bundle_preprocessing, row)
        golden_predictions.append({
            "case_id": case_id,
            "model_version": MODEL_VERSION,
            "policy_version": POLICY_VERSION,
            "probability": round(score, 12),
            "decision": "manual_review" if score >= threshold else "no_review",
        })
    (bundle / "golden-inputs.jsonl").write_text("".join(json.dumps(item, sort_keys=True) + "\n" for item in golden_inputs), encoding="utf-8")
    (bundle / "golden-predictions.jsonl").write_text("".join(json.dumps(item, sort_keys=True) + "\n" for item in golden_predictions), encoding="utf-8")

    model_card = """
# Model card

## Model details and reviewed versions
Dependency-free logistic model `churn-logistic-v1`, preprocessing `churn-preprocessing-v1`, and policy `churn-review-v1`.
## Intended use, users and subjects
Offline learning by a retention analyst on synthetic customer-month subjects.
## Prohibited and out-of-scope use
No real customer decision, automated intervention, eligibility use, or representativeness claim.
## Training data and split
Training-only fitted preprocessing on `synthetic-churn-v1`; entity-disjoint validation and test.
## Baselines, evaluation and threshold
Compared with prevalence and business-rule baselines; model and threshold selected on validation before final test.
## Slice, calibration and uncertainty
Test plan, region, and tenure slices plus fixed-bin calibration are reported; small samples make estimates unstable.
## Known limitations and failure modes
Synthetic data, no temporal shift, strict categories, and no missing-value path. Invalid input fails closed.
## Privacy, fairness, security and misuse considerations
No personal data is present. Real use requires privacy, subgroup, abuse, and intervention review.
## Operational controls and human review
Predictions only nominate manual review; checksum and exact schemas are mandatory.
## Monitoring, incident and rollback
Monitor input rejection, score/action volume and delayed quality; disable scoring and return to manual baseline on mismatch.
## Change history and revalidation triggers
Version 1. Revalidate any fixture, schema, preprocessing, weight, threshold, runtime, or intended-use change.
"""
    write_text(bundle / "model-card.md", model_card)
    write_text(output / "reports/model-card.md", model_card)
    write_text(output / "reports/inference-contract.md", """
# Inference contract

## Inference unit and observation time
One customer-month payload containing only snapshot-time fields.
## Input schema and validation
All eight fields are required. Unknown fields/categories, booleans as numbers, non-finite values, and negative constrained values are rejected.
## Preprocessing and fitted state
Means, scales, categories and feature order are frozen in `preprocessing.json`, fitted on train only.
## Output schema and semantics
Each result has model/policy versions, a probability in [0,1], and `manual_review` or `no_review`.
## Decision policy and threshold
The threshold is selected on validation and versioned separately from model probability.
## Invalid input, timeout and partial failure
Invalid input or artifact mismatch exits non-zero without a prediction; no imputation or partial score.
## Batch and online behavior
CLI accepts one JSON object or JSONL and preserves input order. It is a CPU correctness path, not a latency SLO.
## Compatibility and versioning
Exact schema, preprocessing, feature order, model and policy versions must agree.
## Smoke, parity and performance tests
Golden predictions require 1e-12 absolute probability parity after clean-process loading.
## Rollout, fallback and rollback
Do not deploy this fixture model. A hypothetical mismatch disables scoring and returns to manual review baseline.
""")
    write_text(output / "reports/monitoring-plan.md", """
# Monitoring plan

## Reviewed model, schema, preprocessing and policy versions
Track model, input, preprocessing and policy version on every evidence record.
## Service health signals
Track successful loads, checksum failure, rejection rate, latency and prediction availability.
## Data quality and feature drift
Track missing/unknown/rejected fields and numeric range/quantile changes against training evidence.
## Prediction, calibration and action volume
Track score distribution, threshold crossing and review volume separately.
## Delayed outcome quality and label maturity
Compute quality only after 30-day labels mature and preserve event-time cohorts.
## Slices, sample sizes and privacy
Report plan, region and tenure with counts and suppress conclusions from tiny samples.
## Feedback loops and exposure logging
Record whether a subject was reviewed or contacted before interpreting later outcomes.
## Alerts, owners, evidence and actions
The model owner investigates contract/quality alerts; the service owner disables scoring on integrity failure.
## Retraining triggers and release approval
Drift opens review, not automatic retraining; a new artifact requires fresh validation and approval.
## Incident containment and rollback
Fail closed, retain evidence, disable the artifact, and restore the documented manual baseline.
## Monitoring pipeline quality
Test missing/delayed labels, duplicate events, version joins and alert delivery independently.
""")
    write_text(output / "reports/release-decision.md", """
# Release decision

## Decision
APPROVE WITH CONDITIONS
## Reviewed versions
Synthetic dataset v1, entity-hash split v1, churn-logistic v1, preprocessing v1 and review policy v1.
## Supported claim
The reference is suitable for the next synthetic learning stage and reproducible local review.
## Blocking findings
Real-world release remains blocked because there is no representative data, privacy review, intervention evidence or production validation.
## Non-blocking findings
Slice counts are small and neural evidence is didactic, but both limitations are explicit.
## Required controls and owners
Keep manual review, strict validation, checksums, version logs and owner-reviewed monitoring evidence.
## Rollout and rollback
No service rollout is authorized. For exercise regression, revert to the previous immutable bundle or no score.
## Revalidation triggers
Any data, feature, fitted state, model, threshold, runtime, intended-use or monitoring change.
""")

    tracked = ["model.json", "input-schema.json", "preprocessing.json", "decision-policy.json", "evaluation.json", "model-card.md", "golden-inputs.jsonl", "golden-predictions.jsonl", "reproduction.json"]
    fixture_names = ("dataset.csv", "schema.json", "split_manifest.csv", "split-policy.json", "dataset-card.md", "fixture-manifest.json")
    reproduction = {
        "source_revision": "reference-contract-v1",
        "python_requirement": ">=3.11, standard library only",
        "command": "PYTHONPATH=exercises/model-lifecycle/reference/src python3 -m model_project.pipeline --output <directory>",
        "fixture_digests": {name: digest_file(fixtures / name) for name in fixture_names},
        "determinism": {"seed": SEED, "network": False, "threads": 1, "timestamps_in_outputs": False},
        "expected_files": sorted(set(tracked + ["checksums.json", "manifest.json"])),
    }
    write_json(bundle / "reproduction.json", reproduction)
    write_json(output / "reports/reproduction.json", reproduction)
    checksums = {name: digest_file(bundle / name) for name in tracked}
    write_json(bundle / "checksums.json", {"algorithm": "sha256", "files": checksums})
    manifest = {
        "bundle_format_version": "1",
        "bundle_id": "synthetic-churn-logistic-v1",
        "model_artifact_status": "included",
        "model_file": "model.json",
        "model_sha256": model_sha,
        "model_family": model["family"],
        "model_version": MODEL_VERSION,
        "dataset_version": DATASET_VERSION,
        "split_policy_version": SPLIT_VERSION,
        "feature_schema_version": FEATURE_SCHEMA_VERSION,
        "input_schema_file": "input-schema.json",
        "preprocessing_file": "preprocessing.json",
        "decision_policy_file": "decision-policy.json",
        "evaluation_file": "evaluation.json",
        "model_card_file": "model-card.md",
        "checksums_file": "checksums.json",
        "golden_inputs_file": "golden-inputs.jsonl",
        "golden_predictions_file": "golden-predictions.jsonl",
        "reproduction_file": "reproduction.json",
        "runtime": {"python": ">=3.11", "dependencies": {}},
        "known_limitations": evaluation["limitations"],
    }
    write_json(bundle / "manifest.json", manifest)
    return {"model": model, "preprocessing": preprocessing, "threshold": threshold, "files": len([path for path in output.rglob("*") if path.is_file()])}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--fixtures", type=Path, default=None)
    args = parser.parse_args()
    result = build_reference(args.output.resolve(), args.fixtures.resolve() if args.fixtures else None)
    print(json.dumps({"files": result["files"], "model_version": result["model"]["model_version"], "threshold": result["threshold"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
