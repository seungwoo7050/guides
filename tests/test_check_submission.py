from __future__ import annotations

import hashlib
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("check_submission", ROOT / "scripts/check-submission.py")
assert SPEC is not None and SPEC.loader is not None
CHECKER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CHECKER)


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(record, sort_keys=True) + "\n" for record in records), encoding="utf-8")


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


class SubmissionWorkspace:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.bundle = root / "artifacts/model-bundle"
        self.summary = CHECKER.actual_split_summary()
        self.dataset_version, self.split_version = CHECKER.fixture_versions()
        self.feature_version = "churn-features-v1"

    def write(self) -> None:
        contracts = json.loads(CHECKER.CONTRACTS.read_text(encoding="utf-8"))
        for stage in contracts["stages"]:
            for item in stage["files"]:
                if item["type"] != "markdown":
                    continue
                path = self.root / item["path"]
                path.parent.mkdir(parents=True, exist_ok=True)
                sections = []
                for heading in item["headings"]:
                    body = "APPROVE" if heading == "Decision" else f"Concrete evidence for {heading}."
                    sections.extend((f"# {heading}", "", body, ""))
                path.write_text("\n".join(sections), encoding="utf-8")

        write_json(
            self.root / "reports/split-audit.json",
            {
                "dataset_version": self.dataset_version,
                "split_policy_version": self.split_version,
                **self.summary,
                "entity_overlap": [],
                "duplicate_row_ids": [],
                "forbidden_features": ["future_refund_30d"],
                "valid": True,
                "limitations": ["Synthetic data does not establish external validity."],
            },
        )
        write_json(
            self.root / "reports/baseline.json",
            {
                "dataset_version": self.dataset_version,
                "selection_split": "validation",
                "selection_metric": "f1",
                "decision_context": {"review_budget_fraction": 0.2},
                "baselines": [
                    {"name": "prevalence", "validation": {"f1": 0.2}},
                    {"name": "business-rule", "validation": {"f1": 0.3}},
                ],
                "chosen_baseline": "business-rule",
                "choice_reason": "It has the stronger validation F1.",
                "known_limitations": ["The review budget is synthetic."],
            },
        )
        experiments = [
            {
                "run_id": "linear-001",
                "hypothesis": "Scaling helps the linear boundary.",
                "dataset_version": self.dataset_version,
                "split_policy_version": self.split_version,
                "feature_schema_version": self.feature_version,
                "model": {"family": "logistic-regression", "regularization": 0.1},
                "preprocessing": {"fit_split": "train", "scaling": "standard"},
                "seed": 7050,
                "validation": {"f1": 0.6, "log_loss": 0.5},
                "artifact_status": "candidate",
                "interpretation": "The linear model clears the baseline.",
            },
            {
                "run_id": "tree-001",
                "hypothesis": "A shallow tree captures interactions.",
                "dataset_version": self.dataset_version,
                "split_policy_version": self.split_version,
                "feature_schema_version": self.feature_version,
                "model": {"family": "decision-tree", "max_depth": 3},
                "preprocessing": {"fit_split": "train", "encoding": "one-hot"},
                "seed": 7051,
                "validation": {"f1": 0.55, "log_loss": 0.58},
                "artifact_status": "not-selected",
                "interpretation": "The tree does not improve validation F1.",
            },
        ]
        write_jsonl(self.root / "reports/classical-experiments.jsonl", experiments)
        test_metrics = {"f1": 0.57, "precision": 0.6, "recall": 0.55}
        slices = {"region": {"north": {"count": 10, "f1": 0.5}}}
        write_json(
            self.root / "reports/evaluation.json",
            {
                "selected_run_id": "linear-001",
                "selection_reason": "Best validation F1.",
                "threshold": 0.45,
                "threshold_selection_split": "validation",
                "test": test_metrics,
                "calibration": [
                    {"lower": 0.0, "upper": 0.5, "count": 20, "mean_probability": 0.2, "positive_rate": 0.15}
                ],
                "slices": slices,
                "error_analysis": {"false_positives": ["r1"], "false_negatives": ["r2"]},
                "supported_claim": "The candidate clears the synthetic baseline.",
                "limitations": ["No real population is represented."],
            },
        )
        diagnoses = [
            {
                "symptom": f"failure-{index}",
                "evidence": f"trace-{index}",
                "root_cause": f"cause-{index}",
                "fix": f"fix-{index}",
            }
            for index in range(3)
        ]
        write_json(
            self.root / "reports/neural-experiment.json",
            {
                "run_id": "mlp-001",
                "shapes": {"input": [8], "hidden": [4], "output": [1]},
                "parameter_count": 41,
                "loss": {"name": "binary-cross-entropy"},
                "optimizer": {"name": "sgd", "learning_rate": 0.01},
                "small_batch_overfit": {"initial_loss": 0.7, "final_loss": 0.1},
                "training_trace": [
                    {"epoch": 1, "train_loss": 0.7, "validation_loss": 0.72},
                    {"epoch": 2, "train_loss": 0.6, "validation_loss": 0.64},
                ],
                "checkpoint_rule": {"selection_split": "validation", "metric": "validation_loss"},
                "seed_variation": [{"seed": 1, "f1": 0.55}, {"seed": 2, "f1": 0.56}],
                "failure_diagnoses": diagnoses,
                "comparison": {"classical_f1": 0.57, "neural_f1": 0.56},
                "limitations": ["The neural run is intentionally small."],
            },
        )

        self.bundle.mkdir(parents=True, exist_ok=True)
        write_json(
            self.bundle / "model.json",
            {
                "format_version": 1,
                "model_version": "model-v1",
                "family": "logistic-regression",
                "feature_schema_version": self.feature_version,
                "preprocessing_version": "preprocessing-v1",
                "feature_order": ["tenure_months"],
                "weights": [0.1],
                "bias": 0.05,
                "training": {"split": "train", "seed": 7050},
            },
        )
        write_json(
            self.bundle / "input-schema.json",
            {
                "schema_version": "churn-input-v1",
                "observation_unit": "customer-month",
                "fields": [{"name": "tenure_months", "type": "integer", "required": True}],
                "unknown_field_policy": "reject",
                "compatibility": ["churn-input-v1"],
            },
        )
        write_json(
            self.bundle / "preprocessing.json",
            {
                "preprocessing_version": "preprocessing-v1",
                "fit_split": "train",
                "feature_order": ["tenure_months"],
                "steps": [{"name": "scale", "mean": 10.0}],
                "unknown_and_missing_policy": "reject",
            },
        )
        write_json(
            self.bundle / "decision-policy.json",
            {
                "policy_version": "policy-v1",
                "model_output": "probability",
                "threshold": 0.45,
                "actions": {"positive": "review", "negative": "no-review"},
                "abstention": "reject invalid input",
            },
        )
        write_json(
            self.bundle / "evaluation.json",
            {
                "selected_run_id": "linear-001",
                "dataset_version": self.dataset_version,
                "split_policy_version": self.split_version,
                "threshold": 0.45,
                "threshold_selection_split": "validation",
                "test": test_metrics,
                "slices": slices,
                "limitations": ["Synthetic evaluation only."],
            },
        )
        write_jsonl(
            self.bundle / "golden-inputs.jsonl",
            [
                {"case_id": "case-1", "input": {"tenure_months": 12}},
                {"case_id": "case-2", "input": {"tenure_months": 2}},
            ],
        )
        write_jsonl(
            self.bundle / "golden-predictions.jsonl",
            [
                {
                    "case_id": "case-1",
                    "model_version": "model-v1",
                    "probability": 0.6,
                    "decision": "review",
                    "policy_version": "policy-v1",
                },
                {
                    "case_id": "case-2",
                    "model_version": "model-v1",
                    "probability": 0.2,
                    "decision": "no-review",
                    "policy_version": "policy-v1",
                },
            ],
        )
        fixture_digests = json.loads((CHECKER.FIXTURES / "fixture-manifest.json").read_text(encoding="utf-8"))["files"]
        reproduction = {
            "source_revision": "0123456789abcdef",
            "python_requirement": ">=3.11",
            "command": "python3 -m model_project.inference --bundle artifacts/model-bundle --input input.json",
            "fixture_digests": fixture_digests,
            "determinism": {"seed": 7050, "tolerance": 1e-12},
            "expected_files": [
                "model.json",
                "golden-inputs.jsonl",
                "golden-predictions.jsonl",
                "reproduction.json",
            ],
        }
        write_json(self.bundle / "reproduction.json", reproduction)
        write_json(self.root / "reports/reproduction.json", reproduction)
        report_card = self.root / "reports/model-card.md"
        (self.bundle / "model-card.md").write_bytes(report_card.read_bytes())
        model_digest = hashlib.sha256((self.bundle / "model.json").read_bytes()).hexdigest()
        checksummed_files = [
            "model.json",
            "input-schema.json",
            "preprocessing.json",
            "decision-policy.json",
            "evaluation.json",
            "model-card.md",
            "golden-inputs.jsonl",
            "golden-predictions.jsonl",
            "reproduction.json",
        ]
        write_json(
            self.bundle / "checksums.json",
            {
                "algorithm": "sha256",
                "files": {
                    name: hashlib.sha256((self.bundle / name).read_bytes()).hexdigest() for name in checksummed_files
                },
            },
        )
        manifest = {
            "bundle_format_version": "1",
            "bundle_id": "synthetic-churn-linear-v1",
            "model_artifact_status": "included",
            "model_file": "model.json",
            "model_sha256": model_digest,
            "model_family": "logistic-regression",
            "model_version": "model-v1",
            "dataset_version": self.dataset_version,
            "split_policy_version": self.split_version,
            "feature_schema_version": self.feature_version,
            "input_schema_file": "input-schema.json",
            "preprocessing_file": "preprocessing.json",
            "decision_policy_file": "decision-policy.json",
            "evaluation_file": "evaluation.json",
            "model_card_file": "model-card.md",
            "checksums_file": "checksums.json",
            "golden_inputs_file": "golden-inputs.jsonl",
            "golden_predictions_file": "golden-predictions.jsonl",
            "reproduction_file": "reproduction.json",
            "runtime": {"python": ">=3.11", "dependencies": {"standard-library": "required"}},
            "known_limitations": ["Synthetic fixture only."],
        }
        write_json(self.bundle / "manifest.json", manifest)


class CheckSubmissionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.workspace = SubmissionWorkspace(Path(self.temporary.name))
        self.workspace.write()

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def mutate_json(self, relative: str, mutation: Any) -> None:
        path = self.workspace.root / relative
        value = read_json(path)
        mutation(value)
        write_json(path, value)

    def write_reproduction(self, value: dict[str, Any]) -> None:
        bundle_path = self.workspace.bundle / "reproduction.json"
        write_json(bundle_path, value)
        write_json(self.workspace.root / "reports/reproduction.json", value)
        checksums_path = self.workspace.bundle / "checksums.json"
        checksums = read_json(checksums_path)
        checksums["files"]["reproduction.json"] = hashlib.sha256(bundle_path.read_bytes()).hexdigest()
        write_json(checksums_path, checksums)

    def assert_rejected(self, stage: int, text: str = "") -> None:
        with self.assertRaisesRegex(AssertionError, text):
            CHECKER.validate(self.workspace.root, stage)

    def test_complete_stage_eight_is_accepted(self) -> None:
        result = CHECKER.validate(self.workspace.root, 8)
        self.assertEqual(result["stage"], 8)

    def test_stage_seven_allows_documented_missing_model_but_stage_eight_does_not(self) -> None:
        self.mutate_json(
            "artifacts/model-bundle/manifest.json",
            lambda value: value.update(model_artifact_status="not-included", model_file=None, model_sha256=None),
        )
        CHECKER.validate(self.workspace.root, 7)
        self.assert_rejected(8, "must not be null|requires an included model")

    def test_empty_placeholder_and_non_finite_evidence_are_rejected(self) -> None:
        cases = [
            ("reports/baseline.json", lambda value: value.update(choice_reason=""), 3, "must not be empty"),
            ("reports/baseline.json", lambda value: value.update(choice_reason="TODO"), 3, "placeholder"),
            ("reports/evaluation.json", lambda value: value["test"].update(f1=float("nan")), 5, "non-finite"),
            ("reports/baseline.json", lambda value: value.update(known_limitations=[]), 3, "must not be empty"),
        ]
        for relative, mutation, stage, message in cases:
            with self.subTest(relative=relative, message=message):
                with tempfile.TemporaryDirectory() as directory:
                    workspace = SubmissionWorkspace(Path(directory))
                    workspace.write()
                    value = read_json(workspace.root / relative)
                    mutation(value)
                    write_json(workspace.root / relative, value)
                    with self.assertRaisesRegex(AssertionError, message):
                        CHECKER.validate(workspace.root, stage)

    def test_cross_stage_versions_and_selection_references_are_enforced(self) -> None:
        self.mutate_json("reports/baseline.json", lambda value: value.update(dataset_version="other"))
        self.assert_rejected(3, "dataset_version")

        self.workspace.write()
        self.mutate_json("reports/baseline.json", lambda value: value.update(chosen_baseline="missing"))
        self.assert_rejected(3, "chosen_baseline")

        self.workspace.write()
        self.mutate_json("reports/evaluation.json", lambda value: value.update(selected_run_id="missing"))
        self.assert_rejected(5, "selected_run_id")

    def test_classical_runs_require_linear_train_only_selection_evidence(self) -> None:
        path = self.workspace.root / "reports/classical-experiments.jsonl"
        records = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
        for record in records:
            record["model"] = {"family": "decision-tree"}
        write_jsonl(path, records)
        self.assert_rejected(4, "linear or logistic")

        self.workspace.write()
        records = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
        records[0]["preprocessing"]["fit_split"] = "all"
        write_jsonl(path, records)
        self.assert_rejected(4, "train only")

        self.workspace.write()
        records = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
        records[0]["validation"]["test_f1"] = 0.99
        write_jsonl(path, records)
        self.assert_rejected(4, "test evidence")

    def test_evaluation_requires_finite_structured_test_calibration_and_slices(self) -> None:
        for key in ("test", "calibration", "slices"):
            with self.subTest(key=key):
                with tempfile.TemporaryDirectory() as directory:
                    workspace = SubmissionWorkspace(Path(directory))
                    workspace.write()
                    path = workspace.root / "reports/evaluation.json"
                    value = read_json(path)
                    value[key] = {}
                    write_json(path, value)
                    with self.assertRaises(AssertionError):
                        CHECKER.validate(workspace.root, 5)

    def test_neural_trace_and_diagnoses_must_be_meaningful_and_structured(self) -> None:
        self.mutate_json("reports/neural-experiment.json", lambda value: value.update(training_trace=value["training_trace"][:1]))
        self.assert_rejected(6, "at least 2")

        self.workspace.write()
        self.mutate_json(
            "reports/neural-experiment.json",
            lambda value: value.update(failure_diagnoses=["one", "two", "three"]),
        )
        self.assert_rejected(6, "non-empty object")

    def test_bundle_identity_model_digest_and_evaluation_must_agree(self) -> None:
        self.mutate_json("artifacts/model-bundle/evaluation.json", lambda value: value.update(selected_run_id="tree-001"))
        self.assert_rejected(7, "selected_run_id")

        self.workspace.write()
        self.mutate_json("artifacts/model-bundle/manifest.json", lambda value: value.update(model_sha256="0" * 64))
        self.assert_rejected(7, "checksum mismatch")

        self.workspace.write()
        self.mutate_json("artifacts/model-bundle/decision-policy.json", lambda value: value.update(threshold=0.9))
        checksums_path = self.workspace.bundle / "checksums.json"
        checksums = read_json(checksums_path)
        checksums["files"]["decision-policy.json"] = hashlib.sha256(
            (self.workspace.bundle / "decision-policy.json").read_bytes()
        ).hexdigest()
        write_json(checksums_path, checksums)
        self.assert_rejected(7, "threshold must match")

    def test_stage_eight_requires_golden_and_reproduction_references(self) -> None:
        (self.workspace.bundle / "golden-predictions.jsonl").unlink()
        self.assert_rejected(8, "missing file")

        self.workspace.write()
        reproduction = read_json(self.workspace.bundle / "reproduction.json")
        reproduction["fixture_digests"]["dataset.csv"] = "0" * 64
        write_json(self.workspace.bundle / "reproduction.json", reproduction)
        checksums_path = self.workspace.bundle / "checksums.json"
        checksums = read_json(checksums_path)
        checksums["files"]["reproduction.json"] = hashlib.sha256(
            (self.workspace.bundle / "reproduction.json").read_bytes()
        ).hexdigest()
        write_json(checksums_path, checksums)
        self.assert_rejected(8, "fixture digest")

    def test_workspace_and_nested_submission_symlinks_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            candidate = root / "candidate"
            SubmissionWorkspace(candidate).write()
            workspace_link = root / "workspace-link"
            workspace_link.symlink_to(candidate, target_is_directory=True)
            with self.assertRaisesRegex(AssertionError, "real directory"):
                CHECKER.validate(workspace_link, 1)

            reports = candidate / "reports"
            actual_reports = candidate / "actual-reports"
            reports.rename(actual_reports)
            reports.symlink_to(actual_reports, target_is_directory=True)
            with self.assertRaisesRegex(AssertionError, "symlink"):
                CHECKER.validate(candidate, 1)

    def test_reproduction_checksum_and_expected_files_are_enforced(self) -> None:
        checksums_path = self.workspace.bundle / "checksums.json"
        checksums = read_json(checksums_path)
        checksums["files"].pop("reproduction.json")
        write_json(checksums_path, checksums)
        self.assert_rejected(8, "reproduction_file")

        self.workspace.write()
        reproduction = read_json(self.workspace.bundle / "reproduction.json")
        reproduction["expected_files"].remove("model.json")
        self.write_reproduction(reproduction)
        self.assert_rejected(8, "omits manifest references")

        self.workspace.write()
        reproduction = read_json(self.workspace.bundle / "reproduction.json")
        reproduction["expected_files"].append("../outside.json")
        self.write_reproduction(reproduction)
        self.assert_rejected(8, "safe relative path")


if __name__ == "__main__":
    unittest.main()
