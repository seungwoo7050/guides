#!/usr/bin/env python3
"""Validate the exact guide-algorithms source tree and learning contracts."""

from __future__ import annotations

import ast
from collections import Counter
import io
import os
from pathlib import Path
import re
import stat
import sys
import tokenize
from urllib.parse import unquote

ROOT = Path(os.environ.get("GUIDE_ROOT", Path(__file__).resolve().parents[1])).resolve()
MANIFEST = ROOT / "scripts/layout-manifest.txt"
IGNORED_NAMES = {".DS_Store"}
LEARNER_WORKSPACE = Path("exercises/07-verified-algorithms-capstone/workspace")
CORE_DOCS = (
    "docs/01-foundations/01-problem-contracts-and-counterexamples.md",
    "docs/01-foundations/02-asymptotic-analysis.md",
    "docs/01-foundations/03-recurrences-and-divide-and-conquer.md",
    "docs/01-foundations/04-correctness-and-invariants.md",
    "docs/02-data-structures/01-linear-structures-ranges-and-hashing.md",
    "docs/02-data-structures/02-order-search-heaps-and-priority.md",
    "docs/02-data-structures/03-trees-and-balanced-search-trees.md",
    "docs/02-data-structures/04-disjoint-sets-and-amortized-analysis.md",
    "docs/03-design-techniques/01-brute-force-and-backtracking.md",
    "docs/03-design-techniques/02-greedy-methods.md",
    "docs/03-design-techniques/03-dynamic-programming.md",
    "docs/04-graph-algorithms/01-traversal-and-topological-order.md",
    "docs/04-graph-algorithms/02-minimum-spanning-trees.md",
    "docs/04-graph-algorithms/03-shortest-paths.md",
    "docs/04-graph-algorithms/04-network-flow-and-matching.md",
    "docs/05-string-algorithms/01-string-matching-and-preprocessing.md",
    "docs/06-complexity/01-sorting-stability-and-lower-bounds.md",
    "docs/06-complexity/02-complexity-classes-and-reductions.md",
    "docs/07-mixed-review-and-capstone.md",
    "docs/80-extended-practice.md",
)
EXERCISES = (
    "exercises/01-analysis-and-counterexamples",
    "exercises/02-data-structures",
    "exercises/03-design-techniques",
    "exercises/04-graphs",
    "exercises/05-strings",
    "exercises/06-complexity",
    "exercises/07-verified-algorithms-capstone",
)
DOC_HEADINGS = (
    "학습 목표",
    "선행 개념",
    "핵심 모델",
    "연결 실습",
    "완료 기준",
    "실패 조건",
    "연습",
)
EXERCISE_HEADINGS = ("목표", "완료 기준", "자기 설명", "검증")
EXECUTABLES = {
    "prepare.sh",
    "verify.sh",
    "scripts/new-workspace.sh",
    "scripts/atomic_directory_publish.py",
    "scripts/repository_state.py",
    "scripts/run_with_timeout.py",
    "scripts/test-checker.py",
    "scripts/test-prepare-marker.py",
    "scripts/test-runner-safety.py",
    "scripts/test-validator.py",
    "scripts/test-verify-preflight.py",
    "scripts/test-workspace-tools.py",
    "scripts/validate.py",
    "exercises/07-verified-algorithms-capstone/check.py",
}
LEGACY_PATHS = {
    "docs/01-problem-solving-loop.md",
    "docs/02-cpp17-toolkit.md",
    "docs/03-linear-data-and-ranges.md",
    "docs/04-order-search-and-priority.md",
    "docs/05-trees-and-graphs.md",
    "docs/06-brute-force-greedy-and-dp.md",
    "docs/07-mixed-problems-and-review.md",
    "docs/08-asymptotic-analysis-recurrences-and-correctness.md",
    "docs/09-sorting-stability-and-lower-bounds.md",
    "docs/10-amortized-analysis.md",
    "docs/11-binary-search-trees-and-red-black-trees.md",
    "docs/12-minimum-spanning-trees.md",
    "docs/13-shortest-paths-with-negative-edges.md",
    "docs/14-string-matching-and-preprocessing.md",
    "docs/15-complexity-classes-and-reductions.md",
    "docs/16-network-flow-and-bipartite-matching.md",
    "exercises/verified-algorithms",
}
ERRORS: list[str] = []
README_MAPPING_HEADER = (
    "| 순서 | 문서 | 관찰 예제 | 직접 수행 | 수정 위치 | 검증 | 완료 뒤 비교·다음 |"
)
README_MAPPING_DOCS = ("docs/00-roadmap.md", *CORE_DOCS)
README_MAPPING_EXERCISES = tuple(
    f"{exercise}/README.md" for exercise in EXERCISES
)
IMPLEMENTATION_REFERENCE = Path(
    "exercises/07-verified-algorithms-capstone/reference/algorithms.py"
)
IMPLEMENTATION_README = Path("exercises/07-verified-algorithms-capstone/README.md")
PUBLIC_ALGORITHM_FUNCTIONS = (
    "prefix_sums",
    "range_sum",
    "lower_bound",
    "bfs_distances",
    "dijkstra",
    "knapsack_01",
    "select_intervals",
    "red_black_height",
    "kruskal_mst",
    "bellman_ford",
    "kmp_find",
    "max_flow",
    "lcs_length",
)
MARKER_OPEN = "[" + "Implementation "
IMPLEMENTATION_MARKER = re.compile(
    re.escape(MARKER_OPEN) + r"(?P<identifier>0|[1-9][0-9]*(?:-[1-9][0-9]*)?)\]"
)
ANY_IMPLEMENTATION_MARKER = re.compile(re.escape(MARKER_OPEN) + r"[^\]\n]+\]")


