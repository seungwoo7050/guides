#!/usr/bin/env python3
"""Prove that the validator rejects independent layout and pedagogy defects."""

from __future__ import annotations

import os
import re
import shutil
import stat
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ("학습 목표", "선행 개념", "연결 실습", "완료 기준")


@dataclass(frozen=True)
class Mutant:
    name: str
    apply: Callable[[Path], None]


def concepts(root: Path) -> list[Path]:
    return [path for path in sorted((root / "docs").rglob("*.md"))
            if path.name != "00-roadmap.md" and all(f"## {name}" in path.read_text(encoding="utf-8") for name in CONTRACT)]


def rename_heading(root: Path, heading: str) -> None:
    path = concepts(root)[0]
    text = path.read_text(encoding="utf-8")
    anchor = f"## {heading}\n"
    if text.count(anchor) != 1:
        raise RuntimeError(f"heading anchor mismatch: {path}: {heading}")
    path.write_text(text.replace(anchor, f"## {heading} 누락\n", 1), encoding="utf-8")


def update_manifest(root: Path, relative: str) -> None:
    path = root / "scripts/layout-manifest.txt"
    lines = path.read_text(encoding="utf-8").splitlines()
    path.write_text("\n".join(sorted({*lines, relative})) + "\n", encoding="utf-8")


def arbitrary_root(root: Path) -> None:
    (root / "unexpected-root.txt").write_text("unexpected\n", encoding="utf-8")


def extra_doc(root: Path) -> None:
    (root / "docs/99-unexpected.md").write_text("# unexpected\n", encoding="utf-8")
    update_manifest(root, "docs/99-unexpected.md")


def missing_goal(root: Path) -> None: rename_heading(root, "학습 목표")
def missing_prerequisite(root: Path) -> None: rename_heading(root, "선행 개념")
def missing_connection(root: Path) -> None: rename_heading(root, "연결 실습")
def missing_completion(root: Path) -> None: rename_heading(root, "완료 기준")


def wrong_order(root: Path) -> None:
    path = concepts(root)[0]
    text = path.read_text(encoding="utf-8")
    text = text.replace("## 선행 개념\n", "## __SWAP__\n", 1)
    text = text.replace("## 연결 실습\n", "## 선행 개념\n", 1)
    text = text.replace("## __SWAP__\n", "## 연결 실습\n", 1)
    path.write_text(text, encoding="utf-8")


def short_completion(root: Path) -> None:
    path = concepts(root)[0]
    text = path.read_text(encoding="utf-8")
    changed, count = re.subn(r"(^## 완료 기준\n).*?(?=^## |\Z)",
                             r"\1\n- 첫 기준\n- 둘째 기준\n", text, count=1, flags=re.M | re.S)
    if count != 1: raise RuntimeError("completion anchor mismatch")
    path.write_text(changed, encoding="utf-8")


def remove_mode(root: Path) -> None:
    path = root / "prepare.sh"
    path.chmod(path.stat().st_mode & ~(stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH))


def add_symlink(root: Path) -> None:
    os.symlink("README.md", root / "unexpected-link")
    update_manifest(root, "unexpected-link")


def add_directory_symlink(root: Path) -> None:
    os.symlink("docs", root / "unexpected-directory-link")
    update_manifest(root, "unexpected-directory-link")


def broken_anchor(root: Path) -> None:
    path = concepts(root)[0]
    path.write_text(path.read_text(encoding="utf-8") + "\n[깨진 anchor](#definitely-missing-anchor)\n", encoding="utf-8")


def body(text: str, heading: str) -> str:
    match = re.search(rf"(^## {re.escape(heading)}\n)(.*?)(?=^## |\Z)", text, re.M | re.S)
    if not match: raise RuntimeError(f"section missing: {heading}")
    return match.group(2)


def copied_rubric(root: Path) -> None:
    source, target = concepts(root)[:2]
    source_text = source.read_text(encoding="utf-8")
    target_text = target.read_text(encoding="utf-8")
    for heading in CONTRACT:
        replacement = body(source_text, heading)
        target_text, count = re.subn(
            rf"(^## {re.escape(heading)}\n).*?(?=^## |\Z)",
            lambda match, value=replacement: match.group(1) + value,
            target_text, count=1, flags=re.M | re.S,
        )
        if count != 1: raise RuntimeError(f"copy anchor mismatch: {heading}")
    target.write_text(target_text, encoding="utf-8")


