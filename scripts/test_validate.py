#!/usr/bin/env python3
"""Prove that the repository validator rejects representative mutations."""

from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from collections.abc import Callable
from pathlib import Path

sys.dont_write_bytecode = True
from guide_state import capture, copy_source

ROOT = Path(__file__).resolve().parents[1]
Mutation = Callable[[Path], None]


def replace(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    if old not in text:
        raise AssertionError(f"mutant target이 없습니다: {path}: {old}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def run_validator(root: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "scripts/validate.py"],
        cwd=root,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
        timeout=20,
    )


def mutations() -> list[tuple[str, Mutation]]:
    return [
        (
            "missing-required-doc",
            lambda root: (root / "docs/00-roadmap.md").unlink(),
        ),
        (
            "unexpected-tree-entry",
            lambda root: (root / "unexpected-guide-file.txt").write_text(
                "mutant\n", encoding="utf-8"
            ),
        ),
        (
            "missing-self-explanation",
            lambda root: replace(
                root / "exercises/01-language-and-domain/01-first-program/README.md",
                "## 자기 설명",
                "## 회고",
            ),
        ),
        (
            "different-skeleton-test",
            lambda root: (
                root
                / "exercises/01-language-and-domain/02-value-object-contract/skeleton/src/test/java/dev/guides/java/valueobject/MoneyTest.java"
            ).write_text(
                (
                    root
                    / "exercises/01-language-and-domain/02-value-object-contract/skeleton/src/test/java/dev/guides/java/valueobject/MoneyTest.java"
                ).read_text(encoding="utf-8")
                + "// mutant\n",
                encoding="utf-8",
            ),
        ),
        (
            "wrong-wrapper-version",
            lambda root: replace(
                root / ".mvn/wrapper/maven-wrapper.properties", "3.9.16", "3.9.15"
            ),
        ),
        (
            "reference-todo",
            lambda root: replace(
                root
                / "exercises/01-language-and-domain/02-value-object-contract/reference/src/main/java/dev/guides/java/valueobject/Money.java",
                "public record Money",
                "// TODO mutant\npublic record Money",
            ),
        ),
        (
            "broken-markdown-link",
            lambda root: (
                root / "docs/00-roadmap.md"
            ).write_text(
                (root / "docs/00-roadmap.md").read_text(encoding="utf-8")
                + "\n[mutant](missing-document.md)\n",
                encoding="utf-8",
            ),
        ),
    ]


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="guide-java-linked-worktree-") as temporary:
        fixture = Path(temporary) / "fixture"
        copied = Path(temporary) / "copied"
        fixture.mkdir()
        (fixture / "tracked.txt").write_text("tracked\n", encoding="utf-8")
        git_file = fixture / ".git"
        git_file.write_text("gitdir: /tmp/example-worktree\n", encoding="utf-8")
        linked_fingerprint = capture(fixture)
        git_file.unlink()
        regular_fingerprint = capture(fixture)
        if linked_fingerprint != regular_fingerprint:
            print("linked worktree의 .git 파일이 source fingerprint에 포함됩니다.", file=sys.stderr)
            return 1
        git_file.write_text("gitdir: /tmp/example-worktree\n", encoding="utf-8")
        copy_source(fixture, copied)
        if (copied / ".git").exists():
            print("linked worktree의 .git 파일이 격리 복사본에 포함됩니다.", file=sys.stderr)
            return 1
        print("[PASS] linked worktree .git 파일을 source 상태에서 제외")

    baseline = run_validator(ROOT)
    if baseline.returncode != 0:
        print("validator baseline이 실패했습니다.", file=sys.stderr)
        print(baseline.stdout, file=sys.stderr)
        return 1

    with tempfile.TemporaryDirectory(prefix="guide-java-validator-") as temporary:
        temporary_root = Path(temporary)
        for name, mutate in mutations():
            mutant = temporary_root / name
            mutant.mkdir()
            copy_source(ROOT, mutant)
            mutate(mutant)
            result = run_validator(mutant)
            if result.returncode == 0:
                print(f"validator가 mutant를 놓쳤습니다: {name}", file=sys.stderr)
                return 1
            print(f"[PASS] validator mutant 거부: {name}")
            shutil.rmtree(mutant)
    print("validator mutant suite를 통과했습니다.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