def report(message: str) -> None:
    ERRORS.append(message)


def ignored(path: Path) -> bool:
    relative = path.relative_to(ROOT)
    root_state = bool(relative.parts) and relative.parts[0] in {".git", ".guide"}
    learner_workspace = (
        relative == LEARNER_WORKSPACE or LEARNER_WORKSPACE in relative.parents
    )
    return (
        path.name in IGNORED_NAMES
        or root_state
        or "__pycache__" in relative.parts
        or learner_workspace
    )


def source_files() -> set[str]:
    result: set[str] = set()
    for path in ROOT.rglob("*"):
        if ignored(path):
            continue
        try:
            metadata = path.lstat()
        except OSError as error:
            report(f"source metadata를 읽을 수 없습니다: {path}: {error}")
            continue
        relative = path.relative_to(ROOT).as_posix()
        if stat.S_ISLNK(metadata.st_mode):
            report(f"source tree symlink 금지: {relative}")
            result.add(relative)
        elif stat.S_ISREG(metadata.st_mode):
            result.add(relative)
        elif not stat.S_ISDIR(metadata.st_mode):
            report(f"source tree 특수 파일 금지: {relative}")
    return result


def check_exact_tree(actual: set[str]) -> None:
    if not MANIFEST.is_file():
        report("layout manifest가 없습니다")
        return
    expected_lines = MANIFEST.read_text(encoding="utf-8").splitlines()
    expected = {line for line in expected_lines if line and not line.startswith("#")}
    if expected_lines != sorted(expected_lines) or len(expected) != len(
        [line for line in expected_lines if line and not line.startswith("#")]
    ):
        report("layout manifest는 중복 없이 정렬되어야 합니다")
    missing = sorted(expected - actual)
    unexpected = sorted(actual - expected)
    if missing:
        report(f"exact-tree 필수 파일 없음: {missing}")
    if unexpected:
        report(f"exact-tree 예상 밖 파일: {unexpected}")
    for legacy in sorted(LEGACY_PATHS):
        path = ROOT / legacy
        if path.exists() or path.is_symlink():
            report(f"legacy 경로가 남았습니다: {legacy}")


def github_slug(value: str) -> str:
    value = re.sub(r"`([^`]*)`", r"\1", value).strip().lower()
    value = re.sub(r"<[^>]+>", "", value)
    value = re.sub(r"[^\w\s가-힣-]", "", value)
    return re.sub(r"[\s-]+", "-", value).strip("-")


def anchors(path: Path) -> set[str]:
    values: set[str] = set()
    counts: dict[str, int] = {}
    in_fence = False
    marker = ""
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.lstrip()
        if stripped.startswith(("```", "~~~")):
            current = stripped[:3]
            if not in_fence:
                in_fence, marker = True, current
            elif marker == current:
                in_fence = False
            continue
        if in_fence:
            continue
        match = re.match(r"^#{1,6}\s+(.+?)\s*#*\s*$", line)
        if match:
            base = github_slug(match.group(1))
            count = counts.get(base, 0)
            counts[base] = count + 1
            values.add(base if count == 0 else f"{base}-{count}")
    return values


def section(text: str, heading: str) -> str:
    match = re.search(
        rf"^## {re.escape(heading)}\s*$\n(?P<body>.*?)(?=^## |\Z)",
        text,
        flags=re.MULTILINE | re.DOTALL,
    )
    return match.group("body") if match else ""


