#!/usr/bin/env python3
"""Validate the exact operating-systems guide tree and learning contracts."""

from __future__ import annotations

import ast
import json
import os
from pathlib import Path
import re
import stat
import sys
from typing import Any
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
    "build-sanitize",
    "workspace",
}
IGNORED_PREFIXES = (".checker-mutant.", ".workspace-copy.", ".workspace-create.lock")
IGNORED_NAMES = {".DS_Store"}
CORE_DOCS = {
    "docs/01-boundary-and-execution/01-kernel-boundary-and-events.md",
    "docs/01-boundary-and-execution/02-processes-threads-and-context-switches.md",
    "docs/01-boundary-and-execution/03-cpu-scheduling.md",
    "docs/01-boundary-and-execution/04-blocking-wakeup-and-ipc.md",
    "docs/02-concurrency/01-races-atomicity-and-ordering.md",
    "docs/02-concurrency/02-synchronization-primitives.md",
    "docs/02-concurrency/03-deadlock-and-progress.md",
    "docs/03-virtual-memory/01-address-spaces-and-faults.md",
    "docs/03-virtual-memory/02-demand-paging-cow-and-replacement.md",
    "docs/04-storage-and-io/01-filesystems-page-cache-and-crash-consistency.md",
    "docs/04-storage-and-io/02-device-io-interrupts-and-dma.md",
    "docs/80-extended-labs.md",
}
DOC_HEADINGS = ("학습 목표", "핵심 모델", "연결 실습", "완료 기준", "실패 조건", "자기 설명")
EXERCISE_HEADINGS = ("목표", "체크포인트", "완료 기준", "자기 설명", "검증")
EXAMPLE_HEADINGS = ("학습 목표", "준비 환경", "완료 기준", "자기 설명", "검증")
CHECKPOINTS = (
    "01-lifecycle",
    "02-synchronization",
    "03-scheduler",
    "04-deadlock",
    "05-paging",
    "06-storage",
    "07-device-io",
    "08-cli",
)
PACKAGE_MODULES = {
    "__init__.py",
    "cli.py",
    "deadlock.py",
    "device_io.py",
    "filesystem.py",
    "journal.py",
    "lifecycle.py",
    "paging.py",
    "scheduler.py",
    "synchronization.py",
}
SKELETON_BOUNDARY_MODULES = PACKAGE_MODULES - {"__init__.py"}
FIXTURES = {
    "condition.json",
    "deadlock-cycle.json",
    "deadlock-safe.json",
    "filesystem.json",
    "io.json",
    "lifecycle.json",
    "replacement.json",
    "schedule.json",
    "translation.json",
}
FAILURE_FIXTURES = {
    "01-lifecycle-duplicate-ready.json",
    "02-lifecycle-blocked-without-queue.json",
    "03-memory-shared-writable.json",
    "04-device-double-location.json",
    "05-filesystem-link-count.json",
    "06-journal-commit-before-begin.json",
    "07-device-queue-depth.json",
    "08-lifecycle-stale-wait-metadata.json",
}
EXECUTABLES = {
    "prepare.sh",
    "verify.sh",
    "scripts/atomic_directory_publish.py",
    "scripts/new-workspace.sh",
    "scripts/repository_state.py",
    "scripts/run_with_timeout.py",
    "scripts/test-checker.py",
    "scripts/test-common-safety.py",
    "scripts/test-examples.py",
    "scripts/test-validator.py",
    "scripts/test-verify-preflight.py",
    "scripts/test-verify-signal.py",
    "scripts/test-workspace-tools.py",
    "scripts/validate.py",
    "exercises/kernel-model/check.py",
    "exercises/kernel-model/check.sh",
    "exercises/kernel-model/reference/kernel-model.py",
    "exercises/kernel-model/skeleton/kernel-model.py",
}
LEGACY_PATHS = {
    "docs/01-kernel-boundary-and-events.md",
    "docs/02-processes-threads-and-context-switches.md",
    "docs/03-cpu-scheduling.md",
    "docs/04-concurrency-atomics-and-memory-order.md",
    "docs/05-synchronization-primitives.md",
    "docs/06-deadlock-and-progress.md",
    "docs/07-address-spaces-page-tables-and-tlb.md",
    "docs/08-demand-paging-cow-and-replacement.md",
    "docs/09-filesystems-page-cache-and-crash-consistency.md",
    "docs/10-device-io-interrupts-and-dma.md",
}
ERRORS: list[str] = []


