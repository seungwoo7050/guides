#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

EXERCISE = Path(__file__).resolve().parents[1]
ROOT = Path(__file__).resolve().parents[3]
FIXTURES = EXERCISE / "fixtures"
TIMEOUT_SECONDS = 45


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def run(
    command: list[str],
    *,
    cwd: Path,
    environment: dict[str, str] | None = None,
    expect_success: bool = True,
) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run(
        command,
        cwd=cwd,
        env=environment,
        text=True,
        capture_output=True,
        check=False,
        timeout=TIMEOUT_SECONDS,
    )
    if expect_success and completed.returncode != 0:
        detail = (completed.stdout + completed.stderr).strip()
        raise AssertionError(f"candidate command failed ({completed.returncode}): {detail}")
    return completed


def source_fingerprint(candidate: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(candidate.rglob("*")):
        if not path.is_file() or path.is_symlink() or "__pycache__" in path.parts or path.suffix == ".pyc":
            continue
        digest.update(path.relative_to(candidate).as_posix().encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def build_candidate(candidate: Path, fixtures: Path, output: Path) -> None:
    environment = os.environ.copy()
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    candidate_script = candidate / "candidate.py"
    pipeline = candidate / "src/model_project/pipeline.py"
    if candidate_script.is_file():
        command = [
            sys.executable,
            str(candidate_script),
            "--fixtures",
            str(fixtures),
            "--output",
            str(output),
        ]
    elif pipeline.is_file():
        environment["PYTHONPATH"] = str(candidate / "src")
        command = [
            sys.executable,
            "-m",
            "model_project.pipeline",
            "--fixtures",
            str(fixtures),
            "--output",
            str(output),
        ]
    else:
        raise AssertionError("candidate.py or src/model_project/pipeline.py is required")
    run(command, cwd=candidate, environment=environment)


def validate_output(output: Path) -> None:
    completed = run(
        [
            sys.executable,
            str(ROOT / "scripts/check-submission.py"),
            "--workspace",
            str(output),
            "--stage",
            "8",
        ],
        cwd=ROOT,
        expect_success=False,
    )
    if completed.returncode != 0:
        detail = (completed.stdout + completed.stderr).strip()
        raise AssertionError(f"strict lifecycle validation failed: {detail}")

    preprocessing = load_json(output / "artifacts/model-bundle/preprocessing.json")
    evaluation = load_json(output / "reports/evaluation.json")
    experiments = [
        json.loads(line)
        for line in (output / "reports/classical-experiments.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if preprocessing.get("fit_split") != "train":
        raise AssertionError("preprocessing must be fitted on train only")
    if "future_refund_30d" in preprocessing.get("feature_order", []):
        raise AssertionError("forbidden future_refund_30d was exported as a feature")
    if evaluation.get("threshold_selection_split") != "validation":
        raise AssertionError("model and threshold selection must use validation, never test")
    if any("test" in record for record in experiments):
        raise AssertionError("classical selection records contain test evidence")


def mutate_test_labels(destination: Path) -> None:
    shutil.copytree(FIXTURES, destination)
    with (destination / "split_manifest.csv").open(newline="", encoding="utf-8") as handle:
        test_ids = {row["row_id"] for row in csv.DictReader(handle) if row["split"] == "test"}
    dataset = destination / "dataset.csv"
    with dataset.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
        fieldnames = list(rows[0])
    for row in rows:
        if row["row_id"] in test_ids:
            row["churn_30d"] = "0" if row["churn_30d"] == "1" else "1"
    with dataset.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def check_test_independence(candidate: Path, first_output: Path, temporary: Path) -> None:
    mutated_fixtures = temporary / "mutated-fixtures"
    mutate_test_labels(mutated_fixtures)
    second_output = temporary / "mutated-output"
    build_candidate(candidate, mutated_fixtures, second_output)
    stable_files = [
        "artifacts/model-bundle/model.json",
        "artifacts/model-bundle/preprocessing.json",
        "artifacts/model-bundle/decision-policy.json",
        "reports/classical-experiments.jsonl",
    ]
    for relative in stable_files:
        if (first_output / relative).read_bytes() != (second_output / relative).read_bytes():
            raise AssertionError(f"changing test labels changed selection or fitted state: {relative}")


def check_clean_inference(candidate: Path, output: Path, temporary: Path) -> None:
    inference = candidate / "src/model_project/inference.py"
    if not inference.is_file():
        return
    environment = os.environ.copy()
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    environment["PYTHONPATH"] = str(candidate / "src")
    bundle = output / "artifacts/model-bundle"
    completed = run(
        [
            sys.executable,
            "-m",
            "model_project.inference",
            "--bundle",
            str(bundle),
            "--input",
            str(bundle / "golden-inputs.jsonl"),
        ],
        cwd=candidate,
        environment=environment,
    )
    actual = [json.loads(line) for line in completed.stdout.splitlines() if line.strip()]
    expected = [
        json.loads(line)
        for line in (bundle / "golden-predictions.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if actual != expected:
        raise AssertionError("clean-process golden inference output mismatch")

    invalid = temporary / "invalid-input.json"
    invalid.write_text("{}\n", encoding="utf-8")
    rejected = run(
        [
            sys.executable,
            "-m",
            "model_project.inference",
            "--bundle",
            str(bundle),
            "--input",
            str(invalid),
        ],
        cwd=candidate,
        environment=environment,
        expect_success=False,
    )
    if rejected.returncode == 0:
        raise AssertionError("invalid inference input was silently accepted")


def main() -> int:
    parser = argparse.ArgumentParser(description="Public model-lifecycle candidate checker")
    parser.add_argument("--candidate", type=Path, required=True)
    args = parser.parse_args()
    candidate = args.candidate.absolute()
    try:
        if not candidate.is_dir() or candidate.is_symlink():
            raise AssertionError(f"candidate must be a real directory: {candidate}")
        before = source_fingerprint(candidate)
        with tempfile.TemporaryDirectory(prefix="lifecycle-candidate-") as raw:
            temporary = Path(raw)
            output = temporary / "output"
            build_candidate(candidate, FIXTURES, output)
            validate_output(output)
            check_test_independence(candidate, output, temporary)
            check_clean_inference(candidate, output, temporary)
        if source_fingerprint(candidate) != before:
            raise AssertionError("candidate source or workspace was modified during verification")
    except (
        AssertionError,
        OSError,
        ValueError,
        KeyError,
        TypeError,
        json.JSONDecodeError,
        subprocess.TimeoutExpired,
    ) as exc:
        print(f"ERROR {exc}")
        return 1
    print(f"MODEL LIFECYCLE OK candidate={candidate}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