def visible_markdown(text: str) -> str:
    visible: list[str] = []
    in_fence = False
    marker = ""
    for line in text.splitlines():
        stripped = line.lstrip()
        if stripped.startswith(("```", "~~~")):
            current = stripped[:3]
            if not in_fence:
                in_fence, marker = True, current
            elif marker == current:
                in_fence = False
            continue
        if not in_fence:
            visible.append(re.sub(r"`[^`]*`", "", line))
    if in_fence:
        visible.append("UNCLOSED_FENCE")
    return "\n".join(visible)


def check_markdown() -> None:
    link_pattern = re.compile(r"(?<!!)\[[^\]]+\]\(([^)\n]+)\)")
    for path in sorted(ROOT.rglob("*.md")):
        if ignored(path):
            continue
        relative = path.relative_to(ROOT).as_posix()
        text = path.read_text(encoding="utf-8")
        lines = text.splitlines()
        if not lines or not lines[0].startswith("# ") or sum(line.startswith("# ") for line in lines) != 1:
            report(f"H1은 첫 줄에 정확히 하나여야 합니다: {relative}")
        visible = visible_markdown(text)
        if "UNCLOSED_FENCE" in visible:
            report(f"닫히지 않은 code fence: {relative}")
        for raw in link_pattern.findall(visible):
            target = raw.strip().split(maxsplit=1)[0].strip("<>")
            if target.startswith(("http://", "https://", "mailto:", "data:")):
                continue
            decoded = unquote(target)
            file_part, _, fragment = decoded.partition("#")
            resolved = path if not file_part else (path.parent / file_part).resolve()
            try:
                resolved.relative_to(ROOT)
            except ValueError:
                report(f"저장소 밖 링크: {relative} -> {target}")
                continue
            if not resolved.exists():
                report(f"깨진 링크: {relative} -> {target}")
                continue
            if resolved.is_dir():
                resolved = resolved / "README.md"
            if fragment and resolved.suffix.lower() == ".md" and github_slug(fragment) not in anchors(resolved):
                report(f"깨진 anchor: {relative} -> {target}")

        if relative in CORE_DOCS:
            positions: list[int] = []
            for heading in DOC_HEADINGS:
                token = f"## {heading}\n"
                if text.count(token) != 1:
                    report(f"문서 학습 heading 누락/중복: {relative} -> {heading}")
                positions.append(text.find(token))
            if all(position >= 0 for position in positions) and positions != sorted(positions):
                report(f"문서 학습 heading 순서 오류: {relative}")
            completion = section(text, "완료 기준")
            if len(re.findall(r"^- ", completion, flags=re.MULTILINE)) < 3:
                report(f"문서 완료 기준 3개 미만: {relative}")
            connection = section(text, "연결 실습")
            if "exercises/" not in connection and "../exercises/" not in connection:
                report(f"문서 연결 실습 링크 누락: {relative}")


def check_exercise_pedagogy() -> None:
    completion_owners: dict[str, str] = {}
    explanation_owners: dict[str, str] = {}
    for exercise in EXERCISES:
        readme = ROOT / exercise / "README.md"
        if not readme.is_file():
            report(f"exercise README 누락: {exercise}")
            continue
        text = readme.read_text(encoding="utf-8")
        positions: list[int] = []
        for heading in EXERCISE_HEADINGS:
            token = f"## {heading}\n"
            if text.count(token) != 1:
                report(f"exercise 학습 heading 누락/중복: {exercise} -> {heading}")
            positions.append(text.find(token))
        if all(position >= 0 for position in positions) and positions != sorted(positions):
            report(f"exercise heading 순서는 목표→완료 기준→자기 설명→검증이어야 합니다: {exercise}")
        completion = section(text, "완료 기준")
        explanation = section(text, "자기 설명")
        if len(re.findall(r"^- ", completion, flags=re.MULTILINE)) < 3:
            report(f"관찰 가능한 완료 기준 3개 미만: {exercise}")
        if len(re.findall(r"\?\s*$", explanation, flags=re.MULTILINE)) < 2:
            report(f"자기 설명 질문 2개 미만: {exercise}")
        normalized_completion = " ".join(completion.split())
        normalized_explanation = " ".join(explanation.split())
        if normalized_completion in completion_owners:
            report(f"복사형 완료 기준: {exercise}, {completion_owners[normalized_completion]}")
        if normalized_explanation in explanation_owners:
            report(f"복사형 자기 설명: {exercise}, {explanation_owners[normalized_explanation]}")
        completion_owners[normalized_completion] = exercise
        explanation_owners[normalized_explanation] = exercise


