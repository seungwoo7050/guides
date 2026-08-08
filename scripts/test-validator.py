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
