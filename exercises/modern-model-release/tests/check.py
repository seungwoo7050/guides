#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

EXERCISE = Path(__file__).resolve().parents[1]
FIXTURES = EXERCISE / "fixtures"


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def run(candidate: Path, arguments: list[str], *, expect_success: bool = True) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run(
        [sys.executable, str(candidate / "candidate.py"), *arguments],
        cwd=candidate,
        text=True,
        capture_output=True,
        check=False,
        timeout=30,
    )
    if expect_success and completed.returncode != 0:
        raise AssertionError(f"candidate command failed: {completed.stderr.strip()}")
    return completed


def require_finite(value: Any, location: str = "root") -> None:
    if isinstance(value, float) and not math.isfinite(value):
        raise AssertionError(f"non-finite number at {location}")
    if isinstance(value, dict):
        for key, child in value.items():
            require_finite(child, f"{location}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            require_finite(child, f"{location}[{index}]")


def check_attention(candidate: Path) -> None:
    completed = run(candidate, ["attention", "--base", str(FIXTURES / "base-model.json"), "--tokens", "1,2,3"])
    result = json.loads(completed.stdout)
    weights = result["weights"]
    context = result["context"]
    if len(weights) != 3 or any(len(row) != 3 for row in weights) or len(context) != 3:
        raise AssertionError("attention shape must be [sequence, sequence] and context must preserve sequence length")
    for row_index, row in enumerate(weights):
        if abs(sum(row) - 1.0) > 1e-9:
            raise AssertionError("attention softmax must normalize keys for each query")
        if any(abs(row[column]) > 1e-12 for column in range(row_index + 1, len(row))):
            raise AssertionError("causal mask exposes a future token")
    require_finite(result)


def check_bundle(candidate: Path, output: Path) -> None:
    reports = output / "reports"
    bundle = output / "artifacts" / "bundle"
    required = [
        reports / "01-tokenizer-contract.json",
        reports / "02-attention-invariants.json",
        reports / "03-transfer-comparison.json",
        reports / "04-release-review.md",
        bundle / "manifest.json",
        bundle / "tokenizer.json",
        bundle / "base-model.json",
        bundle / "adapter.json",
        bundle / "model-card.md",
        bundle / "golden-input.json",
        bundle / "golden-output.json",
    ]
    missing = [str(path.relative_to(output)) for path in required if not path.is_file()]
    if missing:
        raise AssertionError(f"missing release artifacts: {', '.join(missing)}")

    tokenizer_report = load(required[0])
    attention_report = load(required[1])
    transfer = load(required[2])
    manifest = load(bundle / "manifest.json")
    tokenizer = load(bundle / "tokenizer.json")
    base = load(bundle / "base-model.json")
    adapter = load(bundle / "adapter.json")
    require_finite([tokenizer_report, attention_report, transfer, manifest, adapter])
    if tokenizer_report.get("unknown_tokens") != "reject":
        raise AssertionError("tokenizer contract must reject unknown tokens")
    if attention_report.get("causal_mask") is not True or attention_report.get("softmax_axis") != "keys-per-query":
        raise AssertionError("attention report does not state the tested invariants")
    if attention_report.get("maximum_future_weight") != 0 or attention_report.get("base_regression", {}).get("all_passed") is not True:
        raise AssertionError("attention/base regression evidence failed")
    if transfer.get("selection_split") != "validation":
        raise AssertionError("model and epoch selection must use validation, never test")
    if transfer.get("test_evaluations") != 1:
        raise AssertionError("the final test split must be evaluated once")
    comparisons = transfer.get("comparisons", [])
    if {item.get("mode") for item in comparisons} != {"frozen", "partial"}:
        raise AssertionError("frozen and partial transfer must both be compared")
    if any(not item.get("trace") for item in comparisons):
        raise AssertionError("each transfer mode needs a non-empty training trace")
    if transfer.get("selected_mode") not in {"frozen", "partial"} or transfer.get("base_regression_passed") is not True:
        raise AssertionError("selection or base regression evidence is incomplete")

    if base.get("tokenizer_id") != tokenizer.get("tokenizer_id") or base.get("tokenizer_version") != tokenizer.get("version"):
        raise AssertionError("bundle tokenizer is incompatible with the base model")
    if adapter.get("base_model") != manifest.get("base_model"):
        raise AssertionError("adapter must identify the exact base model")
    if adapter.get("tokenizer") != manifest.get("tokenizer"):
        raise AssertionError("adapter must identify the exact tokenizer")
    for name, expected in manifest.get("files", {}).items():
        if not (bundle / name).is_file() or digest(bundle / name) != expected:
            raise AssertionError(f"bundle digest mismatch: {name}")
    if len(manifest.get("files", {})) < 6:
        raise AssertionError("bundle manifest omits required file digests")

    valid = run(candidate, ["infer", "--bundle", str(bundle), "--input", str(bundle / "golden-input.json")])
    actual = json.loads(valid.stdout)
    if actual != load(bundle / "golden-output.json"):
        raise AssertionError("golden inference output mismatch")
    if set(actual) != {"model_version", "probability", "decision"} or not 0.0 <= actual["probability"] <= 1.0:
        raise AssertionError("inference output violates its public contract")

    bad_payloads = [
        {},
        {"text": 5},
        {"text": "calm mystery"},
        {"text": ""},
        {"text": "calm clear help kind slow safe urgent"},
        {"text": "calm", "extra": True},
    ]
    with tempfile.TemporaryDirectory(prefix="modern-invalid-") as raw:
        for index, payload in enumerate(bad_payloads):
            path = Path(raw) / f"input-{index}.json"
            path.write_text(json.dumps(payload) + "\n", encoding="utf-8")
            completed = run(candidate, ["infer", "--bundle", str(bundle), "--input", str(path)], expect_success=False)
            if completed.returncode == 0:
                raise AssertionError(f"invalid input was silently accepted: {payload!r}")

    card = (bundle / "model-card.md").read_text(encoding="utf-8")
    review = (reports / "04-release-review.md").read_text(encoding="utf-8")
    for heading in ("## Intended use", "## Evaluation", "## Limitations", "## Base and tokenizer"):
        if heading not in card:
            raise AssertionError(f"model card missing {heading}")
    for heading in ("## Decision", "## Evidence", "## Blocking findings", "## Required controls", "## Revalidation"):
        if heading not in review:
            raise AssertionError(f"release review missing {heading}")


def check_bundle_mutations(candidate: Path, bundle: Path, temporary: Path) -> None:
    golden_input = bundle / "golden-input.json"

    checksum_bundle = temporary / "checksum-bundle"
    shutil.copytree(bundle, checksum_bundle)
    with (checksum_bundle / "adapter.json").open("a", encoding="utf-8") as handle:
        handle.write("\n")
    if run(candidate, ["infer", "--bundle", str(checksum_bundle), "--input", str(golden_input)], expect_success=False).returncode == 0:
        raise AssertionError("inference accepted an adapter whose checksum changed")

    tokenizer_bundle = temporary / "tokenizer-bundle"
    shutil.copytree(bundle, tokenizer_bundle)
    tokenizer = load(tokenizer_bundle / "tokenizer.json")
    tokenizer["version"] = "tok-incompatible"
    write_json(tokenizer_bundle / "tokenizer.json", tokenizer)
    tokenizer_identity = {
        "id": tokenizer["tokenizer_id"],
        "version": tokenizer["version"],
        "sha256": digest(tokenizer_bundle / "tokenizer.json"),
    }
    adapter = load(tokenizer_bundle / "adapter.json")
    adapter["tokenizer"] = tokenizer_identity
    write_json(tokenizer_bundle / "adapter.json", adapter)
    manifest = load(tokenizer_bundle / "manifest.json")
    manifest["tokenizer"] = tokenizer_identity
    manifest["files"]["tokenizer.json"] = tokenizer_identity["sha256"]
    manifest["files"]["adapter.json"] = digest(tokenizer_bundle / "adapter.json")
    write_json(tokenizer_bundle / "manifest.json", manifest)
    if run(candidate, ["infer", "--bundle", str(tokenizer_bundle), "--input", str(golden_input)], expect_success=False).returncode == 0:
        raise AssertionError("inference accepted a tokenizer incompatible with the base model")

    identity_bundle = temporary / "base-identity-bundle"
    shutil.copytree(bundle, identity_bundle)
    adapter = load(identity_bundle / "adapter.json")
    adapter["base_model"]["version"] = "base-other"
    write_json(identity_bundle / "adapter.json", adapter)
    manifest = load(identity_bundle / "manifest.json")
    manifest["files"]["adapter.json"] = digest(identity_bundle / "adapter.json")
    write_json(identity_bundle / "manifest.json", manifest)
    if run(candidate, ["infer", "--bundle", str(identity_bundle), "--input", str(golden_input)], expect_success=False).returncode == 0:
        raise AssertionError("inference accepted an adapter bound to a different base model")


def check_test_independence(candidate: Path, first_output: Path, temporary: Path) -> None:
    mutated = temporary / "mutated-fixtures"
    shutil.copytree(FIXTURES, mutated)
    rows = [json.loads(line) for line in (mutated / "sequences.jsonl").read_text(encoding="utf-8").splitlines()]
    for row in rows:
        if row["split"] == "test":
            row["label"] = 1 - row["label"]
    (mutated / "sequences.jsonl").write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in rows), encoding="utf-8")
    second_output = temporary / "mutated-output"
    run(candidate, ["build", "--fixtures", str(mutated), "--output", str(second_output)])
    first_adapter = load(first_output / "artifacts" / "bundle" / "adapter.json")
    second_adapter = load(second_output / "artifacts" / "bundle" / "adapter.json")
    if first_adapter != second_adapter:
        raise AssertionError("changing test labels changed the selected model or fitted parameters")