def check_sources(actual: set[str]) -> None:
    for relative in sorted(actual):
        path = ROOT / relative
        metadata = path.lstat()
        if not stat.S_ISREG(metadata.st_mode):
            continue
        if metadata.st_size == 0:
            report(f"빈 source 파일: {relative}")
        if path.suffix == ".py":
            try:
                ast.parse(path.read_text(encoding="utf-8"), filename=relative)
            except SyntaxError as error:
                report(f"Python 문법 오류: {relative}:{error.lineno}: {error.msg}")
        data = path.read_bytes()
        if b"\r\n" in data:
            report(f"CRLF 금지: {relative}")
        if any(line.endswith((b" ", b"\t")) for line in data.splitlines()):
            report(f"줄 끝 공백 금지: {relative}")
    for relative in EXECUTABLES:
        path = ROOT / relative
        if not path.is_file():
            report(f"실행 파일 누락: {relative}")
        elif not path.stat().st_mode & stat.S_IXUSR or not path.read_bytes().startswith(b"#!"):
            report(f"실행 mode/shebang 오류: {relative}")
    reference = ROOT / "exercises/07-verified-algorithms-capstone/reference/algorithms.py"
    if reference.is_file():
        text = reference.read_text(encoding="utf-8")
        if "NotImplementedError" in text or re.search(r"\bTODO\b", text):
            report("reference에 미완성 표식이 있습니다")
    skeleton = ROOT / "exercises/07-verified-algorithms-capstone/skeleton/algorithms.py"
    if skeleton.is_file() and "NotImplementedError" not in skeleton.read_text(encoding="utf-8"):
        report("skeleton에 의도한 미구현 경계가 없습니다")


def check_versions_and_navigation() -> None:
    required_312 = (
        ROOT / "docs/00-roadmap.md",
        ROOT / "docs/90-implementation-profiles/python.md",
        ROOT / "prepare.sh",
    )
    for path in required_312:
        text = path.read_text(encoding="utf-8") if path.is_file() else ""
        if "3.12" not in text:
            report(f"Python 3.12 기준 누락: {path.relative_to(ROOT)}")
    for path in CORE_DOCS:
        document = ROOT / path
        if document.is_file() and "C++17" in document.read_text(encoding="utf-8"):
            report(f"언어 중립 core 문서에 C++17이 남았습니다: {path}")
    roadmap_path = ROOT / "docs/00-roadmap.md"
    readme_path = ROOT / "README.md"
    roadmap = roadmap_path.read_text(encoding="utf-8") if roadmap_path.is_file() else ""
    readme = readme_path.read_text(encoding="utf-8") if readme_path.is_file() else ""
    roadmap_doc_positions: list[int] = []
    for path in CORE_DOCS:
        relative_from_docs = Path(path).relative_to("docs").as_posix()
        count = roadmap.count(relative_from_docs)
        if count != 1:
            report(f"roadmap 정본 문서는 정확히 한 번이어야 합니다: {path} -> {count}")
        roadmap_doc_positions.append(roadmap.find(relative_from_docs))
    if all(position >= 0 for position in roadmap_doc_positions) and roadmap_doc_positions != sorted(
        roadmap_doc_positions
    ):
        report("roadmap 정본 문서 순서 오류")

    roadmap_exercise_positions: list[int] = []
    for exercise in EXERCISES:
        target = f"../{exercise}/README.md"
        count = roadmap.count(target)
        if count != 1:
            report(f"roadmap exercise 대응은 정확히 한 번이어야 합니다: {target} -> {count}")
        roadmap_exercise_positions.append(roadmap.find(target))
    if all(position >= 0 for position in roadmap_exercise_positions) and roadmap_exercise_positions != sorted(
        roadmap_exercise_positions
    ):
        report("roadmap exercise 대응 순서 오류")
    roadmap_requirements = (
        "## 대상 독자",
        "## 선행지식과 지원 환경",
        "필수 경로",
        "선택 경로",
        "## Exercise 대응",
        "## 종료 능력",
        "## 이 가이드가 다루지 않는 것",
        "## 완료 기준",
        "## 자동 검증의 한계",
    )
    for requirement in roadmap_requirements:
        if requirement not in roadmap:
            report(f"roadmap 학습 계약 누락: {requirement}")
    for command in ("./prepare.sh", "./verify.sh", "make check"):
        if command not in readme:
            report(f"README 정본 명령 누락: {command}")


