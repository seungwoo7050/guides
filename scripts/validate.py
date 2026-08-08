#!/usr/bin/env python3
"""Validate the exact guide-algorithms source tree and learning contracts."""

from __future__ import annotations

import ast
import os
from pathlib import Path
import re
import stat
import sys
from urllib.parse import unquote

ROOT = Path(os.environ.get("GUIDE_ROOT", Path(__file__).resolve().parents[1])).resolve()
MANIFEST = ROOT / "scripts/layout-manifest.txt"
IGNORED_PARTS = {
    ".git",
    ".guide",
    ".pytest_cache",
    ".venv",
    "__pycache__",
    "build",
    "dist",
    "htmlcov",
    "workspace",
}
IGNORED_NAMES = {".DS_Store"}
CORE_DOCS = {
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
}
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


def report(message: str) -> None:
    ERRORS.append(message)


def ignored(path: Path) -> bool:
    relative = path.relative_to(ROOT)
    return path.name in IGNORED_NAMES or any(part in IGNORED_PARTS for part in relative.parts)


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
    for path in sorted(CORE_DOCS):
        relative_from_docs = Path(path).relative_to("docs").as_posix()
        if relative_from_docs not in roadmap and Path(path).name not in roadmap:
            report(f"roadmap 정본 문서 누락: {path}")
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


def main() -> int:
    actual = source_files()
    check_exact_tree(actual)
    check_markdown()
    check_exercise_pedagogy()
    check_sources(actual)
    check_versions_and_navigation()
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