def report(message: str) -> None:
    ERRORS.append(message)


def ignored(path: Path) -> bool:
    relative = path.relative_to(ROOT)
    return (
        path.name in IGNORED_NAMES
        or any(part in IGNORED_PARTS for part in relative.parts)
        or any(part.startswith(IGNORED_PREFIXES) for part in relative.parts)
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
        elif stat.S_ISDIR(metadata.st_mode):
            if stat.S_IMODE(metadata.st_mode) != 0o755:
                report(f"source directory mode는 0755여야 합니다: {relative}")
        else:
            report(f"source tree 특수 파일 금지: {relative}")
    return result


def check_exact_tree(actual: set[str]) -> None:
    if not MANIFEST.is_file():
        report("layout manifest가 없습니다")
        return
    lines = MANIFEST.read_text(encoding="utf-8").splitlines()
    expected_lines = [line for line in lines if line and not line.startswith("#")]
    expected = set(expected_lines)
    if lines != expected_lines or expected_lines != sorted(expected_lines) or len(expected) != len(expected_lines):
        report("layout manifest는 빈 줄·주석·중복 없이 정렬되어야 합니다")
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


def normalized_rubric(text: str, headings: tuple[str, ...]) -> str:
    return " || ".join(" ".join(section(text, heading).split()) for heading in headings)


def visible_markdown(text: str) -> tuple[str, bool]:
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
    return "\n".join(visible), in_fence


def check_heading_contract(relative: str, text: str, headings: tuple[str, ...], label: str) -> None:
    positions: list[int] = []
    for heading in headings:
        token = f"## {heading}\n"
        if text.count(token) != 1:
            report(f"{label} heading 누락/중복: {relative} -> {heading}")
        positions.append(text.find(token))
    if all(position >= 0 for position in positions) and positions != sorted(positions):
        report(f"{label} heading 순서 오류: {relative}")


def check_markdown() -> None:
    link_pattern = re.compile(r"(?<!!)\[[^\]]+\]\(([^)\n]+)\)")
    completion_owners: dict[str, str] = {}
    explanation_owners: dict[str, str] = {}
    concept_rubric_owners: dict[str, str] = {}
    for path in sorted(ROOT.rglob("*.md")):
        if ignored(path):
            continue
        relative = path.relative_to(ROOT).as_posix()
        text = path.read_text(encoding="utf-8")
        visible, fence_open = visible_markdown(text)
        visible_lines = visible.splitlines()
        if (
            not visible_lines
            or not visible_lines[0].startswith("# ")
            or sum(line.startswith("# ") for line in visible_lines) != 1
        ):
            report(f"H1은 첫 줄에 정확히 하나여야 합니다: {relative}")
        if fence_open:
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
            check_heading_contract(relative, text, DOC_HEADINGS, "본문 학습")
            completion = section(text, "완료 기준")
            explanation = section(text, "자기 설명")
            connection = section(text, "연결 실습")
            if len(re.findall(r"^- ", completion, flags=re.MULTILINE)) < 3:
                report(f"본문 완료 기준 3개 미만: {relative}")
            if len(re.findall(r"\?\s*$", explanation, flags=re.MULTILINE)) < 2:
                report(f"본문 자기 설명 질문 2개 미만: {relative}")
            if "examples/" not in connection and "exercises/" not in connection:
                report(f"본문 연결 실습 경로 누락: {relative}")
            normalized_completion = " ".join(completion.split())
            normalized_explanation = " ".join(explanation.split())
            if normalized_completion in completion_owners:
                report(f"복사형 완료 기준: {relative}, {completion_owners[normalized_completion]}")
            if normalized_explanation in explanation_owners:
                report(f"복사형 자기 설명: {relative}, {explanation_owners[normalized_explanation]}")
            full_rubric = normalized_rubric(text, DOC_HEADINGS)
            if full_rubric in concept_rubric_owners:
                report(f"복사형 본문 전체 rubric: {relative}, {concept_rubric_owners[full_rubric]}")
            completion_owners[normalized_completion] = relative
            explanation_owners[normalized_explanation] = relative
            concept_rubric_owners[full_rubric] = relative

    exercise = ROOT / "exercises/kernel-model/README.md"
    practice_rubrics: list[tuple[str, str]] = []
    if exercise.is_file():
        text = exercise.read_text(encoding="utf-8")
        check_heading_contract("exercises/kernel-model/README.md", text, EXERCISE_HEADINGS, "exercise 학습")
        if len(re.findall(r"^- ", section(text, "완료 기준"), flags=re.MULTILINE)) < 4:
            report("exercise 완료 기준 4개 미만")
        if len(re.findall(r"\?\s*$", section(text, "자기 설명"), flags=re.MULTILINE)) < 4:
            report("exercise 자기 설명 질문 4개 미만")
        for checkpoint in CHECKPOINTS:
            if text.count(f"`{checkpoint}`") < 1 or f"CHECKPOINT={checkpoint}" not in text:
                report(f"exercise checkpoint 설명/명령 누락: {checkpoint}")
        if "./scripts/new-workspace.sh exercises/kernel-model" not in text:
            report("exercise 안전한 workspace 생성 명령 누락")
        practice_rubrics.append(
            (
                "exercises/kernel-model/README.md",
                normalized_rubric(text, ("목표", "완료 기준", "자기 설명", "검증")),
            )
        )

    examples = ROOT / "examples/README.md"
    if examples.is_file():
        text = examples.read_text(encoding="utf-8")
        check_heading_contract("examples/README.md", text, EXAMPLE_HEADINGS, "examples 학습")
        if len(re.findall(r"^- ", section(text, "완료 기준"), flags=re.MULTILINE)) < 5:
            report("examples 완료 기준 5개 미만")
        if len(re.findall(r"\?\s*$", section(text, "자기 설명"), flags=re.MULTILINE)) < 5:
            report("examples 자기 설명 질문 5개 미만")
        practice_rubrics.append(
            (
                "examples/README.md",
                normalized_rubric(text, ("학습 목표", "완료 기준", "자기 설명", "검증")),
            )
        )

    practice_owners: dict[str, str] = {}
    for relative, rubric in practice_rubrics:
        if rubric in practice_owners:
            report(f"복사형 exercise 전체 rubric: {relative}, {practice_owners[rubric]}")
        practice_owners[rubric] = relative


def read_json(path: Path) -> Any | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        report(f"JSON fixture 오류: {path.relative_to(ROOT)}: {error}")
        return None


def check_fixtures_and_packages() -> None:
    exercise = ROOT / "exercises/kernel-model"
    fixtures_dir = exercise / "fixtures"
    failure_dir = exercise / "failure-fixtures"
    actual_fixtures = {path.name for path in fixtures_dir.glob("*.json")} if fixtures_dir.is_dir() else set()
    actual_failures = {path.name for path in failure_dir.glob("*.json")} if failure_dir.is_dir() else set()
    if actual_fixtures != FIXTURES:
        report(f"정상 fixture exact set 오류: missing={sorted(FIXTURES - actual_fixtures)} extra={sorted(actual_fixtures - FIXTURES)}")
    if actual_failures != FAILURE_FIXTURES:
        report(
            f"failure fixture exact set 오류: missing={sorted(FAILURE_FIXTURES - actual_failures)} "
            f"extra={sorted(actual_failures - FAILURE_FIXTURES)}"
        )
    for name in sorted(actual_fixtures):
        data = read_json(fixtures_dir / name)
        if not isinstance(data, dict):
            report(f"정상 fixture 최상위 object 필요: {name}")
        elif not isinstance(data.get("expected"), dict) or not data["expected"]:
            report(f"정상 fixture expected object 누락/비어 있음: {name}")
    for name in sorted(actual_failures):
        data = read_json(failure_dir / name)
        if not isinstance(data, dict):
            report(f"failure fixture 최상위 object 필요: {name}")
        elif not isinstance(data.get("expected_error"), str) or not data["expected_error"].strip():
            report(f"failure fixture expected_error 누락/비어 있음: {name}")

    for variant in ("skeleton", "reference"):
        package = exercise / variant / "kernel_model"
        actual_modules = {path.name for path in package.glob("*.py")} if package.is_dir() else set()
        if actual_modules != PACKAGE_MODULES:
            report(
                f"{variant} package exact module 오류: "
                f"missing={sorted(PACKAGE_MODULES - actual_modules)} extra={sorted(actual_modules - PACKAGE_MODULES)}"
            )


def assigned_literal(tree: ast.AST, name: str) -> Any | None:
    for node in ast.walk(tree):
        value: ast.expr | None = None
        if isinstance(node, ast.Assign) and any(isinstance(target, ast.Name) and target.id == name for target in node.targets):
            value = node.value
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name) and node.target.id == name:
            value = node.value
        if value is not None:
            try:
                return ast.literal_eval(value)
            except (TypeError, ValueError):
                return None
    return None


