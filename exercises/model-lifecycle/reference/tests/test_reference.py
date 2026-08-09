from __future__ import annotations

import copy
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from model_project.inference import ContractError, infer, load_bundle
from model_project.pipeline import (
    build_reference,
    fit_preprocessing,
    load_rows,
    probabilities,
    select_threshold,
    split_rows,
    train_logistic,
)

EXERCISE = Path(__file__).resolve().parents[2]
FIXTURES = EXERCISE / "fixtures"
COMMITTED = EXERCISE / "reference"


def file_map(root: Path) -> dict[str, bytes]:
    return {str(path.relative_to(root)): path.read_bytes() for path in root.rglob("*") if path.is_file()}


class ReferenceTests(unittest.TestCase):
    def test_train_only_preprocessing_and_selection_ignore_test_labels(self) -> None:
        rows = load_rows(FIXTURES)
        train = split_rows(rows, "train")
        validation = split_rows(rows, "validation")
        preprocessing = fit_preprocessing(train)
        train_mean = sum(row["monthly_usage_hours"] for row in train) / len(train)
        all_mean = sum(row["monthly_usage_hours"] for row in rows) / len(rows)
        stored = preprocessing["steps"][0]["means"]["monthly_usage_hours"]
        self.assertAlmostEqual(stored, train_mean)
        self.assertNotAlmostEqual(stored, all_mean)
        model = train_logistic(train, preprocessing)
        scores = probabilities(model, preprocessing, validation)
        threshold = select_threshold([row["churn_30d"] for row in validation], scores)[0]
        mutated = copy.deepcopy(rows)
        for row in mutated:
            if row["split"] == "test":
                row["churn_30d"] = 1 - row["churn_30d"]
        mutated_train = split_rows(mutated, "train")
        mutated_validation = split_rows(mutated, "validation")
        mutated_preprocessing = fit_preprocessing(mutated_train)
        mutated_model = train_logistic(mutated_train, mutated_preprocessing)
        mutated_scores = probabilities(mutated_model, mutated_preprocessing, mutated_validation)
        mutated_threshold = select_threshold([row["churn_30d"] for row in mutated_validation], mutated_scores)[0]
        self.assertEqual(model, mutated_model)
        self.assertEqual(preprocessing, mutated_preprocessing)
        self.assertEqual(threshold, mutated_threshold)

    def test_build_is_byte_deterministic_and_matches_committed_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as first, tempfile.TemporaryDirectory() as second:
            first_path, second_path = Path(first), Path(second)
            build_reference(first_path, FIXTURES)
            build_reference(second_path, FIXTURES)
            self.assertEqual(file_map(first_path), file_map(second_path))
            committed = {
                key: value
                for key, value in file_map(COMMITTED).items()
                if key.startswith("reports/") or key.startswith("artifacts/")
            }
            self.assertEqual(file_map(first_path), committed)

    def test_clean_process_golden_predictions(self) -> None:
        bundle = COMMITTED / "artifacts/model-bundle"
        command = [sys.executable, "-m", "model_project.inference", "--bundle", str(bundle), "--input", str(bundle / "golden-inputs.jsonl")]
        environment = {**os.environ, "PYTHONPATH": str(COMMITTED / "src")}
        completed = subprocess.run(command, check=True, text=True, capture_output=True, env=environment)
        actual = [json.loads(line) for line in completed.stdout.splitlines()]
        expected = [json.loads(line) for line in (bundle / "golden-predictions.jsonl").read_text(encoding="utf-8").splitlines()]
        self.assertEqual(actual, expected)

    def test_invalid_inputs_fail_closed(self) -> None:
        loaded = load_bundle(COMMITTED / "artifacts/model-bundle")
        valid = json.loads((COMMITTED / "artifacts/model-bundle/golden-inputs.jsonl").read_text(encoding="utf-8").splitlines()[0])["input"]
        for bad in (
            {key: value for key, value in valid.items() if key != "region"},
            {**valid, "unknown": 1},
            {**valid, "region": "central"},
            {**valid, "tenure_months": -1},
            {**valid, "support_tickets_90d": 1.5},
        ):
            with self.subTest(bad=bad):
                with self.assertRaises(ContractError):
                    infer(loaded, bad)

    def test_tampered_artifact_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "bundle"
            shutil.copytree(COMMITTED / "artifacts/model-bundle", target)
            model = target / "model.json"
            model.write_bytes(model.read_bytes() + b" ")
            with self.assertRaises(ContractError):
                load_bundle(target)


if __name__ == "__main__":
    unittest.main()