def check_readme_learning_map() -> None:
    path = ROOT / "README.md"
    if not path.is_file():
        return
    readme = path.read_text(encoding="utf-8")
    mapping = section(readme, "단계별 학습 지도")
    if not mapping:
        report("README 단계별 학습 지도 누락")
        return
    if mapping.count(README_MAPPING_HEADER) != 1:
        report("README ordered mapping canonical field 누락/중복")

    doc_positions: list[int] = []
    for relative in README_MAPPING_DOCS:
        count = mapping.count(relative)
        position = mapping.find(relative)
        if count != 1:
            report(f"README ordered mapping 문서는 정확히 한 번이어야 합니다: {relative} -> {count}")
        doc_positions.append(position)
    if all(position >= 0 for position in doc_positions) and doc_positions != sorted(
        doc_positions
    ):
        report("README ordered mapping 문서 순서 오류")

    exercise_positions: list[int] = []
    for relative in README_MAPPING_EXERCISES:
        count = mapping.count(relative)
        position = mapping.find(relative)
        if count != 1:
            report(f"README ordered mapping exercise는 정확히 한 번이어야 합니다: {relative} -> {count}")
        exercise_positions.append(position)
    if all(position >= 0 for position in exercise_positions) and exercise_positions != sorted(
        exercise_positions
    ):
        report("README ordered mapping exercise 순서 오류")

    required_mapping_contracts = (
        "저장소 밖 개인 학습 노트",
        "exercises/07-verified-algorithms-capstone/workspace/algorithms.py",
        "scripts/new-workspace.sh exercises/07-verified-algorithms-capstone",
        "make stage-check STAGE=data-structures",
        "make stage-check STAGE=design-techniques",
        "make stage-check STAGE=graphs",
        "make stage-check STAGE=strings",
        "make stage-check STAGE=all",
        "통과 뒤 `reference/`",
        "docs/80-extended-practice.md",
    )
    for contract in required_mapping_contracts:
        if contract not in mapping:
            report(f"README ordered mapping 학습 계약 누락: {contract}")
    if "별도 `examples/`가 없다" not in readme or "| — |" not in mapping:
        report("README example 부재 계약 누락")
    manual_contracts = ("make docs-check", "수학적 타당성", "채점하지 않")
    if any(contract not in readme for contract in manual_contracts):
        report("README 분석 evidence의 manual review 경계 누락")


def top_level_definitions(
    tree: ast.Module,
) -> dict[str, list[ast.FunctionDef | ast.ClassDef]]:
    result: dict[str, list[ast.FunctionDef | ast.ClassDef]] = {}
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
            result.setdefault(node.name, []).append(node)
    return result


def one_definition(
    definitions: dict[str, list[ast.FunctionDef | ast.ClassDef]],
    name: str,
    expected_type: type[ast.FunctionDef] | type[ast.ClassDef],
) -> ast.FunctionDef | ast.ClassDef | None:
    candidates = definitions.get(name, [])
    if len(candidates) != 1 or not isinstance(candidates[0], expected_type):
        return None
    return candidates[0]


def class_field_contract(node: ast.ClassDef) -> tuple[tuple[str, ...], tuple[tuple[str, str, str], ...]]:
    decorators = tuple(
        ast.dump(decorator, include_attributes=False) for decorator in node.decorator_list
    )
    fields: list[tuple[str, str, str]] = []
    for statement in node.body:
        if isinstance(statement, ast.AnnAssign) and isinstance(statement.target, ast.Name):
            fields.append(
                (
                    statement.target.id,
                    ast.dump(statement.annotation, include_attributes=False),
                    ast.dump(statement.value, include_attributes=False)
                    if statement.value is not None
                    else "",
                )
            )
    return decorators, tuple(fields)


