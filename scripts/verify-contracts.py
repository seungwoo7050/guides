#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ALLOWED_TYPES = {"markdown", "json", "jsonl"}


def safe_relative(raw: str) -> Path:
    path = Path(raw)
    if path.is_absolute() or ".." in path.parts or not path.parts:
        raise AssertionError(f"unsafe contract path: {raw}")
    return path


def validate(path: Path) -> dict[str, int]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("contract_version") != 1:
        raise AssertionError("unsupported contract_version")
    stages = data.get("stages")
    if not isinstance(stages, list) or not stages:
        raise AssertionError("stages must be a non-empty list")
    numbers = [stage.get("stage") for stage in stages]
    if numbers != list(range(1, len(stages) + 1)) or numbers[-1] != 8:
        raise AssertionError(f"stages must be consecutive 1..8: {numbers}")

    seen: set[Path] = set()
    file_count = 0
    for stage in stages:
        if not isinstance(stage.get("title"), str) or not stage["title"].strip():
            raise AssertionError(f"stage {stage.get('stage')} has no title")
        files = stage.get("files")
        if not isinstance(files, list) or not files:
            raise AssertionError(f"stage {stage['stage']} has no files")
        for item in files:
            relative = safe_relative(item.get("path", ""))
            if relative in seen:
                raise AssertionError(f"duplicate output path: {relative}")
            seen.add(relative)
            kind = item.get("type")
            if kind not in ALLOWED_TYPES:
                raise AssertionError(f"unsupported file type for {relative}: {kind}")
            if kind == "markdown" and not item.get("headings"):
                raise AssertionError(f"markdown contract has no headings: {relative}")
            if kind in {"json", "jsonl"} and not item.get("required_keys"):
                raise AssertionError(f"structured contract has no required_keys: {relative}")
            file_count += 1

    required_templates = {
        "baseline.json",
        "bundle-evaluation.json",
        "checksums.json",
        "decision-policy.json",
        "evaluation.json",
        "problem-statement.md",
        "dataset-card.md",
        "inference-contract.md",
        "golden-inputs.jsonl",
        "golden-predictions.jsonl",
        "model-card.md",
        "monitoring-plan.md",
        "neural-experiment.json",
        "preprocessing.json",
        "release-decision.md",
        "reproduction.json",
        "split-audit.json",
        "model-bundle-manifest.json",
        "input-schema.json",
        "experiment-record.json",
    }
    templates = ROOT / "exercises/model-lifecycle/templates"
    missing = sorted(name for name in required_templates if not (templates / name).is_file())
    if missing:
        raise AssertionError(f"missing templates: {missing}")
    for json_path in templates.glob("*.json"):
        json.loads(json_path.read_text(encoding="utf-8"))
    for jsonl_path in templates.glob("*.jsonl"):
        records = [json.loads(line) for line in jsonl_path.read_text(encoding="utf-8").splitlines() if line.strip()]
        if not records:
            raise AssertionError(f"JSONL template has no records: {jsonl_path.name}")

    for source in (ROOT / "exercises/model-lifecycle/skeleton/src").rglob("*.py"):
        compile(source.read_text(encoding="utf-8"), str(source), "exec")

    return {"stages": len(stages), "files": file_count, "templates": len(required_templates)}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--contracts", type=Path, default=ROOT / "exercises/model-lifecycle/contracts/stages.json")
    args = parser.parse_args()
    try:
        summary = validate(args.contracts.resolve())
    except (AssertionError, KeyError, TypeError, json.JSONDecodeError) as exc:
        print(f"ERROR {exc}")
        return 1
    print("CONTRACTS OK " + json.dumps(summary, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