def check_exercise_sources() -> None:
    exercise = ROOT / "exercises/kernel-model"
    reference_sources: list[str] = []
    skeleton_total = 0
    for module in sorted(PACKAGE_MODULES):
        reference = exercise / "reference/kernel_model" / module
        skeleton = exercise / "skeleton/kernel_model" / module
        if reference.is_file():
            reference_sources.append(reference.read_text(encoding="utf-8"))
        if module in SKELETON_BOUNDARY_MODULES and skeleton.is_file():
            try:
                tree = ast.parse(skeleton.read_text(encoding="utf-8"), filename=str(skeleton))
            except SyntaxError:
                continue
            boundaries = sum(
                isinstance(node, ast.Raise)
                and isinstance(node.exc, ast.Call)
                and isinstance(node.exc.func, ast.Name)
                and node.exc.func.id == "NotImplementedError"
                for node in ast.walk(tree)
            )
            skeleton_total += boundaries
            if boundaries == 0:
                report(f"skeleton 구현 경계 누락: {module}")
    joined_reference = "\n".join(reference_sources)
    if "NotImplementedError" in joined_reference or re.search(r"\bTODO\b", joined_reference):
        report("reference에 미완성 표식이 있습니다")
    if skeleton_total < 50:
        report(f"skeleton 구현 경계가 부족합니다: {skeleton_total}")

    checker = exercise / "check.py"
    if not checker.is_file():
        return
    try:
        tree = ast.parse(checker.read_text(encoding="utf-8"), filename=str(checker))
    except SyntaxError:
        return
    if assigned_literal(tree, "CHECKPOINTS") != CHECKPOINTS:
        report("checker CHECKPOINTS exact 계약 오류")
    test_names: set[str] = set()
    test_count = 0
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) or not node.name.startswith("test_"):
            continue
        if node.name in test_names:
            report(f"checker 중복 test 이름: {node.name}")
        test_names.add(node.name)
        test_count += 1
        assertions: set[str] = set()
        assertion_count = 0
        for child in ast.walk(node):
            if not (
                isinstance(child, ast.Call)
                and isinstance(child.func, ast.Attribute)
                and child.func.attr.startswith("assert")
            ):
                continue
            normalized = ast.dump(child, include_attributes=False)
            if normalized in assertions:
                report(f"checker 중복 assertion: {node.name}")
            assertions.add(normalized)
            assertion_count += 1
        if assertion_count == 0:
            report(f"checker assertion 없는 test: {node.name}")
    if test_count < 20:
        report(f"checker test가 부족합니다: {test_count}")


