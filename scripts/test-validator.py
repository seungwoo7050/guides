#!/usr/bin/env python3
"""Mutation-test the exact-tree and pedagogical validator in disposable copies."""

from __future__ import annotations

from collections.abc import Callable
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def copy_source(destination: Path) -> Path:
    target = destination / "repository"
    shutil.copytree(
        ROOT,
        target,
        ignore=shutil.ignore_patterns(
            ".git",
            ".guide",
            ".pytest_cache",
            ".venv",
            "__pycache__",
            "workspace",
            "*.pyc",
            "*.pyo",
        ),
    )
    return target


def validate(root: Path) -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy()
    environment["GUIDE_ROOT"] = str(root)
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    return subprocess.run(
        [sys.executable, str(root / "scripts/validate.py")],
        cwd=root,
        env=environment,
        text=True,
        capture_output=True,
        timeout=20,
        check=False,
    )


def replace_once(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    if text.count(old) != 1:
        raise AssertionError(f"mutant 대상이 정확히 하나가 아닙니다: {path}: {old!r}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def add_unexpected(root: Path) -> None:
    (root / "unexpected.txt").write_text("mutant\n", encoding="utf-8")


def delete_required(root: Path) -> None:
    (root / "docs/00-roadmap.md").unlink()


def remove_explanation(root: Path) -> None:
    path = root / "exercises/02-data-structures/README.md"
    replace_once(path, "## 자기 설명", "## 설명 초안")


def remove_prerequisite(root: Path) -> None:
    path = root / "docs/01-foundations/02-asymptotic-analysis.md"
    replace_once(path, "## 선행 개념", "## 선행 개념 누락")


def remove_roadmap_limit(root: Path) -> None:
    path = root / "docs/00-roadmap.md"
    replace_once(path, "## 자동 검증의 한계", "## 자동 검사 참고")


def break_link(root: Path) -> None:
    path = root / "README.md"
    replace_once(path, "docs/00-roadmap.md", "docs/missing-roadmap.md")


def poison_reference(root: Path) -> None:
    path = root / "exercises/07-verified-algorithms-capstone/reference/algorithms.py"
    path.write_text(path.read_text(encoding="utf-8") + "\n# TODO mutant\n", encoding="utf-8")


def add_symlink(root: Path) -> None:
    os.symlink("README.md", root / "README-link.md")


def add_directory_symlink(root: Path) -> None:
    os.symlink("docs", root / "docs-link")


def duplicate_rubric(root: Path) -> None:
    source = root / "exercises/02-data-structures/README.md"
    target = root / "exercises/03-design-techniques/README.md"
    source_text = source.read_text(encoding="utf-8")
    target_text = target.read_text(encoding="utf-8")

    def section(text: str, heading: str) -> str:
        start = text.index(f"## {heading}\n") + len(f"## {heading}\n")
        end = text.find("\n## ", start)
        return text[start:] if end < 0 else text[start:end]

    original = section(target_text, "완료 기준")
    duplicated = section(source_text, "완료 기준")
    target.write_text(target_text.replace(original, duplicated, 1), encoding="utf-8")


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="guide-algorithms-validator-baseline-") as temporary:
        root = copy_source(Path(temporary))
        baseline = validate(root)
        if baseline.returncode != 0:
            raise AssertionError(f"baseline validator 실패\n{baseline.stdout}\n{baseline.stderr}")

    mutants: tuple[tuple[str, Callable[[Path], None], str], ...] = (
        ("unexpected exact-tree file", add_unexpected, "exact-tree 예상 밖 파일"),
        ("missing required roadmap", delete_required, "exact-tree 필수 파일 없음"),
        ("missing exercise explanation", remove_explanation, "heading 누락/중복"),
        ("missing concept prerequisite", remove_prerequisite, "heading 누락/중복"),
        ("missing roadmap limit", remove_roadmap_limit, "roadmap 학습 계약 누락"),
        ("broken internal link", break_link, "깨진 링크"),
        ("incomplete reference", poison_reference, "reference에 미완성 표식"),
        ("source symlink", add_symlink, "source tree symlink 금지"),
        ("source directory symlink", add_directory_symlink, "source tree symlink 금지"),
        ("copied completion rubric", duplicate_rubric, "복사형 완료 기준"),
    )
    for label, mutate, expected in mutants:
        with tempfile.TemporaryDirectory(prefix="guide-algorithms-validator-mutant-") as temporary:
            root = copy_source(Path(temporary))
            mutate(root)
            result = validate(root)
            output = result.stdout + result.stderr
            if result.returncode == 0 or expected not in output:
                raise AssertionError(
                    f"mutant를 의도한 이유로 거부하지 않았습니다: {label}\n"
                    f"expected={expected!r}\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}"
                )
    print(f"[PASS] validator mutation suite: baseline 1개 + mutant {len(mutants)}개")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
