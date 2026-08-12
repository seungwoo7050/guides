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


def implementation_marker(value: str) -> str:
    """Build a marker without making this validator test an annotation owner."""
    return "[" + f"Implementation {value}]"


def remove_line_containing(path: Path, needle: str) -> None:
    lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
    matches = [index for index, line in enumerate(lines) if needle in line]
    if len(matches) != 1:
        raise AssertionError(f"line mutant 대상이 정확히 하나가 아닙니다: {path}: {needle!r}")
    del lines[matches[0]]
    path.write_text("".join(lines), encoding="utf-8")


def add_unexpected(root: Path) -> None:
    (root / "unexpected.txt").write_text("mutant\n", encoding="utf-8")


def delete_roadmap(root: Path) -> None:
    (root / "docs/00-roadmap.md").unlink()


def remove_core_heading(root: Path) -> None:
    path = root / "docs/01-boundary-and-execution/01-kernel-boundary-and-events.md"
    replace_once(path, "## 실패 조건", "## 실패 조건 누락")


def break_link(root: Path) -> None:
    path = root / "README.md"
    replace_once(
        path,
        "[운영체제 원리 학습 경로](docs/00-roadmap.md)",
        "[운영체제 원리 학습 경로](docs/missing-roadmap.md)",
    )


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


def remove_learning_map_row(root: Path) -> None:
    remove_line_containing(root / "README.md", "CHECKPOINT=04-deadlock")


def use_reference_in_learning_map(root: Path) -> None:
    path = root / "README.md"
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines(keepends=True)
    matching = [index for index, line in enumerate(lines) if "CHECKPOINT=05-paging" in line]
    if len(matching) != 1 or lines[matching[0]].count("IMPL=workspace") != 1:
        raise AssertionError("README mapping의 paging workspace command를 찾을 수 없습니다")
    lines[matching[0]] = lines[matching[0]].replace("IMPL=workspace", "IMPL=reference", 1)
    path.write_text("".join(lines), encoding="utf-8")


def swap_learning_map_docs(root: Path) -> None:
    path = root / "README.md"
    first = "docs/01-boundary-and-execution/03-cpu-scheduling.md"
    second = "docs/04-storage-and-io/02-device-io-interrupts-and-dma.md"
    text = path.read_text(encoding="utf-8")
    if text.count(first) != 1 or text.count(second) != 1:
        raise AssertionError("README mapping doc swap 대상이 정확하지 않습니다")
    sentinel = "docs/mapping-swap-sentinel.md"
    text = text.replace(first, sentinel, 1).replace(second, first, 1).replace(sentinel, second, 1)
    path.write_text(text, encoding="utf-8")


def shorten_reference_path_in_learning_map(root: Path) -> None:
    path = root / "README.md"
    replace_once(
        path,
        "exercises/kernel-model/reference/kernel_model/scheduler.py",
        "reference/kernel_model/scheduler.py",
    )


def duplicate_workspace_command(root: Path) -> None:
    path = root / "README.md"
    command = "./scripts/new-workspace.sh exercises/kernel-model"
    path.write_text(path.read_text(encoding="utf-8") + f"\n```sh\n{command}\n```\n", encoding="utf-8")


def duplicate_implementation_anchor(root: Path) -> None:
    path = root / "exercises/kernel-model/reference/kernel_model/lifecycle.py"
    marker = implementation_marker("1")
    path.write_text(path.read_text(encoding="utf-8") + f"\n# {marker} duplicate mutant\n", encoding="utf-8")


def gap_implementation_anchor(root: Path) -> None:
    path = root / "exercises/kernel-model/reference/kernel_model/deadlock.py"
    replace_once(path, implementation_marker("4"), implementation_marker("10"))


def annotate_skeleton(root: Path) -> None:
    path = root / "exercises/kernel-model/skeleton/kernel_model/lifecycle.py"
    marker = implementation_marker("1")
    path.write_text(path.read_text(encoding="utf-8") + f"\n# {marker} forbidden mutant\n", encoding="utf-8")


def remove_reference_index_row(root: Path) -> None:
    remove_line_containing(root / "exercises/kernel-model/reference/README.md", "| 4-1 |")


def duplicate_reference_index_row(root: Path) -> None:
    path = root / "exercises/kernel-model/reference/README.md"
    text = path.read_text(encoding="utf-8")
    line = next(line for line in text.splitlines(keepends=True) if "| 4-1 |" in line)
    replace_once(path, line, line + line)


def reorder_reference_index_rows(root: Path) -> None:
    path = root / "exercises/kernel-model/reference/README.md"
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines(keepends=True)
    first = next(index for index, line in enumerate(lines) if "| 4-1 |" in line)
    second = next(index for index, line in enumerate(lines) if "| 4-2 |" in line)
    lines[first], lines[second] = lines[second], lines[first]
    path.write_text("".join(lines), encoding="utf-8")


def move_implementation_anchor_owner(root: Path) -> None:
    source = root / "exercises/kernel-model/reference/kernel_model/deadlock.py"
    target = root / "exercises/kernel-model/reference/kernel_model/journal.py"
    marker = implementation_marker("4-1")
    lines = source.read_text(encoding="utf-8").splitlines(keepends=True)
    matches = [index for index, line in enumerate(lines) if marker in line]
    if len(matches) != 1:
        raise AssertionError("owner mutant source marker를 찾을 수 없습니다")
    moved = lines.pop(matches[0])
    source.write_text("".join(lines), encoding="utf-8")
    target.write_text(target.read_text(encoding="utf-8") + "\n" + moved, encoding="utf-8")


