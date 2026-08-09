#!/usr/bin/env python3
"""Prove that representative shallow repository mutations are rejected."""

from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile


ROOT = Path(__file__).resolve().parents[1]


def copy_source(destination: Path) -> None:
    ignored = shutil.ignore_patterns(
        ".git", ".guide", "build", "build-*", "out", "workspace", ".workspace.*",
        "__pycache__", "*.pyc", "*.log", "*.spv", "*.dxil", "*.metallib",
    )
    shutil.copytree(ROOT, destination, symlinks=True, ignore=ignored)


def verifier(root: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "scripts/verify_repository.py", "--quick"],
        cwd=root,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=120,
        check=False,
    )


def expect_rejected(root: Path, label: str) -> None:
    result = verifier(root)
    if result.returncode == 0:
        raise AssertionError(f"repository verifier accepted {label}\n{result.stdout}")
    print(f"[REJECTED] {label}")


def mutate_duplicate_key(root: Path) -> None:
    path = root / "exercises/01-transform-trace/contract.json"
    text = path.read_text(encoding="utf-8")
    path.write_text(text.replace('  "id":', '  "id": "duplicate-id",\n  "id":', 1), encoding="utf-8")


def mutate_unrelated_contract(root: Path) -> None:
    path = root / "exercises/02-sampling-and-color/contract.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["known_bad_mutations"] = [
        "rotate_fog_token",
        "cache_audio_voice",
        "network_packet_loss",
        "database_schema_drift",
    ]
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def mutate_broken_anchor(root: Path) -> None:
    path = root / "README.md"
    path.write_text(
        path.read_text(encoding="utf-8")
        + "\n[깨진 anchor](docs/00-roadmap.md#anchor-that-does-not-exist)\n",
        encoding="utf-8",
    )


def mutate_repetitive_document(root: Path) -> None:
    path = root / "docs/01-visual-model/02-coordinate-spaces-and-transforms.md"
    repeated = "좌표 상태를 확인합니다. " * 20
    body = "\n".join(repeated for _ in range(40))
    path.write_text(
        "# 좌표 공간과 변환 반복 변조\n\n"
        f"## 목표\n\n{body}\n\n"
        f"## 시작하기 전에\n\n{body}\n\n"
        "## 연결 실습\n\n"
        "[실습 01](../../../exercises/01-transform-trace/README.md)\n\n"
        f"## 완료 기준\n\n{body}\n",
        encoding="utf-8",
    )


def main() -> int:
    mutations = {
        "duplicate-json-key": mutate_duplicate_key,
        "unrelated-contract-identifiers": mutate_unrelated_contract,
        "broken-markdown-anchor": mutate_broken_anchor,
        "repetitive-concept-document": mutate_repetitive_document,
    }
    with tempfile.TemporaryDirectory(prefix="cg-repository-verifier-") as raw:
        root = Path(raw)
        baseline = root / "baseline"
        copy_source(baseline)
        baseline_result = verifier(baseline)
        if baseline_result.returncode != 0:
            raise AssertionError(f"repository verifier baseline failed\n{baseline_result.stdout}")
        for label, mutation in mutations.items():
            candidate = root / label
            shutil.copytree(baseline, candidate, symlinks=True)
            mutation(candidate)
            expect_rejected(candidate, label)
    print(f"REPOSITORY_VERIFIER_NEGATIVE_TEST_OK cases={len(mutations)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