def check_skeleton_contract() -> None:
    reference_path = ROOT / IMPLEMENTATION_REFERENCE
    skeleton_path = ROOT / "exercises/07-verified-algorithms-capstone/skeleton/algorithms.py"
    if not reference_path.is_file() or not skeleton_path.is_file():
        return
    try:
        reference_tree = ast.parse(
            reference_path.read_text(encoding="utf-8"),
            filename=IMPLEMENTATION_REFERENCE.as_posix(),
        )
        skeleton_tree = ast.parse(
            skeleton_path.read_text(encoding="utf-8"),
            filename=skeleton_path.relative_to(ROOT).as_posix(),
        )
    except SyntaxError:
        return

    expected_import_tree = ast.parse(
        "from __future__ import annotations\n"
        "from dataclasses import dataclass\n"
        "from typing import Iterable, Sequence\n"
    )
    expected_imports = tuple(
        ast.dump(node, include_attributes=False) for node in expected_import_tree.body
    )
    skeleton_imports = tuple(
        ast.dump(node, include_attributes=False)
        for node in skeleton_tree.body
        if isinstance(node, (ast.Import, ast.ImportFrom))
    )
    if skeleton_imports != expected_imports:
        report("skeleton import 계약은 공개 자료형·type hint에 필요한 범위로 제한합니다")

    reference_defs = top_level_definitions(reference_tree)
    skeleton_defs = top_level_definitions(skeleton_tree)
    allowed_skeleton_definitions = {
        "_missing",
        "RedBlackNode",
        *PUBLIC_ALGORITHM_FUNCTIONS,
    }
    unexpected_definitions = sorted(set(skeleton_defs) - allowed_skeleton_definitions)
    if unexpected_definitions:
        report(f"skeleton에 정답 helper 또는 예상 밖 정의가 있습니다: {unexpected_definitions}")
    for name in sorted(allowed_skeleton_definitions):
        count = len(skeleton_defs.get(name, []))
        if count != 1:
            report(f"skeleton top-level 정의는 정확히 한 번이어야 합니다: {name} -> {count}")
    for statement in skeleton_tree.body:
        allowed_statement = isinstance(statement, (ast.Import, ast.ImportFrom, ast.FunctionDef, ast.ClassDef))
        if isinstance(statement, ast.Expr) and isinstance(statement.value, ast.Constant) and isinstance(
            statement.value.value, str
        ):
            allowed_statement = True
        if not allowed_statement:
            report(f"skeleton top-level 실행·상태 누출 금지: {type(statement).__name__}")

    reference_functions = {
        name
        for name, nodes in reference_defs.items()
        if len(nodes) == 1 and isinstance(nodes[0], ast.FunctionDef)
    }
    skeleton_functions = {
        name
        for name, nodes in skeleton_defs.items()
        if len(nodes) == 1 and isinstance(nodes[0], ast.FunctionDef)
    }
    expected_public = set(PUBLIC_ALGORITHM_FUNCTIONS)
    if {name for name in reference_functions if not name.startswith("_")} != expected_public:
        report("reference 공개 함수 inventory가 canonical contract와 다릅니다")
    if {name for name in skeleton_functions if not name.startswith("_")} != expected_public:
        report("skeleton 공개 함수 inventory가 reference와 다릅니다")

    for name in PUBLIC_ALGORITHM_FUNCTIONS:
        reference = one_definition(reference_defs, name, ast.FunctionDef)
        skeleton = one_definition(skeleton_defs, name, ast.FunctionDef)
        if not isinstance(reference, ast.FunctionDef) or not isinstance(
            skeleton, ast.FunctionDef
        ):
            continue
        reference_signature = (
            ast.dump(reference.args, include_attributes=False),
            ast.dump(reference.returns, include_attributes=False),
        )
        skeleton_signature = (
            ast.dump(skeleton.args, include_attributes=False),
            ast.dump(skeleton.returns, include_attributes=False),
        )
        if skeleton_signature != reference_signature:
            report(f"skeleton 공개 함수 signature 불일치: {name}")
        expected_boundary = (
            len(skeleton.body) == 1
            and isinstance(skeleton.body[0], ast.Return)
            and isinstance(skeleton.body[0].value, ast.Call)
            and isinstance(skeleton.body[0].value.func, ast.Name)
            and skeleton.body[0].value.func.id == "_missing"
            and len(skeleton.body[0].value.args) == 1
            and isinstance(skeleton.body[0].value.args[0], ast.Constant)
            and skeleton.body[0].value.args[0].value == name
        )
        if not expected_boundary:
            report(f"skeleton 함수가 designated _missing 경계를 벗어났습니다: {name}")

    reference_node = one_definition(reference_defs, "RedBlackNode", ast.ClassDef)
    skeleton_node = one_definition(skeleton_defs, "RedBlackNode", ast.ClassDef)
    if not isinstance(reference_node, ast.ClassDef) or not isinstance(
        skeleton_node, ast.ClassDef
    ):
        report("RedBlackNode 공개 자료형이 reference 또는 skeleton에 없습니다")
    elif class_field_contract(reference_node) != class_field_contract(skeleton_node):
        report("skeleton RedBlackNode field·decorator 계약이 reference와 다릅니다")
    elif any(not isinstance(statement, ast.AnnAssign) for statement in skeleton_node.body):
        report("skeleton RedBlackNode에 field 계약 외 구현을 두지 않습니다")

    missing = one_definition(skeleton_defs, "_missing", ast.FunctionDef)
    missing_boundary = (
        isinstance(missing, ast.FunctionDef)
        and len(missing.body) == 1
        and isinstance(missing.body[0], ast.Raise)
        and isinstance(missing.body[0].exc, ast.Call)
        and isinstance(missing.body[0].exc.func, ast.Name)
        and missing.body[0].exc.func.id == "NotImplementedError"
    )
    if not missing_boundary:
        report("skeleton _missing의 NotImplementedError 경계가 다릅니다")


