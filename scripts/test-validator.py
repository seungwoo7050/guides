#!/usr/bin/env python3
"""Mutation-test the exact-tree and pedagogical validator in disposable copies."""

from __future__ import annotations

from collections.abc import Callable
from functools import partial
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
DOC_HEADINGS = ("학습 목표", "핵심 모델", "연결 실습", "완료 기준", "실패 조건", "자기 설명")
ROADMAP_FIELDS = (
    "## 대상 독자와 선행지식",
    "## 이 가이드가 소유하는 범위",
    "## 권장 읽기 순서",
    "## 목적별 짧은 경로",
    "## 실습의 두 종류",
    "## 완료 기준",
    "## 지원 환경과 비보장 범위",
)


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
            "build",
            "build-sanitize",
            "workspace",
            ".checker-mutant.*",
            ".workspace-copy.*",
            ".workspace-create.lock*",
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
        timeout=30,
        check=False,
    )


def replace_once(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    if text.count(old) != 1:
        raise AssertionError(f"mutant 대상이 정확히 하나가 아닙니다: {path}: {old!r}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def add_unexpected(root: Path) -> None:
    (root / "unexpected.txt").write_text("mutant\n", encoding="utf-8")


def delete_roadmap(root: Path) -> None:
    (root / "docs/00-roadmap.md").unlink()


def remove_core_heading(root: Path) -> None:
    path = root / "docs/01-boundary-and-execution/01-kernel-boundary-and-events.md"
    replace_once(path, "## 실패 조건", "## 실패 조건 누락")


def break_link(root: Path) -> None:
    path = root / "README.md"
    replace_once(path, "docs/00-roadmap.md", "docs/missing-roadmap.md")


def poison_reference(root: Path) -> None:
    path = root / "exercises/kernel-model/reference/kernel_model/lifecycle.py"
    path.write_text(path.read_text(encoding="utf-8") + "\n# TODO mutant\n", encoding="utf-8")


def add_symlink(root: Path) -> None:
    os.symlink("README.md", root / "README-link.md")


def add_directory_symlink(root: Path) -> None:
    os.symlink("docs", root / "docs-link")


def damage_directory_mode(root: Path) -> None:
    (root / "docs/01-boundary-and-execution").chmod(0o700)


def section_body(text: str, heading: str) -> str:
    start = text.index(f"## {heading}\n") + len(f"## {heading}\n")
    end = text.find("\n## ", start)
    return text[start:] if end < 0 else text[start:end]


def copy_sections(source: Path, target: Path, mappings: tuple[tuple[str, str], ...]) -> None:
    source_text = source.read_text(encoding="utf-8")
    target_text = target.read_text(encoding="utf-8")
    for source_heading, target_heading in mappings:
        old = section_body(target_text, target_heading)
        new = section_body(source_text, source_heading)
        if target_text.count(old) != 1:
            raise AssertionError(f"section mutant 대상이 정확히 하나가 아닙니다: {target}: {target_heading}")
        target_text = target_text.replace(old, new, 1)
    target.write_text(target_text, encoding="utf-8")


def duplicate_completion(root: Path) -> None:
    source = root / "docs/01-boundary-and-execution/01-kernel-boundary-and-events.md"
    target = root / "docs/01-boundary-and-execution/02-processes-threads-and-context-switches.md"
    copy_sections(source, target, (("완료 기준", "완료 기준"),))


def duplicate_full_concept_rubric(root: Path) -> None:
    source = root / "docs/01-boundary-and-execution/01-kernel-boundary-and-events.md"
    target = root / "docs/01-boundary-and-execution/02-processes-threads-and-context-switches.md"
    copy_sections(source, target, tuple((heading, heading) for heading in DOC_HEADINGS))


def duplicate_full_exercise_rubric(root: Path) -> None:
    source = root / "examples/README.md"
    target = root / "exercises/kernel-model/README.md"
    copy_sections(
        source,
        target,
        (
            ("학습 목표", "목표"),
            ("완료 기준", "완료 기준"),
            ("자기 설명", "자기 설명"),
            ("검증", "검증"),
        ),
    )


def remove_roadmap_field(root: Path, field: str) -> None:
    path = root / "docs/00-roadmap.md"
    replace_once(path, field, "## 로드맵 개별 필드 mutant")


def delete_fixture_expected(root: Path) -> None:
    path = root / "exercises/kernel-model/fixtures/lifecycle.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    del data["expected"]
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def damage_checkpoint_contract(root: Path) -> None:
    path = root / "exercises/kernel-model/check.py"
    replace_once(path, '    "08-cli",\n', '    "08-cli-mutant",\n')


def remove_executable_mode(root: Path) -> None:
    (root / "scripts/test-checker.py").chmod(0o644)


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="guide-os-validator-baseline-") as temporary:
        root = copy_source(Path(temporary))
        baseline = validate(root)
        if baseline.returncode != 0:
            raise AssertionError(f"baseline validator 실패\n{baseline.stdout}\n{baseline.stderr}")

    mutants: list[tuple[str, Callable[[Path], None], str]] = [
        ("unexpected exact-tree file", add_unexpected, "exact-tree 예상 밖 파일"),
        ("missing roadmap", delete_roadmap, "exact-tree 필수 파일 없음"),
        ("missing core pedagogy heading", remove_core_heading, "본문 학습 heading 누락/중복"),
        ("broken internal link", break_link, "깨진 링크"),
        ("incomplete reference", poison_reference, "reference에 미완성 표식"),
        ("source symlink", add_symlink, "source tree symlink 금지"),
        ("source directory symlink", add_directory_symlink, "source tree symlink 금지"),
        ("source directory mode", damage_directory_mode, "source directory mode는 0755"),
        ("copied completion rubric", duplicate_completion, "복사형 완료 기준"),
        ("copied complete concept rubric", duplicate_full_concept_rubric, "복사형 본문 전체 rubric"),
        ("copied complete exercise rubric", duplicate_full_exercise_rubric, "복사형 exercise 전체 rubric"),
        ("missing fixture expected", delete_fixture_expected, "expected object 누락/비어 있음"),
        ("damaged checkpoint list", damage_checkpoint_contract, "CHECKPOINTS exact 계약 오류"),
        ("missing executable mode", remove_executable_mode, "실행 mode/shebang 오류"),
    ]
    mutants.extend(
        (
            f"missing roadmap field: {field}",
            partial(remove_roadmap_field, field=field),
            "roadmap 학습 계약 누락",
        )
        for field in ROADMAP_FIELDS
    )
    for label, mutate, expected in mutants:
        with tempfile.TemporaryDirectory(prefix="guide-os-validator-mutant-") as temporary:
            root = copy_source(Path(temporary))
            mutate(root)
            result = validate(root)
            output = result.stdout + result.stderr
            if result.returncode == 0 or expected not in output:
                raise AssertionError(
                    f"mutant를 의도한 이유로 거부하지 않았습니다: {label}\n"
                    f"expected={expected!r}\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}"
                )
    print(
        f"[PASS] validator mutation suite: baseline 1개 + mutant {len(mutants)}개 "
        f"(roadmap fields={len(ROADMAP_FIELDS)}, full-rubric=2)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
