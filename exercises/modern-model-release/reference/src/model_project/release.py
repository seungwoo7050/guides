from __future__ import annotations

import copy
import json
import math
import os
import shutil
from pathlib import Path
from typing import Any

from .core import attention, probability, read_json, sequence_feature, sha256, validate_base_tokenizer


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def load_rows(path: Path) -> list[dict[str, Any]]:
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    seen: set[str] = set()
    for row in rows:
        if not isinstance(row, dict) or set(row) != {"id", "split", "text", "label"}:
            raise ValueError("sequence row has an unexpected schema")
        if row["id"] in seen:
            raise ValueError(f"duplicate sequence id: {row['id']}")
        seen.add(row["id"])
        if row["split"] not in {"train", "validation", "test"} or row["label"] not in {0, 1}:
            raise ValueError(f"invalid split or label: {row['id']}")
    if {row["split"] for row in rows} != {"train", "validation", "test"}:
        raise ValueError("train, validation and test are all required")
    return rows


def loss_and_accuracy(rows: list[dict[str, Any]], features: dict[str, list[float]], adapter: dict[str, Any]) -> tuple[float, float]:
    losses: list[float] = []
    correct = 0
    for row in rows:
        score = probability(features[row["id"]], adapter)
        clipped = min(max(score, 1e-12), 1.0 - 1e-12)
        label = int(row["label"])
        losses.append(-(label * math.log(clipped) + (1 - label) * math.log(1.0 - clipped)))
        correct += int((score >= 0.5) == bool(label))
    return sum(losses) / len(losses), correct / len(rows)


def fit_mode(mode: str, train: list[dict[str, Any]], selection: list[dict[str, Any]], features: dict[str, list[float]]) -> dict[str, Any]:
    dimension = len(next(iter(features.values())))
    adapter: dict[str, Any] = {
        "mode": mode,
        "head_weights": [0.03 * (index + 1) for index in range(dimension)],
        "head_bias": 0.0,
    }
    if mode == "partial":
        adapter.update({"adapter_scale": [1.0] * dimension, "adapter_shift": [0.0] * dimension})
    learning_rate = 0.22 if mode == "frozen" else 0.12
    best: tuple[float, int, dict[str, Any]] | None = None
    trace: list[dict[str, Any]] = []
    for epoch in range(1, 61):
        for row in train:
            feature = features[row["id"]]
            if mode == "partial":
                transformed = [
                    math.tanh(adapter["adapter_scale"][index] * value + adapter["adapter_shift"][index])
                    for index, value in enumerate(feature)
                ]
            else:
                transformed = feature
            score = probability(feature, adapter)
            error = score - int(row["label"])
            old_weights = list(adapter["head_weights"])
            adapter["head_weights"] = [
                weight - learning_rate * error * transformed[index]
                for index, weight in enumerate(adapter["head_weights"])
            ]
            adapter["head_bias"] -= learning_rate * error
            if mode == "partial":
                for index, value in enumerate(feature):
                    derivative = 1.0 - transformed[index] ** 2
                    adapter["adapter_scale"][index] -= learning_rate * error * old_weights[index] * derivative * value
                    adapter["adapter_shift"][index] -= learning_rate * error * old_weights[index] * derivative
        train_loss, _ = loss_and_accuracy(train, features, adapter)
        selection_loss, selection_accuracy = loss_and_accuracy(selection, features, adapter)
        if best is None or selection_loss < best[0]:
            best = (selection_loss, epoch, copy.deepcopy(adapter))
        if epoch == 1 or epoch % 10 == 0:
            trace.append({
                "epoch": epoch,
                "train_log_loss": round(train_loss, 9),
                "selection_log_loss": round(selection_loss, 9),
                "selection_accuracy": round(selection_accuracy, 9),
            })
    assert best is not None
    best_loss, best_epoch, best_adapter = best
    best_accuracy = loss_and_accuracy(selection, features, best_adapter)[1]
    return {
        "mode": mode,
        "selected_epoch": best_epoch,
        "selection_log_loss": round(best_loss, 9),
        "selection_accuracy": round(best_accuracy, 9),
        "trace": trace,
        "adapter": best_adapter,
    }