def check_implementation_annotations(actual: set[str]) -> None:
    markers_by_path: dict[str, list[str]] = {}
    for relative in sorted(actual):
        path = ROOT / relative
        if not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        occurrences = ANY_IMPLEMENTATION_MARKER.findall(text)
        if text.count(MARKER_OPEN) != len(occurrences):
            report(f"Implementation marker 닫힘·형식 오류: {relative}")
        if not occurrences:
            continue
        identifiers: list[str] = []
        for occurrence in occurrences:
            match = IMPLEMENTATION_MARKER.fullmatch(occurrence)
            if match is None:
                report(f"Implementation marker 형식 오류: {relative}: {occurrence}")
                continue
            identifiers.append(match.group("identifier"))
        markers_by_path[relative] = identifiers

    reference_relative = IMPLEMENTATION_REFERENCE.as_posix()
    for relative in sorted(markers_by_path):
        if relative != reference_relative:
            report(f"Implementation marker 금지 경로: {relative}")

    reference_path = ROOT / IMPLEMENTATION_REFERENCE
    if not reference_path.is_file():
        return
    reference_text = reference_path.read_text(encoding="utf-8")
    identifiers = markers_by_path.get(reference_relative, [])
    counts = Counter(identifiers)
    if not identifiers:
        report("reference Implementation anchor가 없습니다")
    for identifier, count in sorted(counts.items()):
        if count != 1:
            report(f"reference Implementation anchor 중복: {identifier} -> {count}")

    def identifier_key(identifier: str) -> tuple[int, ...]:
        return tuple(int(part) for part in identifier.split("-"))

    top_levels = sorted(
        int(identifier) for identifier in counts if "-" not in identifier
    )
    if top_levels:
        first = 0 if top_levels[0] == 0 else 1
        expected_top_levels = list(range(first, top_levels[-1] + 1))
        if top_levels != expected_top_levels:
            report(
                "Implementation top-level 번호는 간격 없이 연속이어야 합니다: "
                f"{top_levels}"
            )
    for top_level in top_levels:
        children = sorted(
            int(identifier.split("-", 1)[1])
            for identifier in counts
            if identifier.startswith(f"{top_level}-")
            and identifier.count("-") == 1
        )
        if children and children != list(range(1, children[-1] + 1)):
            report(
                f"Implementation {top_level} substep은 1부터 연속이어야 합니다: {children}"
            )
    for identifier in counts:
        if "-" in identifier and int(identifier.split("-", 1)[0]) not in top_levels:
            report(f"Implementation substep의 top-level anchor가 없습니다: {identifier}")

    comment_identifiers: list[str] = []
    marker_lines: dict[str, int] = {}
    try:
        tokens = tokenize.generate_tokens(io.StringIO(reference_text).readline)
        for token in tokens:
            if token.type != tokenize.COMMENT:
                continue
            for match in IMPLEMENTATION_MARKER.finditer(token.string):
                identifier = match.group("identifier")
                comment_identifiers.append(identifier)
                marker_lines[identifier] = token.start[0]
    except tokenize.TokenError as error:
        report(f"reference tokenization 실패: {error}")
    if Counter(comment_identifiers) != counts:
        report("Implementation anchor는 Python comment token이어야 합니다")

    try:
        tree = ast.parse(reference_text, filename=reference_relative)
    except SyntaxError:
        tree = None
    primary_symbols: dict[str, str] = {}
    public_symbol_owners: dict[str, str] = {}
    if tree is not None:
        definitions = sorted(
            (
                (node.lineno, node.name)
                for node in tree.body
                if isinstance(node, (ast.FunctionDef, ast.ClassDef))
            ),
            key=lambda item: item[0],
        )
        for identifier in identifiers:
            marker_line = marker_lines.get(identifier)
            if marker_line is None:
                continue
            following = next(
                (name for line, name in definitions if line > marker_line),
                None,
            )
            if following is None:
                report(f"Implementation {identifier} 뒤에 top-level symbol이 없습니다")
            else:
                primary_symbols[identifier] = following

        public_symbols = {*PUBLIC_ALGORITHM_FUNCTIONS, "RedBlackNode"}
        ordered_markers = sorted(
            ((line, identifier) for identifier, line in marker_lines.items()),
            key=lambda item: item[0],
        )
        for line, symbol in definitions:
            if symbol not in public_symbols:
                continue
            preceding = [
                identifier
                for marker_line, identifier in ordered_markers
                if marker_line < line
            ]
            if preceding:
                public_symbol_owners[symbol] = preceding[-1]
        missing_public_coverage = sorted(public_symbols - set(public_symbol_owners))
        if missing_public_coverage:
            report(f"Implementation annotation public API coverage 누락: {missing_public_coverage}")

    readme_path = ROOT / IMPLEMENTATION_README
    if not readme_path.is_file():
        return
    readme = readme_path.read_text(encoding="utf-8")
    index = section(readme, "기준 구현 읽기 순서")
    index_rows: dict[str, list[str]] = {}
    index_ids: list[str] = []
    for line in index.splitlines():
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if not cells or re.fullmatch(r"\d+(?:-\d+)?", cells[0]) is None:
            continue
        identifier = cells[0]
        index_ids.append(identifier)
        if identifier in index_rows:
            report(f"capstone README Implementation index row 중복: {identifier}")
        index_rows[identifier] = cells[1:]

    expected_ids = sorted(counts, key=identifier_key)
    if index_ids != expected_ids or set(index_rows) != set(counts):
        report(
            "capstone README·source Implementation 번호 대응 불일치: "
            f"source={expected_ids}, index={index_ids}"
        )
    for identifier, symbol in primary_symbols.items():
        cells = index_rows.get(identifier, [])
        symbol_cell = cells[0] if cells else ""
        if f"`{symbol}`" not in symbol_cell:
            report(
                f"capstone README Implementation {identifier} row가 source anchor symbol을 가리키지 않습니다: {symbol}"
            )
    for symbol, identifier in sorted(public_symbol_owners.items()):
        cells = index_rows.get(identifier, [])
        symbol_cell = cells[0] if cells else ""
        if f"`{symbol}`" not in symbol_cell:
            report(
                f"capstone README Implementation {identifier} row에 nearest-anchor public symbol이 없습니다: {symbol}"
            )
    for symbol in (*PUBLIC_ALGORITHM_FUNCTIONS, "RedBlackNode"):
        if f"`{symbol}`" not in index:
            report(f"capstone README Implementation index public symbol 누락: {symbol}")
    index_contracts = (
        "reference/algorithms.py",
        "Git 작성 이력",
        "권장 구현 순서",
        "workspace",
        "`all`",
        "Implementation 0이 없다",
        "중간 CLI도 없다",
    )
    for contract in index_contracts:
        if contract not in index:
            report(f"capstone README Implementation scope 계약 누락: {contract}")
    if "Implementation 0이 없다" in index and "0" in counts:
        report("Implementation 0 면제 선언과 source anchor가 충돌합니다")


