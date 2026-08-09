from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

EXERCISE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(EXERCISE / "reference/src"))

from model_project.pipeline import build_reference  # noqa: E402


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def refresh_checksum(bundle: Path, relative: str) -> None:
    path = bundle / relative
    checksums_path = bundle / "checksums.json"
    checksums = json.loads(checksums_path.read_text(encoding="utf-8"))
    checksums["files"][relative] = hashlib.sha256(path.read_bytes()).hexdigest()
    write_json(checksums_path, checksums)


def mutate(output: Path, kind: str) -> None:
    bundle = output / "artifacts/model-bundle"
    if kind == "fit-all-splits-preprocessing":
        path = bundle / "preprocessing.json"
        value = json.loads(path.read_text(encoding="utf-8"))
        value["fit_split"] = "train+validation+test"
        write_json(path, value)
        refresh_checksum(bundle, "preprocessing.json")
    elif kind == "forbidden-feature":
        path = bundle / "preprocessing.json"
        value = json.loads(path.read_text(encoding="utf-8"))
        value["feature_order"].append("future_refund_30d")
        write_json(path, value)
        refresh_checksum(bundle, "preprocessing.json")
    elif kind == "test-based-selection":
        path = output / "reports/evaluation.json"
        value = json.loads(path.read_text(encoding="utf-8"))
        value["threshold_selection_split"] = "test"
        write_json(path, value)
    else:
        raise ValueError(f"unknown mutation: {kind}")


def main(kind: str) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fixtures", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    build_reference(args.output.resolve(), args.fixtures.resolve())
    mutate(args.output.resolve(), kind)
    print(json.dumps({"mutation": kind, "output": str(args.output)}, sort_keys=True))
    return 0