def missing_learning_map_row(root: Path) -> None:
    path = root / "README.md"
    lines = path.read_text(encoding="utf-8").splitlines()
    selected = []
    for line in lines:
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) == 7 and "](docs/03-remote-pr-workflow.md)" in cells[1]:
            selected.append(line)
    if len(selected) != 1:
        raise RuntimeError("root learning-map row mismatch")
    path.write_text("\n".join(line for line in lines if line != selected[0]) + "\n", encoding="utf-8")


def missing_learning_map_field(root: Path) -> None:
    path = root / "README.md"
    text = path.read_text(encoding="utf-8")
    changed, count = re.subn(r"(\| 순서 \| 문서 \| 관찰 예제 \| 직접 수행 \| )수정 위치( \| 검증 \|)",
                             r"\1변경 대상\2", text, count=1)
    if count != 1:
        raise RuntimeError("root learning-map header mismatch")
    path.write_text(changed, encoding="utf-8")


def reordered_learning_map(root: Path) -> None:
    path = root / "README.md"
    lines = path.read_text(encoding="utf-8").splitlines()
    indexes: list[int] = []
    for index, line in enumerate(lines):
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) == 7 and cells[0] in {"1", "2"}:
            indexes.append(index)
    if len(indexes) != 2:
        raise RuntimeError("root learning-map order mismatch")
    lines[indexes[0]], lines[indexes[1]] = lines[indexes[1]], lines[indexes[0]]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def empty_learning_map_verification(root: Path) -> None:
    path = root / "README.md"
    lines = path.read_text(encoding="utf-8").splitlines()
    changed = 0
    for index, line in enumerate(lines):
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) == 7 and cells[0] == "2":
            cells[5] = ""
            lines[index] = "| " + " | ".join(cells) + " |"
            changed += 1
    if changed != 1:
        raise RuntimeError("root learning-map verification mismatch")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def wrong_connected_exercise(root: Path) -> None:
    path = root / "docs/01-workspace-basics.md"
    text = path.read_text(encoding="utf-8")
    old = "../exercises/README.md#1단계-작업-공간과-브랜치"
    new = "../README.md#학습-순서와-실습-지도"
    if text.count(old) != 1:
        raise RuntimeError("connected exercise link mismatch")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def wrong_connected_fragment(root: Path) -> None:
    path = root / "docs/01-workspace-basics.md"
    text = path.read_text(encoding="utf-8")
    old = "../exercises/README.md#1단계-작업-공간과-브랜치"
    new = "../exercises/README.md#2단계-변경-검토와-커밋"
    if text.count(old) != 1:
        raise RuntimeError("connected exercise fragment mismatch")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def missing_expected_evidence(root: Path) -> None:
    path = root / "exercises/README.md"
    text = path.read_text(encoding="utf-8")
    if text.count("**기대 증거:**") < 1:
        raise RuntimeError("expected-evidence field missing")
    path.write_text(text.replace("**기대 증거:**", "**관찰 결과:**", 1), encoding="utf-8")


def meaningless_expected_evidence(root: Path) -> None:
    path = root / "exercises/README.md"
    text = path.read_text(encoding="utf-8")
    match = re.search(r"(^### 1단계 작업 공간과 브랜치\n)(.*?)(?=^### |^## |\Z)", text, re.M | re.S)
    if not match:
        raise RuntimeError("stage-one evidence section mismatch")
    body_text, count = re.subn(r"^- \*\*기대 증거:\*\*.*$",
                               "- **기대 증거:** 완료 상태입니다.", match.group(2), count=1, flags=re.M)
    if count != 1:
        raise RuntimeError("stage-one evidence field mismatch")
    path.write_text(text[:match.start(2)] + body_text + text[match.end(2):], encoding="utf-8")


def missing_recovery_contract(root: Path) -> None:
    path = root / "exercises/README.md"
    text = path.read_text(encoding="utf-8")
    if "`recovery/*`" not in text:
        raise RuntimeError("recovery evidence mismatch")
    path.write_text(text.replace("recovery/*", "recovery/name"), encoding="utf-8")


def missing_recovery_walkthrough(root: Path) -> None:
    path = root / "exercises/README.md"
    text = path.read_text(encoding="utf-8")
    old = 'git -C "$RECOVERY_LAB" switch --detach main'
    new = 'git -C "$RECOVERY_LAB" switch main'
    if text.count(old) != 1:
        raise RuntimeError("recovery walkthrough mismatch")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def forbidden_implementation_marker(root: Path) -> None:
    path = root / "exercises/setup.sh"
    marker = "# [" + "Implementation 1]\n"
    path.write_text(path.read_text(encoding="utf-8") + marker, encoding="utf-8")