def infer_payload(bundle: Path, payload: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValueError("input must be a JSON object")
    permissive = os.environ.get("MODERN_MODEL_BUG") == "invalid-input-coercion"
    if set(payload) != {"text"} and not permissive:
        raise ValueError("input must contain exactly the text field")
    manifest = read_json(bundle / "manifest.json")
    for name, expected in manifest.get("files", {}).items():
        path = bundle / name
        if not path.is_file() or sha256(path) != expected:
            raise ValueError(f"bundle digest mismatch: {name}")
    tokenizer = read_json(bundle / "tokenizer.json")
    base = read_json(bundle / "base-model.json")
    adapter = read_json(bundle / "adapter.json")
    validate_base_tokenizer(base, tokenizer)
    base_identity = adapter.get("base_model")
    if not isinstance(base_identity, dict):
        raise ValueError("adapter is missing base model identity")
    if base_identity != manifest.get("base_model"):
        raise ValueError("adapter/base manifest identity mismatch")
    if adapter.get("tokenizer") != manifest.get("tokenizer"):
        raise ValueError("adapter/tokenizer manifest identity mismatch")
    feature = sequence_feature(payload.get("text"), tokenizer, base)
    score = probability(feature, adapter)
    return {
        "decision": "escalate" if score >= float(manifest["decision_threshold"]) else "standard",
        "model_version": manifest["bundle_version"],
        "probability": round(score, 12),
    }


def build_release(fixtures: Path, output: Path) -> None:
    if output.exists() and any(output.iterdir()):
        raise ValueError("output directory must be absent or empty")
    reports = output / "reports"
    bundle = output / "artifacts" / "bundle"
    reports.mkdir(parents=True, exist_ok=True)
    bundle.mkdir(parents=True, exist_ok=True)

    tokenizer_path = fixtures / "tokenizer.json"
    base_path = fixtures / "base-model.json"
    tokenizer = read_json(tokenizer_path)
    base = read_json(base_path)
    validate_base_tokenizer(base, tokenizer)
    rows = load_rows(fixtures / "sequences.jsonl")
    features = {row["id"]: sequence_feature(row["text"], tokenizer, base) for row in rows}
    by_split = {name: [row for row in rows if row["split"] == name] for name in ("train", "validation", "test")}

    write_json(reports / "01-tokenizer-contract.json", {
        "stage": 1,
        "tokenizer": {"id": tokenizer["tokenizer_id"], "version": tokenizer["version"], "sha256": sha256(tokenizer_path)},
        "base_model": {"id": base["model_id"], "version": base["version"], "sha256": sha256(base_path)},
        "normalization": tokenizer["normalization"],
        "unknown_tokens": "reject",
        "max_length": tokenizer["max_length"],
    })

    probe = attention([1, 2, 3], base)
    future = [probe["weights"][row][column] for row in range(3) for column in range(row + 1, 3)]
    regression = read_json(fixtures / "base-regression.json")
    regression_results = []
    for case in regression["cases"]:
        actual = attention(case["token_ids"], base)["context"]
        passed = all(
            abs(actual[row][column] - case["expected_context"][row][column]) <= float(regression["absolute_tolerance"])
            for row in range(len(actual)) for column in range(len(actual[row]))
        )
        regression_results.append({"name": case["name"], "passed": passed})
    write_json(reports / "02-attention-invariants.json", {
        "stage": 2,
        "shape": [3, 3],
        "causal_mask": True,
        "softmax_axis": "keys-per-query",
        "row_sums": [round(sum(row), 12) for row in probe["weights"]],
        "maximum_future_weight": max(future),
        "base_regression": {"all_passed": all(item["passed"] for item in regression_results), "cases": regression_results},
    })

    selection_name = "test" if os.environ.get("MODERN_MODEL_BUG") == "test-based-selection" else "validation"
    comparisons = [fit_mode(mode, by_split["train"], by_split[selection_name], features) for mode in ("frozen", "partial")]
    selected = min(comparisons, key=lambda item: item["selection_log_loss"])
    test_loss, test_accuracy = loss_and_accuracy(by_split["test"], features, selected["adapter"])
    base_identity = {"id": base["model_id"], "version": base["version"], "sha256": sha256(base_path)}
    tokenizer_identity = {"id": tokenizer["tokenizer_id"], "version": tokenizer["version"], "sha256": sha256(tokenizer_path)}
    adapter = copy.deepcopy(selected["adapter"])
    adapter.update({
        "artifact_version": "adapter-v1",
        "selected_epoch": selected["selected_epoch"],
        "base_model": base_identity,
        "tokenizer": tokenizer_identity,
    })
    if os.environ.get("MODERN_MODEL_BUG") == "base-identity-missing":
        adapter.pop("base_model")

    write_json(reports / "03-transfer-comparison.json", {
        "stage": 3,
        "split_counts": {name: len(value) for name, value in by_split.items()},
        "selection_split": selection_name,
        "test_evaluations": 1,
        "base_model": base_identity,
        "tokenizer": tokenizer_identity,
        "comparisons": [{key: value for key, value in item.items() if key != "adapter"} for item in comparisons],
        "selected_mode": selected["mode"],
        "selected_epoch": selected["selected_epoch"],
        "test": {"log_loss": round(test_loss, 9), "accuracy": round(test_accuracy, 9)},
        "base_regression_passed": all(item["passed"] for item in regression_results),
    })

    copied_tokenizer = copy.deepcopy(tokenizer)
    if os.environ.get("MODERN_MODEL_BUG") == "tokenizer-base-mismatch":
        copied_tokenizer["version"] = "tok-incompatible"
    write_json(bundle / "tokenizer.json", copied_tokenizer)
    shutil.copy2(base_path, bundle / "base-model.json")
    write_json(bundle / "adapter.json", adapter)
    (bundle / "model-card.md").write_text(
        "# Model card\n\n## Intended use\nSynthetic support-message escalation demonstration only.\n\n"
        "## Evaluation\nSelection uses validation; the test split is evaluated once after selection.\n\n"
        "## Limitations\nTiny synthetic English vocabulary; no production, safety or fairness claim.\n\n"
        "## Base and tokenizer\nBase `tiny-sequence-encoder@base-v1`; tokenizer `tiny-sequence-tokenizer@tok-v1`.\n",
        encoding="utf-8",
    )
    golden_input = {"text": "calm clear help"}
    write_json(bundle / "golden-input.json", golden_input)

    manifest_tokenizer = {
        "id": copied_tokenizer["tokenizer_id"],
        "version": copied_tokenizer["version"],
        "sha256": sha256(bundle / "tokenizer.json"),
    }
    manifest_base = {"id": base["model_id"], "version": base["version"], "sha256": sha256(bundle / "base-model.json")}
    adapter["tokenizer"] = manifest_tokenizer
    if os.environ.get("MODERN_MODEL_BUG") != "base-identity-missing":
        adapter["base_model"] = manifest_base
    write_json(bundle / "adapter.json", adapter)
    provisional_manifest = {
        "bundle_version": "modern-transfer-v1",
        "base_model": manifest_base,
        "tokenizer": manifest_tokenizer,
        "decision_threshold": 0.5,
        "input_contract": {"required": ["text"], "additional_fields": False, "unknown_tokens": "reject", "max_length": 6},
        "output_contract": {"fields": ["model_version", "probability", "decision"]},
    }
    write_json(bundle / "manifest.json", provisional_manifest)
    golden_output = infer_payload(bundle, golden_input)
    write_json(bundle / "golden-output.json", golden_output)
    files = {
        name: sha256(bundle / name)
        for name in ("adapter.json", "base-model.json", "tokenizer.json", "model-card.md", "golden-input.json", "golden-output.json")
    }
    provisional_manifest["files"] = files
    write_json(bundle / "manifest.json", provisional_manifest)

    decision = "APPROVE FOR EXERCISE ONLY" if selection_name == "validation" else "REJECT"
    (reports / "04-release-review.md").write_text(
        "# Modern model release review\n\n## Decision\n" + decision + "\n\n"
        "## Evidence\nTokenizer/base identity, causal attention invariants, frozen-versus-partial validation selection, "
        "base regression, bundle digests and golden inference were recorded.\n\n"
        "## Blocking findings\nNone for the isolated synthetic exercise. Production evidence is absent.\n\n"
        "## Required controls\nReject unknown or malformed input; keep the base and tokenizer immutable; rerun regression and golden tests.\n\n"
        "## Revalidation\nAny base, tokenizer, adapter, schema, threshold or runtime change requires bundle and evaluation regeneration.\n",
        encoding="utf-8",
    )