def reorder_source_methods_without_changing_construction_order(root: Path) -> None:
    """Move two independent methods while keeping their recommended numbering."""
    path = root / "exercises/kernel-model/reference/kernel_model/journal.py"
    text = path.read_text(encoding="utf-8")
    recover_start = text.index("    # " + implementation_marker("7-3"))
    validate_start = text.index("    # " + implementation_marker("7-4"))
    snapshot_start = text.index("    def snapshot", validate_start)
    recover_block = text[recover_start:validate_start]
    validate_block = text[validate_start:snapshot_start]
    path.write_text(
        text[:recover_start] + validate_block + recover_block + text[snapshot_start:],
        encoding="utf-8",
    )


def remove_example_index_row(root: Path) -> None:
    remove_line_containing(root / "examples/README.md", "|  | 3 | page touch loop")


def use_reference_default(root: Path) -> None:
    replace_once(root / "Makefile", "IMPL ?= workspace", "IMPL ?= reference")


def remove_page_volatile(root: Path) -> None:
    path = root / "examples/page-fault-observer.c"
    replace_once(path, "volatile unsigned char *memory_view;", "unsigned char *memory_view;")


def remove_optional_evidence_contract(root: Path) -> None:
    path = root / "docs/80-extended-labs.md"
    text = path.read_text(encoding="utf-8")
    if "expected evidence" not in text:
        raise AssertionError("optional evidence mutant 대상을 찾을 수 없습니다")
    path.write_text(text.replace("expected evidence", "review artifact"), encoding="utf-8")


def run_reference_from_core_doc(root: Path) -> None:
    path = root / "docs/02-concurrency/02-synchronization-primitives.md"
    path.write_text(
        path.read_text(encoding="utf-8")
        + "\n```sh\nmake -C exercises/kernel-model reference-test\n```\n",
        encoding="utf-8",
    )


def run_impl_reference_from_core_doc(root: Path) -> None:
    path = root / "docs/02-concurrency/02-synchronization-primitives.md"
    path.write_text(
        path.read_text(encoding="utf-8")
        + "\n```sh\nmake checkpoint-check IMPL=reference CHECKPOINT=02-synchronization\n```\n",
        encoding="utf-8",
    )


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="guide-os-validator-baseline-") as temporary:
        root = copy_source(Path(temporary))
        baseline = validate(root)
        if baseline.returncode != 0:
            raise AssertionError(f"baseline validator 실패\n{baseline.stdout}\n{baseline.stderr}")

    with tempfile.TemporaryDirectory(prefix="guide-os-validator-accepted-order-") as temporary:
        root = copy_source(Path(temporary))
        reorder_source_methods_without_changing_construction_order(root)
        accepted = validate(root)
        if accepted.returncode != 0:
            raise AssertionError(
                "source 물리 순서를 construction order로 오인했습니다\n"
                f"{accepted.stdout}\n{accepted.stderr}"
            )

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
        ("missing README learning-map row", remove_learning_map_row, "README ordered mapping 순서 오류"),
        (
            "README learning-map validates reference",
            use_reference_in_learning_map,
            "README ordered mapping workspace 검증 명령 오류",
        ),
        (
            "README learning-map swaps concept docs",
            swap_learning_map_docs,
            "README ordered mapping 문서/checkpoint 대응 오류",
        ),
        (
            "README learning-map shortens reference path",
            shorten_reference_path_in_learning_map,
            "README ordered mapping reference/next 대응 오류",
        ),
        (
            "README repeats non-overwriting workspace command",
            duplicate_workspace_command,
            "README workspace 생성 명령은 전체 학습 순서에서 정확히 한 번",
        ),
        (
            "duplicate implementation anchor",
            duplicate_implementation_anchor,
            "Implementation exact anchor 중복",
        ),
        (
            "gapped implementation anchors",
            gap_implementation_anchor,
            "Implementation top-level 번호가 1부터 연속",
        ),
        ("implementation anchor in skeleton", annotate_skeleton, "Implementation annotation 금지 경로"),
        (
            "missing reference implementation index row",
            remove_reference_index_row,
            "reference Implementation index/source 불일치",
        ),
        (
            "duplicate reference implementation index row",
            duplicate_reference_index_row,
            "reference Implementation index 순서/중복 오류",
        ),
        (
            "reordered reference implementation index rows",
            reorder_reference_index_rows,
            "reference Implementation index 순서/중복 오류",
        ),
        (
            "implementation anchor moves owner module",
            move_implementation_anchor_owner,
            "reference Implementation index/source owner 불일치",
        ),
        (
            "missing example implementation index row",
            remove_example_index_row,
            "examples Implementation index/source 불일치",
        ),
        (
            "root checkpoint defaults to reference",
            use_reference_default,
            "root checkpoint-check의 learner 기본 구현",
        ),
        ("page touch loses volatile access", remove_page_volatile, "최적화 방지 volatile"),
        (
            "optional lab loses expected-evidence contract",
            remove_optional_evidence_contract,
            "선택 확장 manual evidence 계약 누락",
        ),
        (
            "core doc runs reference first",
            run_reference_from_core_doc,
            "핵심 문서가 learner checkpoint 전에 reference 실행",
        ),
        (
            "core doc selects reference implementation",
            run_impl_reference_from_core_doc,
            "핵심 문서가 learner checkpoint 전에 reference 실행",
        ),
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
        f"[PASS] validator mutation suite: baseline 1개 + source-order-independent acceptance 1개 "
        f"+ mutant {len(mutants)}개 "
        f"(roadmap fields={len(ROADMAP_FIELDS)}, full-rubric=2)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