def check_module_entrypoint(candidate: Path, bundle: Path) -> None:
    source = candidate / "src"
    if not (source / "model_project" / "inference.py").is_file():
        return
    environment = dict(os.environ)
    environment["PYTHONPATH"] = str(source)
    completed = subprocess.run(
        [sys.executable, "-m", "model_project.inference", "--bundle", str(bundle), "--input", str(bundle / "golden-input.json")],
        text=True,
        capture_output=True,
        check=False,
        timeout=20,
        env=environment,
    )
    if completed.returncode != 0 or json.loads(completed.stdout) != load(bundle / "golden-output.json"):
        raise AssertionError("python -m model_project.inference clean-process contract failed")


def check_committed_parity(candidate: Path, generated: Path) -> None:
    for relative in (Path("reports"), Path("artifacts/bundle")):
        committed_root = candidate / relative
        generated_root = generated / relative
        committed = {
            path.relative_to(committed_root): path.read_bytes()
            for path in committed_root.rglob("*")
            if path.is_file()
        }
        rebuilt = {
            path.relative_to(generated_root): path.read_bytes()
            for path in generated_root.rglob("*")
            if path.is_file()
        }
        if committed.keys() != rebuilt.keys():
            raise AssertionError(f"committed/generated file set differs under {relative}")
        changed = [str(path) for path in sorted(committed) if committed[path] != rebuilt[path]]
        if changed:
            raise AssertionError(f"committed/generated bytes differ under {relative}: {', '.join(changed)}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate", type=Path, required=True)
    args = parser.parse_args()
    candidate = args.candidate.resolve()
    try:
        if not (candidate / "candidate.py").is_file():
            raise AssertionError("candidate.py is required")
        check_attention(candidate)
        with tempfile.TemporaryDirectory(prefix="modern-candidate-") as raw:
            temporary = Path(raw)
            output = temporary / "output"
            run(candidate, ["build", "--fixtures", str(FIXTURES), "--output", str(output)])
            check_bundle(candidate, output)
            check_bundle_mutations(candidate, output / "artifacts" / "bundle", temporary)
            check_test_independence(candidate, output, temporary)
            check_module_entrypoint(candidate, output / "artifacts" / "bundle")
            if (candidate / "reports").is_dir() and (candidate / "artifacts" / "bundle").is_dir():
                check_committed_parity(candidate, output)
                check_bundle(candidate, candidate)
                check_module_entrypoint(candidate, candidate / "artifacts" / "bundle")
    except (AssertionError, OSError, ValueError, KeyError, TypeError, json.JSONDecodeError, subprocess.TimeoutExpired) as exc:
        print(f"ERROR {exc}")
        return 1
    print(f"MODERN MODEL RELEASE OK candidate={candidate}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
