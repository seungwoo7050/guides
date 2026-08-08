#!/usr/bin/env python3
"""The answer checker must reject five independent known-bad answers."""

from __future__ import annotations

import copy
import importlib.util
import json
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

ROOT = Path(__file__).resolve().parents[1]
EXERCISE = ROOT / "exercises/system-investigation"
REFERENCE = EXERCISE / "reference/diagnoses.json"
spec = importlib.util.spec_from_file_location("check_answers", EXERCISE / "check_answers.py")
if spec is None or spec.loader is None:
    raise RuntimeError("check_answers.py를 불러오지 못했습니다.")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


@dataclass(frozen=True)
class Mutant:
    name: str
    expected: str
    apply: Callable[[dict], None]


def first(data: dict) -> dict:
    return data["cases"][sorted(data["cases"])[0]]


def missing_case(data: dict) -> None:
    del data["cases"][sorted(data["cases"])[0]]


def wrong_layer(data: dict) -> None:
    first(data)["layer"] = "unknown-layer"


def unsafe_command(data: dict) -> None:
    first(data)["observation_commands"].append("sudo rm -rf /tmp/example")


def vague_evidence(data: dict) -> None:
    first(data)["expected_evidence"] = "근거 없음"


def one_regression(data: dict) -> None:
    first(data)["regression_checks"] = ["한 번만 확인하는 불충분한 회귀 검사입니다."]


MUTANTS = (
    Mutant("missing case", "누락된 사례", missing_case),
    Mutant("wrong layer", "layer는", wrong_layer),
    Mutant("unsafe observation", "위험하거나", unsafe_command),
    Mutant("vague evidence", "40자 이상", vague_evidence),
    Mutant("single regression", "두 개 이상", one_regression),
)


def main() -> int:
    baseline = json.loads(REFERENCE.read_text(encoding="utf-8"))
    if module.validate(REFERENCE):
        print("FAIL answer validator baseline")
        return 1
    with tempfile.TemporaryDirectory(prefix="unix-answer-mutants-") as directory:
        for index, mutant in enumerate(MUTANTS, 1):
            data = copy.deepcopy(baseline)
            mutant.apply(data)
            path = Path(directory) / f"mutant-{index}.json"
            path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            errors = module.validate(path)
            if not errors or not any(mutant.expected in message for message in errors):
                print(f"FAIL mutant survived or failed unexpectedly: {mutant.name}: {errors}")
                return 1
            print(f"PASS answer mutant rejected: {mutant.name}")
    print(f"ANSWER MUTANTS: PASS ({len(MUTANTS)})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
