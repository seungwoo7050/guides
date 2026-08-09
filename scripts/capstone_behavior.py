#!/usr/bin/env python3
"""Shared, deterministic helpers for the LedgerLab Capstone behavior evidence."""

from __future__ import annotations

import difflib
import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
LAB_ROOT = REPO_ROOT / "exercises/07-isolated-attack-path"
CHECKER = LAB_ROOT / "tests/check.py"
QUALITY_CHECKER = LAB_ROOT / "tests/check_quality.py"
SKELETON = LAB_ROOT / "skeleton/ledgerlab_policy.py"
REFERENCE = LAB_ROOT / "reference/ledgerlab_policy.py"


class BehaviorRunError(RuntimeError):
    def __init__(self, message: str, output: str = "") -> None:
        super().__init__(message)
        self.output = output


def load_json_object(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise BehaviorRunError(f"evidence JSON을 읽을 수 없습니다: {exc}") from exc
    if not isinstance(value, dict):
        raise BehaviorRunError("evidence JSON 최상위 값은 object여야 합니다.")
    return value


def capture(implementation: Path, expect: str) -> tuple[dict, str]:
    """Run the public lab checker and return its generated evidence and output."""
    if expect not in {"secure", "vulnerable"}:
        raise ValueError(f"지원하지 않는 behavior profile: {expect}")
    implementation = implementation.resolve()
    if not implementation.is_file():
        raise BehaviorRunError(f"implementation 파일이 없습니다: {implementation}")
    with tempfile.TemporaryDirectory(prefix="cybersecurity-capstone-") as directory:
        evidence_path = Path(directory) / "evidence.json"
        try:
            result = subprocess.run(
                [
                    sys.executable,
                    str(CHECKER),
                    "--implementation",
                    str(implementation),
                    "--expect",
                    expect,
                    "--evidence",
                    str(evidence_path),
                ],
                cwd=REPO_ROOT,
                text=True,
                capture_output=True,
                check=False,
                timeout=15,
            )
        except subprocess.TimeoutExpired as exc:
            raise BehaviorRunError("behavior 검사가 15초 안에 끝나지 않았습니다.") from exc
        output = result.stdout + result.stderr
        if result.returncode != 0:
            raise BehaviorRunError(
                f"{expect} behavior 검사가 실패했습니다(exit={result.returncode}).",
                output,
            )
        if not evidence_path.is_file():
            raise BehaviorRunError("behavior 검사가 evidence 파일을 만들지 않았습니다.", output)
        return load_json_object(evidence_path), output


def expected_patch(implementation: Path) -> str:
    skeleton_lines = SKELETON.read_text(encoding="utf-8").splitlines(keepends=True)
    implementation_lines = implementation.read_text(encoding="utf-8").splitlines(keepends=True)
    return "".join(
        difflib.unified_diff(
            skeleton_lines,
            implementation_lines,
            fromfile="skeleton/ledgerlab_policy.py",
            tofile="work/behavior-lab/ledgerlab_policy.py",
            n=0,
        )
    )


def capture_known_bad_quality() -> dict:
    """Run the canonical oracle meta-test that rejects four representative mutants."""
    try:
        result = subprocess.run(
            [sys.executable, str(QUALITY_CHECKER)],
            cwd=REPO_ROOT,
            text=True,
            capture_output=True,
            check=False,
            timeout=20,
        )
    except subprocess.TimeoutExpired as exc:
        raise BehaviorRunError("known-bad meta-test가 20초 안에 끝나지 않았습니다.") from exc
    output = result.stdout + result.stderr
    if result.returncode != 0 or "LAB QUALITY OK reference=pass skeleton=reject mutants=4" not in output:
        raise BehaviorRunError("known-bad meta-test가 기준 구현·mutant 계약을 만족하지 못했습니다.", output)
    return {
        "schema_version": 1,
        "profile": "known-bad-mutants",
        "checker_sha256": hashlib.sha256(QUALITY_CHECKER.read_bytes()).hexdigest(),
        "reference_sha256": hashlib.sha256(REFERENCE.read_bytes()).hexdigest(),
        "cases": ["deny-all", "cross-owner-allowed", "prefix-bypass", "detection-missing"],
        "result": "pass",
        "output": output,
        "limitations": [
            "canonical contract mutant 네 개만 검사하며 가능한 모든 우회 구현을 열거하지 않습니다.",
            "learner patch의 최소성과 production 공격 표면은 사람이 별도로 검토합니다.",
        ],
    }
