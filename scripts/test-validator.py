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

    def role_aware_ignore(directory: str, names: list[str]) -> set[str]:
        relative = Path(directory).resolve().relative_to(ROOT)
        ignored = {
            name
            for name in names
            if name in {"__pycache__"} or name.endswith((".pyc", ".pyo"))
        }
        if relative == Path("."):
            ignored.update({".git", ".guide"})
        if relative == Path("exercises/07-verified-algorithms-capstone"):
            ignored.add("workspace")
        return ignored

    shutil.copytree(
        ROOT,
        target,
        ignore=role_aware_ignore,
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


def implementation_marker(identifier: str) -> str:
    return "[" + "Implementation " + identifier + "]"


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
    replace_once(
        path,
        "2. [학습 로드맵](docs/00-roadmap.md)을 읽는다.",
        "2. [학습 로드맵](docs/missing-roadmap.md)을 읽는다.",
    )


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


def remove_readme_mapping(root: Path) -> None:
    path = root / "README.md"
    replace_once(path, "## 단계별 학습 지도", "## 단계별 학습 지도 누락")


def remove_mapping_column(root: Path) -> None:
    path = root / "README.md"
    replace_once(
        path,
        "| 순서 | 문서 | 관찰 예제 | 직접 수행 | 수정 위치 | 검증 | 완료 뒤 비교·다음 |",
        "| 순서 | 문서 | 관찰 예제 | 직접 수행 | 검증 | 완료 뒤 비교·다음 |",
    )


def remove_mapping_doc(root: Path) -> None:
    path = root / "README.md"
    replace_once(
        path,
        "docs/03-design-techniques/02-greedy-methods.md",
        "docs/03-design-techniques/missing-greedy.md",
    )


def remove_implementation_anchor(root: Path) -> None:
    path = root / "exercises/07-verified-algorithms-capstone/reference/algorithms.py"
    replace_once(path, implementation_marker("4"), "[Construction 4]")


def add_malformed_implementation_anchor(root: Path) -> None:
    path = root / "exercises/07-verified-algorithms-capstone/reference/algorithms.py"
    path.write_text(
        path.read_text(encoding="utf-8")
        + "\n# "
        + "["
        + "Implementation 13 malformed mutant\n",
        encoding="utf-8",
    )


def duplicate_implementation_anchor(root: Path) -> None:
    path = root / "exercises/07-verified-algorithms-capstone/reference/algorithms.py"
    path.write_text(
        path.read_text(encoding="utf-8")
        + "\n# "
        + implementation_marker("1")
        + " duplicate mutant\n",
        encoding="utf-8",
    )


def add_skeleton_implementation_anchor(root: Path) -> None:
    path = root / "exercises/07-verified-algorithms-capstone/skeleton/algorithms.py"
    path.write_text(
        path.read_text(encoding="utf-8")
        + "\n# "
        + implementation_marker("1")
        + " skeleton leak mutant\n",
        encoding="utf-8",
    )


def add_implementation_zero(root: Path) -> None:
    path = root / "exercises/07-verified-algorithms-capstone/reference/algorithms.py"
    path.write_text(
        path.read_text(encoding="utf-8")
        + "\n# "
        + implementation_marker("0")
        + " invented bootstrap mutant\n",
        encoding="utf-8",
    )


def remove_implementation_index_row(root: Path) -> None:
    path = root / "exercises/07-verified-algorithms-capstone/README.md"
    lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
    selected = [line for line in lines if not line.startswith("| 6 |")]
    if len(selected) != len(lines) - 1:
        raise AssertionError("Implementation index 6 row가 정확히 하나가 아닙니다")
    path.write_text("".join(selected), encoding="utf-8")


def swap_implementation_index_symbols(root: Path) -> None:
    path = root / "exercises/07-verified-algorithms-capstone/README.md"
    text = path.read_text(encoding="utf-8")
    first = "| 1 | `prefix_sums`, `range_sum` |"
    second = "| 2 | `lower_bound` |"
    if text.count(first) != 1 or text.count(second) != 1:
        raise AssertionError("Implementation index symbol swap fixture가 단일하지 않습니다")
    text = text.replace(first, "| 1 | `lower_bound` |", 1)
    text = text.replace(second, "| 2 | `prefix_sums`, `range_sum` |", 1)
    path.write_text(text, encoding="utf-8")


def move_secondary_implementation_symbol(root: Path) -> None:
    path = root / "exercises/07-verified-algorithms-capstone/README.md"
    text = path.read_text(encoding="utf-8")
    first = "| 1 | `prefix_sums`, `range_sum` |"
    second = "| 2 | `lower_bound` |"
    if text.count(first) != 1 or text.count(second) != 1:
        raise AssertionError("secondary Implementation symbol fixture가 단일하지 않습니다")
    text = text.replace(first, "| 1 | `prefix_sums` |", 1)
    text = text.replace(second, "| 2 | `lower_bound`, `range_sum` |", 1)
    path.write_text(text, encoding="utf-8")


def complete_one_skeleton_function(root: Path) -> None:
    path = root / "exercises/07-verified-algorithms-capstone/skeleton/algorithms.py"
    replace_once(path, '    return _missing("prefix_sums")', "    return [0]")


def change_skeleton_signature(root: Path) -> None:
    path = root / "exercises/07-verified-algorithms-capstone/skeleton/algorithms.py"
    replace_once(
        path,
        "def lower_bound(values: Sequence[int], target: int) -> int:",
        "def lower_bound(values: Sequence[int]) -> int:",
    )


def duplicate_skeleton_function(root: Path) -> None:
    path = root / "exercises/07-verified-algorithms-capstone/skeleton/algorithms.py"
    text = path.read_text(encoding="utf-8")
    insertion = "\ndef prefix_sums(values: Sequence[int]) -> list[int]:\n    return [0]\n"
    path.write_text(text + insertion, encoding="utf-8")


def add_private_solution_helper(root: Path) -> None:
    path = root / "exercises/07-verified-algorithms-capstone/skeleton/algorithms.py"
    path.write_text(
        path.read_text(encoding="utf-8")
        + "\ndef _solution_prefix(values: Sequence[int]) -> list[int]:\n"
        + "    return [0, *values]\n",
        encoding="utf-8",
    )


def add_skeleton_import_escape(root: Path) -> None:
    path = root / "exercises/07-verified-algorithms-capstone/skeleton/algorithms.py"
    replace_once(
        path,
        "from dataclasses import dataclass\n",
        "from dataclasses import dataclass\nfrom pathlib import Path\n",
    )


def restore_reference_default(root: Path) -> None:
    path = root / "Makefile"
    replace_once(path, "IMPL ?= workspace", "IMPL ?= reference")


def restore_checker_reference_default(root: Path) -> None:
    path = root / "exercises/07-verified-algorithms-capstone/check.py"
    replace_once(
        path,
        'default="workspace"',
        'default=os.environ.get("EXERCISE_IMPL", "reference")',
    )


def swap_roadmap_docs(root: Path) -> None:
    path = root / "docs/00-roadmap.md"
    text = path.read_text(encoding="utf-8")
    first = "01-foundations/01-problem-contracts-and-counterexamples.md"
    second = "01-foundations/02-asymptotic-analysis.md"
    if text.count(first) != 1 or text.count(second) != 1:
        raise AssertionError("roadmap doc swap fixture가 단일하지 않습니다")
    text = text.replace(first, "__DOC_SWAP__", 1).replace(second, first, 1).replace(
        "__DOC_SWAP__", second, 1
    )
    path.write_text(text, encoding="utf-8")


def swap_roadmap_exercises(root: Path) -> None:
    path = root / "docs/00-roadmap.md"
    text = path.read_text(encoding="utf-8")
    first = "../exercises/01-analysis-and-counterexamples/README.md"
    second = "../exercises/02-data-structures/README.md"
    if text.count(first) != 1 or text.count(second) != 1:
        raise AssertionError("roadmap exercise swap fixture가 단일하지 않습니다")
    text = text.replace(first, "__EXERCISE_SWAP__", 1).replace(second, first, 1).replace(
        "__EXERCISE_SWAP__", second, 1
    )
    path.write_text(text, encoding="utf-8")


def hide_unexpected_source_in_workspace_name(root: Path) -> None:
    path = root / "docs/workspace/unexpected.md"
    path.parent.mkdir()
    path.write_text("# unexpected\n", encoding="utf-8")


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
        ("missing README ordered mapping", remove_readme_mapping, "단계별 학습 지도 누락"),
        ("missing README mapping column", remove_mapping_column, "canonical field 누락"),
        ("missing README mapping document", remove_mapping_doc, "ordered mapping 문서는 정확히 한 번"),
        (
            "missing Implementation anchor",
            remove_implementation_anchor,
            "README·source Implementation 번호 대응 불일치",
        ),
        (
            "malformed Implementation anchor",
            add_malformed_implementation_anchor,
            "marker 닫힘·형식 오류",
        ),
        (
            "duplicate Implementation anchor",
            duplicate_implementation_anchor,
            "anchor 중복",
        ),
        (
            "Implementation anchor leaked to skeleton",
            add_skeleton_implementation_anchor,
            "marker 금지 경로",
        ),
        ("invented Implementation zero", add_implementation_zero, "번호 대응 불일치"),
        (
            "missing Implementation README index row",
            remove_implementation_index_row,
            "README·source Implementation 번호 대응 불일치",
        ),
        (
            "swapped Implementation README symbols",
            swap_implementation_index_symbols,
            "row가 source anchor symbol을 가리키지 않습니다",
        ),
        (
            "secondary Implementation symbol moved to wrong owner",
            move_secondary_implementation_symbol,
            "nearest-anchor public symbol이 없습니다",
        ),
        (
            "completed skeleton function",
            complete_one_skeleton_function,
            "designated _missing 경계",
        ),
        (
            "changed skeleton signature",
            change_skeleton_signature,
            "signature 불일치",
        ),
        (
            "duplicate completed skeleton function",
            duplicate_skeleton_function,
            "top-level 정의는 정확히 한 번",
        ),
        (
            "private solution helper in skeleton",
            add_private_solution_helper,
            "정답 helper 또는 예상 밖 정의",
        ),
        (
            "unexpected skeleton import",
            add_skeleton_import_escape,
            "skeleton import 계약",
        ),
        ("reference false-green default", restore_reference_default, "기본 구현은 workspace"),
        (
            "checker reference false-green default",
            restore_checker_reference_default,
            "--impl 기본값은 workspace",
        ),
        (
            "unexpected source hidden by workspace directory name",
            hide_unexpected_source_in_workspace_name,
            "exact-tree 예상 밖 파일",
        ),
        ("swapped roadmap documents", swap_roadmap_docs, "roadmap 정본 문서 순서 오류"),
        (
            "swapped roadmap exercises",
            swap_roadmap_exercises,
            "roadmap exercise 대응 순서 오류",
        ),
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