def malformed_implementation_marker(root: Path) -> None:
    path = root / "exercises/setup.sh"
    marker = "# [" + "Implementation 01]\n"
    path.write_text(path.read_text(encoding="utf-8") + marker, encoding="utf-8")


def missing_roadmap_limit(root: Path) -> None:
    path = root / "docs/00-roadmap.md"
    text = path.read_text(encoding="utf-8")
    path.write_text(text.replace("## 자동화의 한계\n", "## 자동화 한계 누락\n", 1), encoding="utf-8")


MUTANTS = (
    Mutant("arbitrary root file outside exact manifest", arbitrary_root),
    Mutant("unexpected numbered document", extra_doc),
    Mutant("missing learning goals", missing_goal),
    Mutant("missing prerequisites", missing_prerequisite),
    Mutant("missing connected exercise", missing_connection),
    Mutant("missing completion criteria", missing_completion),
    Mutant("wrong pedagogy heading order", wrong_order),
    Mutant("fewer than three completion criteria", short_completion),
    Mutant("missing executable mode", remove_mode),
    Mutant("source symlink", add_symlink),
    Mutant("source directory symlink", add_directory_symlink),
    Mutant("broken Markdown anchor", broken_anchor),
    Mutant("copied pedagogy rubric", copied_rubric),
    Mutant("missing root learning-map row", missing_learning_map_row),
    Mutant("missing root learning-map field", missing_learning_map_field),
    Mutant("reordered root learning-map rows", reordered_learning_map),
    Mutant("empty root learning-map verification", empty_learning_map_verification),
    Mutant("valid but wrong connected exercise", wrong_connected_exercise),
    Mutant("valid but wrong connected exercise fragment", wrong_connected_fragment),
    Mutant("missing expected-evidence field", missing_expected_evidence),
    Mutant("meaningless expected-evidence field", meaningless_expected_evidence),
    Mutant("missing recovery evidence contract", missing_recovery_contract),
    Mutant("missing recovery sandbox walkthrough", missing_recovery_walkthrough),
    Mutant("forbidden implementation marker", forbidden_implementation_marker),
    Mutant("malformed implementation marker", malformed_implementation_marker),
    Mutant("missing roadmap automation limit", missing_roadmap_limit),
)


def copy_source(destination: Path) -> None:
    shutil.copytree(ROOT, destination, symlinks=True,
        ignore=shutil.ignore_patterns(".git", ".guide", ".venv", ".pytest_cache",
                                      "__pycache__", "workspace", "*.pyc", "*.pyo", "*.log"))


def run_validator(root: Path) -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy(); environment["GUIDE_ROOT"] = str(root); environment["PYTHONDONTWRITEBYTECODE"] = "1"
    return subprocess.run([sys.executable, "-B", str(root / "scripts/validate.py")], cwd=root,
                          env=environment, text=True, capture_output=True, timeout=30, check=False)


def state_fingerprint(root: Path) -> str:
    environment = os.environ.copy()
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    result = subprocess.run(
        [sys.executable, "-B", str(root / "scripts/repository_state.py"),
         "fingerprint", "--root", str(root)],
        cwd=root, env=environment, text=True, capture_output=True,
        timeout=30, check=True,
    )
    return result.stdout.strip()


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="guide-validator-") as directory:
        baseline = Path(directory) / "baseline"; copy_source(baseline)
        result = run_validator(baseline)
        if result.returncode:
            print("FAIL validator baseline", file=sys.stderr); print(result.stdout + result.stderr, file=sys.stderr); return 1
        for index, mutant in enumerate(MUTANTS, 1):
            target = Path(directory) / f"mutant-{index}"; shutil.copytree(baseline, target, symlinks=True)
            before_fingerprint = state_fingerprint(target)
            mutant.apply(target)
            if mutant.name == "source directory symlink" and state_fingerprint(target) == before_fingerprint:
                print("FAIL directory symlink missing from source fingerprint", file=sys.stderr); return 1
            result = run_validator(target)
            if result.returncode == 0:
                print(f"FAIL mutant survived: {mutant.name}", file=sys.stderr); return 1
            print(f"PASS mutant rejected: {mutant.name}")
    print(f"VALIDATOR MUTANTS: PASS ({len(MUTANTS)})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