def check_learner_defaults() -> None:
    makefile_path = ROOT / "Makefile"
    checker_path = ROOT / "exercises/07-verified-algorithms-capstone/check.py"
    makefile = makefile_path.read_text(encoding="utf-8") if makefile_path.is_file() else ""
    checker = checker_path.read_text(encoding="utf-8") if checker_path.is_file() else ""
    if not re.search(r"^IMPL\s*\?=\s*workspace\s*$", makefile, flags=re.MULTILINE):
        report("learner stage-check 기본 구현은 workspace여야 합니다")
    if re.search(r'^\s*default\s*=\s*"workspace",\s*$', checker, flags=re.MULTILINE) is None:
        report("capstone checker --impl 기본값은 workspace여야 합니다")
    if re.search(r'["\']EXERCISE_IMPL["\']', checker):
        report("capstone checker --impl 기본값을 외부 환경으로 reference에 바꾸지 않습니다")


def main() -> int:
    actual = source_files()
    check_exact_tree(actual)
    check_markdown()
    check_exercise_pedagogy()
    check_sources(actual)
    check_versions_and_navigation()
    check_readme_learning_map()
    check_skeleton_contract()
    check_implementation_annotations(actual)
    check_learner_defaults()
    if ERRORS:
        print(f"guide-algorithms 검증 실패: {len(ERRORS)}건", file=sys.stderr)
        for error in ERRORS:
            print(f"- {error}", file=sys.stderr)
        return 1
    print(
        f"[PASS] exact tree와 학습 계약: core docs {len(CORE_DOCS)}개, "
        f"exercise {len(EXERCISES)}개, source files {len(actual)}개"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
