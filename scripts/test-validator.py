#!/usr/bin/env python3
"""Prove that the validator rejects independent layout and pedagogy defects."""

from __future__ import annotations

import json
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
    expected_fragment: str | None = None


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


def unfinished_reference(root: Path) -> None:
    candidates = [path for path in root.rglob("*") if path.is_file() and "reference" in path.parts
                  and path.suffix.lower() in {".py", ".md", ".json", ".sh"}]
    if not candidates: raise RuntimeError("reference file missing")
    path = sorted(candidates)[0]
    if path.suffix.lower() == ".json":
        data = json.loads(path.read_text(encoding="utf-8")); data["_unfinished"] = "TODO"
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    else:
        path.write_text(path.read_text(encoding="utf-8") + "\nTODO\n", encoding="utf-8")


def missing_roadmap_limit(root: Path) -> None:
    path = root / "docs/00-roadmap.md"
    text = path.read_text(encoding="utf-8")
    path.write_text(text.replace("## 자동화의 한계\n", "## 자동화 한계 누락\n", 1), encoding="utf-8")


def duplicate_implementation_annotation(root: Path) -> None:
    path = root / "exercises/command-checker/reference/command_checker/model.py"
    text = path.read_text(encoding="utf-8")
    marker = next(line for line in text.splitlines() if "[Implementation 2]" in line)
    path.write_text(text + "\n" + marker + "\n", encoding="utf-8")


def gap_in_implementation_annotations(root: Path) -> None:
    path = root / "exercises/command-checker/reference/command_checker/runner.py"
    text = path.read_text(encoding="utf-8")
    if text.count("[Implementation 9]") != 1:
        raise RuntimeError("implementation 9 anchor mismatch")
    path.write_text(text.replace("[Implementation 9]", "[Implementation 11]", 1), encoding="utf-8")


def implementation_annotation_in_skeleton(root: Path) -> None:
    path = root / "exercises/command-checker/skeleton/command_checker/cli.py"
    path.write_text(
        path.read_text(encoding="utf-8")
        + "\n# [Implementation 11] skeleton에 정답 순서를 노출한 결함입니다.\n",
        encoding="utf-8",
    )


def drift_reference_implementation_index(root: Path) -> None:
    path = root / "exercises/command-checker/README.md"
    text = path.read_text(encoding="utf-8")
    if text.count("| `1` |") != 1:
        raise RuntimeError("reference implementation index anchor mismatch")
    path.write_text(text.replace("| `1` |", "| `99` |", 1), encoding="utf-8")


def remove_py_typed_sidecar(root: Path) -> None:
    path = root / "exercises/command-checker/README.md"
    text = path.read_text(encoding="utf-8")
    if text.count("[Implementation 10-6]") != 1:
        raise RuntimeError("py.typed sidecar anchor mismatch")
    path.write_text(text.replace("[Implementation 10-6] ", "", 1), encoding="utf-8")


def add_implementation_zero(root: Path) -> None:
    path = root / "exercises/command-checker/reference/command_checker/model.py"
    path.write_text(
        path.read_text(encoding="utf-8")
        + "\n# [Implementation 0] 존재하지 않는 bootstrap을 만든 결함입니다.\n",
        encoding="utf-8",
    )


def malformed_implementation_annotation(root: Path) -> None:
    path = root / "exercises/command-checker/reference/command_checker/model.py"
    path.write_text(
        path.read_text(encoding="utf-8")
        + "\n# [Implementation x] 숫자가 아닌 단계 결함입니다.\n",
        encoding="utf-8",
    )


def reference_as_default_implementation(root: Path) -> None:
    path = root / "Makefile"
    text = path.read_text(encoding="utf-8")
    if text.count("EXERCISE_IMPL ?= workspace") != 1:
        raise RuntimeError("Makefile learner default anchor mismatch")
    path.write_text(
        text.replace("EXERCISE_IMPL ?= workspace", "EXERCISE_IMPL ?= reference", 1),
        encoding="utf-8",
    )


def missing_readme_stage_mapping(root: Path) -> None:
    path = root / "README.md"
    text = path.read_text(encoding="utf-8")
    anchor = "make stage-04 EXERCISE_IMPL=workspace"
    if text.count(anchor) != 1:
        raise RuntimeError("README stage-04 mapping anchor mismatch")
    path.write_text(text.replace(anchor, "make stage-XX EXERCISE_IMPL=workspace", 1), encoding="utf-8")


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
    Mutant("unfinished reference", unfinished_reference),
    Mutant("missing roadmap automation limit", missing_roadmap_limit),
    Mutant(
        "duplicate implementation annotation",
        duplicate_implementation_annotation,
        "Implementation annotation 중복",
    ),
    Mutant(
        "gap in implementation annotations",
        gap_in_implementation_annotations,
        "Implementation top-level 번호는 1부터 연속",
    ),
    Mutant(
        "implementation annotation leaked into skeleton",
        implementation_annotation_in_skeleton,
        "Implementation annotation 금지 경로",
    ),
    Mutant(
        "reference implementation index drift",
        drift_reference_implementation_index,
        "Reference 구현 순서 표와 annotation 불일치",
    ),
    Mutant(
        "missing py.typed sidecar annotation",
        remove_py_typed_sidecar,
        "py.typed sidecar annotation",
    ),
    Mutant(
        "invented implementation zero",
        add_implementation_zero,
        "Implementation 0 대상이 없습니다",
    ),
    Mutant(
        "malformed implementation annotation",
        malformed_implementation_annotation,
        "Implementation annotation 형식 오류",
    ),
    Mutant(
        "reference selected as learner default",
        reference_as_default_implementation,
        "Makefile의 EXERCISE_IMPL 기본값은 workspace",
    ),
    Mutant(
        "missing README stage mapping",
        missing_readme_stage_mapping,
        "README 학습 순서에서 stage 명령 누락",
    ),
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
            combined = result.stdout + result.stderr
            if mutant.expected_fragment and mutant.expected_fragment not in combined:
                print(f"FAIL mutant rejected for wrong reason: {mutant.name}", file=sys.stderr)
                print(combined, file=sys.stderr)
                return 1
            print(f"PASS mutant rejected: {mutant.name}")
    print(f"VALIDATOR MUTANTS: PASS ({len(MUTANTS)})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
