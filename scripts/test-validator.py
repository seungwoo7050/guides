#!/usr/bin/env python3
"""Prove that repository validation rejects representative contract defects."""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def copy_repository(destination: Path) -> None:
    def ignore(_directory: str, names: list[str]) -> set[str]:
        return {name for name in names if name in {".git", ".guide", "target", "__pycache__"}}

    shutil.copytree(ROOT, destination, symlinks=True, ignore=ignore)


def validate(root: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["python3", "scripts/validate.py"],
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )


def mutate_text(root: Path, relative: str, old: str, new: str) -> None:
    path = root / relative
    text = path.read_text(encoding="utf-8")
    if old not in text:
        raise AssertionError(f"mutant precondition missing in {relative}: {old}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def main() -> int:
    baseline = validate(ROOT)
    if baseline.returncode:
        raise SystemExit("validator baseline failed:\n" + baseline.stdout + baseline.stderr)

    mutations = [
        (
            "missing required document",
            lambda root: (root / "docs/00-roadmap.md").unlink(),
        ),
        (
            "missing pedagogy heading",
            lambda root: mutate_text(
                root,
                "exercises/01-boundaries-and-failure/01-uncertain-outcome/README.md",
                "## 자기 설명",
                "## 설명",
            ),
        ),
        (
            "unfinished reference",
            lambda root: mutate_text(
                root,
                "exercises/01-boundaries-and-failure/01-uncertain-outcome/reference/src/main/java/dev/guides/distributed/uncertain/UncertainOutcome.java",
                "public final class UncertainOutcome",
                "// TODO unfinished reference\npublic final class UncertainOutcome",
            ),
        ),
        (
            "divergent skeleton test",
            lambda root: mutate_text(
                root,
                "exercises/01-boundaries-and-failure/01-uncertain-outcome/skeleton/src/test/java/dev/guides/distributed/uncertain/UncertainOutcomeTest.java",
                "public final class UncertainOutcomeTest",
                "public final class UncertainOutcomeTest /* divergent */",
            ),
        ),
        (
            "obsolete path",
            lambda root: (root / "reference").mkdir(),
        ),
        (
            "floating Kafka tag",
            lambda root: mutate_text(
                root,
                "exercises/90-optional-labs/single-broker-kraft/reference/compose.yaml",
                "apache/kafka:4.3.1",
                "apache/kafka:latest",
            ),
        ),
    ]

    for name, mutate in mutations:
        with tempfile.TemporaryDirectory(prefix="guide-distributed-validator-") as temporary:
            clone = Path(temporary) / "repository"
            copy_repository(clone)
            mutate(clone)
            outcome = validate(clone)
            if outcome.returncode == 0:
                raise AssertionError(f"validator accepted mutant: {name}")
            print(f"[PASS] validator rejected {name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