def check_sources(actual: set[str]) -> None:
    for relative in sorted(actual):
        path = ROOT / relative
        try:
            data = path.read_bytes()
        except OSError as error:
            report(f"source를 읽을 수 없습니다: {relative}: {error}")
            continue
        if not data:
            report(f"빈 source 파일: {relative}")
        if b"\r\n" in data:
            report(f"CRLF 금지: {relative}")
        if any(line.endswith((b" ", b"\t")) for line in data.splitlines()):
            report(f"줄 끝 공백 금지: {relative}")
        if path.suffix == ".py":
            try:
                ast.parse(data.decode("utf-8"), filename=relative)
            except (SyntaxError, UnicodeDecodeError) as error:
                report(f"Python 문법 오류: {relative}: {error}")
    for relative in sorted(EXECUTABLES):
        path = ROOT / relative
        if not path.is_file():
            report(f"실행 파일 누락: {relative}")
        elif not path.stat().st_mode & stat.S_IXUSR or not path.read_bytes().startswith(b"#!"):
            report(f"실행 mode/shebang 오류: {relative}")


def check_versions_navigation_and_public_commands() -> None:
    for relative in ("README.md", "docs/00-roadmap.md", "prepare.sh"):
        path = ROOT / relative
        text = path.read_text(encoding="utf-8") if path.is_file() else ""
        if "3.12" not in text:
            report(f"Python 3.12 기준 누락: {relative}")
    roadmap_path = ROOT / "docs/00-roadmap.md"
    roadmap = roadmap_path.read_text(encoding="utf-8") if roadmap_path.is_file() else ""
    for relative in sorted(CORE_DOCS):
        from_docs = Path(relative).relative_to("docs").as_posix()
        if from_docs not in roadmap and Path(relative).name not in roadmap:
            report(f"roadmap 정본 문서 누락: {relative}")
    for requirement in (
        "## 대상 독자와 선행지식",
        "## 이 가이드가 소유하는 범위",
        "## 권장 읽기 순서",
        "## 목적별 짧은 경로",
        "## 실습의 두 종류",
        "## 완료 기준",
        "## 지원 환경과 비보장 범위",
    ):
        if requirement not in roadmap:
            report(f"roadmap 학습 계약 누락: {requirement}")
    readme_path = ROOT / "README.md"
    readme = readme_path.read_text(encoding="utf-8") if readme_path.is_file() else ""
    for requirement in ("./prepare.sh", "./verify.sh", "make check", "C11", "Python 3.12"):
        if requirement not in readme:
            report(f"README 정본 계약 누락: {requirement}")
    all_text = "\n".join(
        path.read_text(encoding="utf-8", errors="replace")
        for path in sorted(ROOT.rglob("*"))
        if path.is_file() and not ignored(path) and path.suffix in {".md", ".sh"}
    )
    if re.search(r"Python\s*3\.10|Python 3\.10", all_text, flags=re.IGNORECASE):
        report("이전 Python 3.10 기준이 남았습니다")
    makefile_path = ROOT / "Makefile"
    makefile = makefile_path.read_text(encoding="utf-8") if makefile_path.is_file() else ""
    for target in (
        "prepare:",
        "verify:",
        "check:",
        "docs-check:",
        "meta-check:",
        "common-safety-check:",
        "log-safety-check:",
        "workspace-check:",
        "examples-check:",
        "sanitizer-check:",
        "exercise-check:",
        "checker-check:",
        "signal-check:",
        "checkpoint-check:",
        "clean:",
    ):
        if target not in makefile:
            report(f"공개 Make target 누락: {target[:-1]}")
    gitignore_path = ROOT / ".gitignore"
    gitignore = gitignore_path.read_text(encoding="utf-8") if gitignore_path.is_file() else ""
    for pattern in (".guide/", "build-sanitize/", "workspace/"):
        if pattern not in gitignore:
            report(f"생성물 ignore 계약 누락: {pattern}")


def main() -> int:
    actual = source_files()
    check_exact_tree(actual)
    check_markdown()
    check_fixtures_and_packages()
    check_exercise_sources()
    check_sources(actual)
    check_versions_navigation_and_public_commands()
    if ERRORS:
        print(f"guide-operating-systems 검증 실패: {len(ERRORS)}건", file=sys.stderr)
        for error in ERRORS:
            print(f"- {error}", file=sys.stderr)
        return 1
    print(
        f"[PASS] exact tree와 학습 계약: core docs {len(CORE_DOCS)}개, "
        f"checkpoints {len(CHECKPOINTS)}개, source files {len(actual)}개"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
