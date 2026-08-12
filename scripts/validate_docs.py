#!/usr/bin/env python3
"""컴퓨터 구조 가이드의 최종 문서 구조와 실행 계약을 검사합니다."""

from __future__ import annotations

import ast
import os
from pathlib import Path, PurePosixPath
import re
import stat
import sys
from urllib.parse import unquote

DEFAULT_ROOT = Path(__file__).resolve().parents[1]
ROOT = Path(os.environ.get("GUIDE_ROOT", DEFAULT_ROOT)).resolve()
ERRORS: list[str] = []
CHECKS = 0

EXPECTED_DOCUMENTS = [
    ROOT / "docs/00-roadmap.md",
    ROOT / "docs/01-representation-and-isa/01-data-representation-and-arithmetic.md",
    ROOT / "docs/01-representation-and-isa/02-isa-assembly-and-program-execution.md",
    ROOT / "docs/01-representation-and-isa/03-performance-cpi-and-amdahl.md",
    ROOT / "docs/02-in-order-execution/04-datapath-and-control.md",
    ROOT / "docs/02-in-order-execution/05-pipeline-hazards-and-branching.md",
    ROOT / "docs/03-memory-hierarchy/06-cache-locality-and-amat.md",
    ROOT / "docs/03-memory-hierarchy/07-address-translation-and-tlb.md",
    ROOT / "docs/04-parallel-execution/08-superscalar-out-of-order-and-speculation.md",
    ROOT / "docs/04-parallel-execution/09-simd-vectorization-and-data-layout.md",
    ROOT / "docs/04-parallel-execution/10-multicore-coherence-and-false-sharing.md",
]
EXPECTED_REFERENCES = [
    ROOT / "reference/mips-riscv-crosswalk.md",
    ROOT / "reference/formulas-and-checklist.md",
    ROOT / "reference/sources.md",
    ROOT / "reference/version-baseline.md",
    ROOT / "exercises/processor-model/spec/tiny-risc-isa.md",
]
EXPECTED_EXAMPLES = [
    ROOT / "examples/layout-benchmark",
    ROOT / "examples/branch-benchmark",
    ROOT / "examples/vectorization-report",
    ROOT / "examples/false-sharing",
]
EXPECTED_FIXTURES = [
    ROOT / "exercises/processor-model/fixtures/programs/sum.asm",
    ROOT / "exercises/processor-model/fixtures/programs/overflow.asm",
    ROOT / "exercises/processor-model/fixtures/traces/pipeline-load-use.trace",
    ROOT / "exercises/processor-model/fixtures/traces/pipeline-branch.trace",
    ROOT / "exercises/processor-model/fixtures/traces/cache.trace",
    ROOT / "exercises/processor-model/fixtures/traces/coherence-false-sharing.trace",
    ROOT / "exercises/processor-model/fixtures/vm/config.json",
    ROOT / "exercises/processor-model/fixtures/vm/trace.txt",
]
LEGACY_PATHS = [
    ROOT / "docs/01-data-representation-and-arithmetic.md",
    ROOT / "docs/02-isa-assembly-and-program-execution.md",
    ROOT / "docs/03-performance-cpi-and-amdahl.md",
    ROOT / "docs/04-datapath-and-control.md",
    ROOT / "docs/05-pipeline-hazards-and-branching.md",
    ROOT / "docs/06-cache-locality-and-amat.md",
    ROOT / "docs/07-virtual-memory-and-tlb.md",
    ROOT / "docs/08-superscalar-out-of-order-and-memory-order.md",
    ROOT / "docs/09-simd-vectorization-and-data-layout.md",
    ROOT / "docs/10-multicore-coherence-and-false-sharing.md",
    ROOT / "reference/tiny-risc-isa.md",
]
EXPECTED_MODULES = {
    "__init__.py",
    "bits.py",
    "cache.py",
    "cli.py",
    "coherence.py",
    "control.py",
    "isa.py",
    "perf.py",
    "pipeline.py",
    "predictor.py",
    "rob.py",
    "vm.py",
}
IGNORED_PARTS = {
    ".git",
    ".venv",
    "workspace",
    "build",
    "dist",
    "target",
    "__pycache__",
}
OPTIONAL_REPOSITORY_SIBLINGS = {
    "c",
    "cpp",
    "unix-systems",
    "operating-systems",
    "guide-c",
    "guide-cpp",
    "guide-unix-systems",
    "guide-operating-systems",
}
FORBIDDEN_ARTIFACT_NAMES = {
    "APPLY.md",
    "CATALOG.md",
    "INTEGRATION.md",
    "repository-integration.md",
    "DELETION-LIST.txt",
    "REPORT.md",
}
ALLOWED_TOP_LEVEL = {
    ".git",
    ".gitignore",
    ".guide",
    "CONTRIBUTING.md",
    "LICENSE.md",
    "LICENSES",
    "Makefile",
    "README.md",
    "docs",
    "examples",
    "exercises",
    "prepare.sh",
    "reference",
    "scripts",
    "verify.sh",
}
CONCEPT_HEADINGS = ("## 학습 목표", "## 선행 개념", "## 연결 실습", "## 완료 기준")
EXERCISE_HEADINGS = ("## 목표", "## 완료 기준", "## 자기 설명", "## 검증")
MAPPING_HEADER = (
    "순서",
    "문서",
    "관찰 예제",
    "직접 수행",
    "수정 위치",
    "검증",
    "완료 뒤 비교·다음",
)
IMPLEMENTATION_INDEX_HEADER = ("번호", "파일·symbol", "먼저 고정하는 책임")
IMPLEMENTATION_WORD = "Implementation"
IMPLEMENTATION_ID = re.compile(r"(?:0|[1-9]\d*(?:-[1-9]\d*)?)")
IMPLEMENTATION_CANDIDATE = re.compile(
    r"\[" + IMPLEMENTATION_WORD + r"[^\]\r\n]*\]"
)
IMPLEMENTATION_MARKER = re.compile(
    r"\[" + IMPLEMENTATION_WORD + r" (0|[1-9]\d*(?:-[1-9]\d*)?)\]"
)
ANNOTATION_SCOPES = {
    "layout-benchmark": (
        ROOT / "examples/layout-benchmark",
        ROOT / "examples/layout-benchmark/README.md",
    ),
    "branch-benchmark": (
        ROOT / "examples/branch-benchmark",
        ROOT / "examples/branch-benchmark/README.md",
    ),
    "vectorization-report": (
        ROOT / "examples/vectorization-report",
        ROOT / "examples/vectorization-report/README.md",
    ),
    "false-sharing": (
        ROOT / "examples/false-sharing",
        ROOT / "examples/false-sharing/README.md",
    ),
    "processor-model": (
        ROOT / "exercises/processor-model/reference",
        ROOT / "exercises/processor-model/README.md",
    ),
}


def report(message: str) -> None:
    ERRORS.append(message)


def source_paths(pattern: str) -> list[Path]:
    return [
        path
        for path in ROOT.rglob(pattern)
        if not any(part in IGNORED_PARTS for part in path.relative_to(ROOT).parts)
    ]


def github_slug(text: str) -> str:
    text = re.sub(r"`([^`]*)`", r"\1", text).strip().lower()
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"[^\w\s가-힣-]", "", text)
    return re.sub(r"[\s-]+", "-", text).strip("-")


def headings(path: Path) -> set[str]:
    result: set[str] = set()
    counts: dict[str, int] = {}
    in_fence = False
    fence = ""
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.lstrip()
        if stripped.startswith(("```", "~~~")):
            marker = stripped[:3]
            if not in_fence:
                in_fence = True
                fence = marker
            elif marker == fence:
                in_fence = False
            continue
        if in_fence:
            continue
        match = re.match(r"^#{1,6}\s+(.+?)\s*#*\s*$", line)
        if match:
            base = github_slug(match.group(1))
            count = counts.get(base, 0)
            counts[base] = count + 1
            result.add(base if count == 0 else f"{base}-{count}")
    return result


def inline_code_ranges(text: str) -> list[tuple[int, int]]:
    ranges: list[tuple[int, int]] = []
    cursor = 0
    while cursor < len(text):
        start = text.find("`", cursor)
        if start < 0:
            break
        width = 1
        while start + width < len(text) and text[start + width] == "`":
            width += 1
        marker = "`" * width
        end = text.find(marker, start + width)
        if end < 0:
            break
        ranges.append((start, end + width))
        cursor = end + width
    return ranges


def markdown_link_targets(text: str) -> list[str]:
    pattern = re.compile(r"(?<!!)\[[^\]]+\]\(([^)]+)\)")
    code_ranges = inline_code_ranges(text)
    return [
        match.group(1)
        for match in pattern.finditer(text)
        if not any(start <= match.start() < end for start, end in code_ranges)
    ]


def table_cells(line: str) -> list[str] | None:
    stripped = line.strip()
    if not stripped.startswith("|") or not stripped.endswith("|"):
        return None
    return [cell.strip() for cell in stripped[1:-1].split("|")]


def fenced_code_lines(text: str) -> list[str]:
    result: list[str] = []
    in_fence = False
    fence = ""
    for line in text.splitlines():
        stripped = line.lstrip()
        if stripped.startswith(("```", "~~~")):
            marker = stripped[:3]
            if not in_fence:
                in_fence = True
                fence = marker
            elif marker == fence:
                in_fence = False
            continue
        if in_fence:
            result.append(line)
    return result


def check_expected_tree() -> None:
    global CHECKS
    required_files = [
        ROOT / "README.md",
        ROOT / "Makefile",
        ROOT / "prepare.sh",
        ROOT / "verify.sh",
        ROOT / "scripts/new-workspace.sh",
        ROOT / "scripts/atomic_directory_publish.py",
        ROOT / "scripts/layout-manifest.txt",
        ROOT / "scripts/test-validator.py",
        ROOT / "scripts/test-prepare-marker.py",
        ROOT / "scripts/test-runner-safety.py",
        ROOT / "scripts/test-workspace-tools.py",
        ROOT / "scripts/test-exercise-quality.py",
        ROOT / "scripts/test-verify-preflight.py",
        ROOT / "scripts/tree-fingerprint.py",
        ROOT / "scripts/run_with_timeout.py",
        ROOT / "scripts/validate_docs.py",
        *EXPECTED_DOCUMENTS,
        *EXPECTED_REFERENCES,
    ]
    for path in required_files:
        CHECKS += 1
        if not path.is_file():
            report(f"필수 파일을 찾을 수 없습니다: {path.relative_to(ROOT)}")

    actual_documents = {
        path.resolve()
        for path in (ROOT / "docs").rglob("*.md")
        if not any(part in IGNORED_PARTS for part in path.relative_to(ROOT).parts)
    }
    expected_documents = {path.resolve() for path in EXPECTED_DOCUMENTS}
    CHECKS += 1
    if actual_documents != expected_documents:
        missing = sorted(path.relative_to(ROOT).as_posix() for path in expected_documents - actual_documents)
        extra = sorted(path.relative_to(ROOT).as_posix() for path in actual_documents - expected_documents)
        report(f"docs 정본 구성이 다릅니다: missing={missing}, extra={extra}")

    for path in LEGACY_PATHS:
        CHECKS += 1
        if path.exists() or path.is_symlink():
            report(f"이전 경로가 남았습니다: {path.relative_to(ROOT)}")

    actual_top_level = {path.name for path in ROOT.iterdir()}
    CHECKS += 1
    unexpected_top_level = sorted(actual_top_level - ALLOWED_TOP_LEVEL)
    if unexpected_top_level:
        report(f"예상 밖 최상위 경로가 있습니다: {unexpected_top_level}")

    for directory in EXPECTED_EXAMPLES:
        CHECKS += 1
        required = [directory / "README.md", directory / "Makefile"]
        if not directory.is_dir() or not all(path.is_file() for path in required):
            report(f"예제 구성이 불완전합니다: {directory.relative_to(ROOT)}")

    exercise = ROOT / "exercises/processor-model"
    required_exercise = [
        exercise / "README.md",
        exercise / "Makefile",
        exercise / "check.py",
        exercise / "tests/test_processor_model.py",
        exercise / "skeleton/processor-model.py",
        exercise / "reference/processor-model.py",
    ]
    for path in [*required_exercise, *EXPECTED_FIXTURES]:
        CHECKS += 1
        if not path.is_file():
            report(f"실습 파일을 찾을 수 없습니다: {path.relative_to(ROOT)}")

    for implementation in ("skeleton", "reference"):
        package = exercise / implementation / "processor_model"
        CHECKS += 1
        existing = {path.name for path in package.glob("*.py")}
        if existing != EXPECTED_MODULES:
            missing = sorted(EXPECTED_MODULES - existing)
            extra = sorted(existing - EXPECTED_MODULES)
            report(
                f"{implementation} package 구성이 다릅니다: "
                f"missing={missing}, extra={extra}"
            )


def check_markdown() -> None:
    global CHECKS
    forbidden_fragments = (
        "../../../scripts/new-workspace.sh .",
        "python3 computer-architecture/exercises/",
        " computer-architecture/exercises/",
    )

    for path in sorted(source_paths("*.md")):
        CHECKS += 1
        relative = path.relative_to(ROOT)
        text = path.read_text(encoding="utf-8")
        lines = text.splitlines()
        if not lines or not lines[0].startswith("# "):
            report(f"첫 줄에 H1 제목이 없습니다: {relative}")
        if sum(line.startswith("# ") for line in lines) != 1:
            report(f"H1 제목은 하나여야 합니다: {relative}")

        for fragment in forbidden_fragments:
            if fragment in text:
                report(f"이전 실행 경로가 남았습니다: {relative} -> {fragment}")

        in_fence = False
        fence = ""
        visible: list[str] = []
        raw_visible: list[str] = []
        for number, line in enumerate(lines, 1):
            stripped = line.lstrip()
            if stripped.startswith(("```", "~~~")):
                marker = stripped[:3]
                if not in_fence:
                    in_fence = True
                    fence = marker
                elif marker == fence:
                    in_fence = False
                continue
            if in_fence:
                continue
            raw_visible.append(line)
            visible.append(re.sub(r"`[^`]*`", "", line))
            if re.search(r"(?<!니)다[.”’\"]?\s*$", line):
                report(f"경어체가 아닌 문장 종결입니다: {relative}:{number}")
        if in_fence:
            report(f"닫히지 않은 코드 블록이 있습니다: {relative}")

        for raw_target in markdown_link_targets("\n".join(raw_visible)):
            target = raw_target.strip().split()[0].strip("<>")
            if target.startswith(("http://", "https://", "mailto:", "data:")):
                continue
            decoded = unquote(target)
            file_part, _, fragment = decoded.partition("#")
            resolved = path if not file_part else (path.parent / file_part).resolve()
            try:
                resolved.relative_to(ROOT.parent)
            except ValueError:
                report(f"허용된 저장소 범위 밖을 가리킵니다: {relative} -> {target}")
                continue
            if not resolved.exists():
                try:
                    repository_relative = resolved.relative_to(ROOT.parent)
                except ValueError:
                    repository_relative = PurePosixPath()
                if (
                    repository_relative.parts
                    and repository_relative.parts[0] in OPTIONAL_REPOSITORY_SIBLINGS
                ):
                    continue
                report(f"대상이 없는 링크입니다: {relative} -> {target}")
                continue
            if fragment and resolved.suffix.lower() == ".md":
                if fragment.lower() not in headings(resolved):
                    report(f"대상이 없는 문서 anchor입니다: {relative} -> {target}")


def check_python() -> None:
    global CHECKS
    for path in sorted(source_paths("*.py")):
        CHECKS += 1
        relative = path.relative_to(ROOT)
        text = path.read_text(encoding="utf-8")
        try:
            ast.parse(text, filename=str(relative))
        except SyntaxError as exc:
            report(f"Python 문법 오류입니다: {relative}:{exc.lineno}: {exc.msg}")

    reference_root = ROOT / "exercises/processor-model/reference"
    for path in reference_root.rglob("*.py"):
        CHECKS += 1
        text = path.read_text(encoding="utf-8")
        if "NotImplementedError" in text or "TODO" in text:
            report(f"reference에 미완성 표시가 남았습니다: {path.relative_to(ROOT)}")

    skeleton_root = ROOT / "exercises/processor-model/skeleton/processor_model"
    skeleton_text = "\n".join(
        path.read_text(encoding="utf-8") for path in skeleton_root.glob("*.py")
    )
    CHECKS += 1
    if "NotImplementedError" not in skeleton_text:
        report("skeleton에 직접 구현할 상태 전이가 남아 있지 않습니다")


def check_scripts_and_sources() -> None:
    global CHECKS
    executable_paths = [
        ROOT / "prepare.sh",
        ROOT / "verify.sh",
        ROOT / "scripts/new-workspace.sh",
        ROOT / "scripts/new-workspace.py",
        ROOT / "scripts/atomic_directory_publish.py",
        ROOT / "scripts/check-sanitizers.sh",
        ROOT / "scripts/test-validator.py",
        ROOT / "scripts/test-prepare-marker.py",
        ROOT / "scripts/test-runner-safety.py",
        ROOT / "scripts/test-workspace-tools.py",
        ROOT / "scripts/test-exercise-quality.py",
        ROOT / "scripts/test-verify-preflight.py",
        ROOT / "scripts/tree-fingerprint.py",
        ROOT / "scripts/run_with_timeout.py",
        ROOT / "scripts/validate_docs.py",
        ROOT / "examples/vectorization-report/report.sh",
        ROOT / "exercises/processor-model/reference/processor-model.py",
        ROOT / "exercises/processor-model/skeleton/processor-model.py",
    ]
    for path in executable_paths:
        CHECKS += 1
        if not path.is_file():
            continue
        if not path.stat().st_mode & stat.S_IXUSR:
            report(f"실행 권한이 없습니다: {path.relative_to(ROOT)}")
        data = path.read_bytes()
        if b"\r\n" in data:
            report(f"CRLF 줄 끝을 사용합니다: {path.relative_to(ROOT)}")
        if not data.startswith(b"#!"):
            report(f"실행 파일에 shebang이 없습니다: {path.relative_to(ROOT)}")

    for path in source_paths("*"):
        relative = path.relative_to(ROOT)
        CHECKS += 1
        if path.is_symlink():
            report(f"source tree에 symlink가 있습니다: {relative}")
            continue
        if not path.is_file():
            continue
        if path.stat().st_size == 0:
            report(f"빈 파일이 남았습니다: {relative}")
        if path.suffix in {".pyc", ".o"}:
            report(f"생성물이 source tree에 남았습니다: {relative}")
        data = path.read_bytes()
        if b"\r\n" in data:
            report(f"CRLF 줄 끝을 사용합니다: {relative}")
        try:
            data.decode("utf-8")
        except UnicodeDecodeError:
            report(f"UTF-8로 읽을 수 없는 source 파일입니다: {relative}")


def section(text: str, heading: str) -> str:
    marker = text.find(heading)
    if marker < 0:
        return ""
    start = marker + len(heading)
    following = re.search(r"^##\s+", text[start:], flags=re.MULTILINE)
    return text[start:] if following is None else text[start : start + following.start()]


def check_pedagogy() -> None:
    global CHECKS
    completion_owners: dict[str, Path] = {}
    for path in EXPECTED_DOCUMENTS[1:]:
        text = path.read_text(encoding="utf-8") if path.is_file() else ""
        positions: list[int] = []
        for heading in CONCEPT_HEADINGS:
            CHECKS += 1
            if text.count(heading) != 1:
                report(f"개념 문서 제목은 정확히 한 번이어야 합니다: {path.relative_to(ROOT)} -> {heading}")
            positions.append(text.find(heading))
        if positions != sorted(positions) or any(value < 0 for value in positions):
            report(f"개념 문서 학습 계약 순서가 다릅니다: {path.relative_to(ROOT)}")
        completion = section(text, "## 완료 기준")
        if len(re.findall(r"^-\s+\S", completion, flags=re.MULTILINE)) < 3:
            report(f"개념 문서 완료 기준은 관찰 가능한 항목 3개 이상이어야 합니다: {path.relative_to(ROOT)}")
        normalized_completion = " ".join(completion.split())
        if normalized_completion in completion_owners:
            report(
                "개념 문서 완료 기준을 복사했습니다: "
                f"{path.relative_to(ROOT)}, {completion_owners[normalized_completion].relative_to(ROOT)}"
            )
        completion_owners[normalized_completion] = path

    path = ROOT / "exercises/processor-model/README.md"
    text = path.read_text(encoding="utf-8") if path.is_file() else ""
    positions = []
    for heading in EXERCISE_HEADINGS:
        CHECKS += 1
        if text.count(heading) != 1:
            report(f"실습 제목은 정확히 한 번이어야 합니다: {heading}")
        positions.append(text.find(heading))
    if positions != sorted(positions) or any(value < 0 for value in positions):
        report("실습 학습 계약 순서가 목표→완료 기준→자기 설명→검증과 다릅니다")
    if len(re.findall(r"^-\s+\S", section(text, "## 완료 기준"), flags=re.MULTILINE)) < 3:
        report("실습 완료 기준은 관찰 가능한 항목 3개 이상이어야 합니다")
    questions = re.findall(r"^-\s+(.+\?)\s*$", section(text, "## 자기 설명"), flags=re.MULTILINE)
    if len(questions) < 2 or len(set(questions)) != len(questions):
        report("실습 자기 설명에는 서로 다른 질문 2개 이상이 필요합니다")

    roadmap_path = ROOT / "docs/00-roadmap.md"
    roadmap = roadmap_path.read_text(encoding="utf-8") if roadmap_path.is_file() else ""
    roadmap_requirements = (
        "## 대상 독자",
        "## 선행지식",
        "## 완료 후 할 수 있어야 하는 일",
        "## 지원 환경",
        "필수 경로",
        "선택 경로",
        "## 문서와 실습의 대응",
        "## 완료 기준",
        "## 범위 밖",
        "## 자동 검증의 한계",
    )
    for phrase in roadmap_requirements:
        CHECKS += 1
        if phrase not in roadmap:
            report(f"로드맵 학습 계약이 없습니다: {phrase}")


def check_learning_mapping() -> None:
    global CHECKS
    def mapping_rows(path: Path, label: str) -> list[list[str]]:
        text = path.read_text(encoding="utf-8") if path.is_file() else ""
        lines = text.splitlines()
        tables: list[list[list[str]]] = []
        for index, line in enumerate(lines):
            if table_cells(line) != list(MAPPING_HEADER):
                continue
            separator = table_cells(lines[index + 1]) if index + 1 < len(lines) else None
            if separator is None or len(separator) != len(MAPPING_HEADER) or not all(
                re.fullmatch(r":?-{3,}:?", cell) for cell in separator
            ):
                report(f"{label} canonical 학습 순서 표의 separator가 올바르지 않습니다")
            rows: list[list[str]] = []
            cursor = index + 2
            while cursor < len(lines):
                candidate = table_cells(lines[cursor])
                if candidate is None or len(candidate) != len(MAPPING_HEADER):
                    break
                rows.append(candidate)
                cursor += 1
            tables.append(rows)
        if len(tables) != 1:
            report(f"{label} canonical 학습 순서 표가 정확히 한 번이 아닙니다: {len(tables)}개")
        return tables[0] if tables else []

    def normalized_targets(owner: Path, row: list[str]) -> set[str]:
        result: set[str] = set()
        for raw_target in markdown_link_targets(" | ".join(row)):
            target = unquote(raw_target.strip().split()[0].strip("<>"))
            if target.startswith(("http://", "https://", "mailto:", "data:")):
                continue
            target_path = target.split("#", 1)[0]
            if not target_path:
                continue
            candidate = (owner.parent / target_path).resolve()
            try:
                result.add(candidate.relative_to(ROOT).as_posix())
            except ValueError:
                continue
        return result

    readme_path = ROOT / "README.md"
    roadmap_path = ROOT / "docs/00-roadmap.md"
    mappings = (
        ("README", readme_path, mapping_rows(readme_path, "README"), True),
        ("roadmap", roadmap_path, mapping_rows(roadmap_path, "roadmap"), False),
    )
    CHECKS += len(mappings)
    valid = True
    for label, _, rows, _ in mappings:
        if len(rows) != 10:
            report(f"{label} canonical 학습 순서 표는 10행이어야 합니다: {len(rows)}행")
            valid = False
    if not valid:
        return

    example_targets_by_stage = {
        1: set(),
        2: set(),
        3: {"examples/layout-benchmark/README.md"},
        4: set(),
        5: {"examples/branch-benchmark/README.md"},
        6: {"examples/layout-benchmark/README.md"},
        7: set(),
        8: set(),
        9: {"examples/vectorization-report/README.md"},
        10: {"examples/false-sharing/README.md"},
    }
    exercise_target = "exercises/processor-model/README.md"
    example_targets = {
        directory.relative_to(ROOT).as_posix() + "/README.md"
        for directory in EXPECTED_EXAMPLES
    }
    modules = {
        1: "bits.py",
        2: "isa.py",
        3: "perf.py",
        4: "control.py",
        5: "pipeline.py",
        6: "cache.py",
        7: "vm.py",
        8: "{predictor,rob}.py",
        10: "coherence.py",
    }
    for label, owner, rows, require_exercise in mappings:
        for position, (row, document) in enumerate(zip(rows, EXPECTED_DOCUMENTS[1:]), 1):
            CHECKS += 1
            if any(not cell for cell in row):
                report(f"{label} 학습 순서 {position:02d}행에 빈 field가 있습니다")
            try:
                order = int(row[0])
            except ValueError:
                order = -1
            if order != position:
                report(f"{label} 학습 순서 번호가 다릅니다: {row[0]} != {position:02d}")

            targets_by_cell = [normalized_targets(owner, [cell]) for cell in row]
            targets = set().union(*targets_by_cell)
            expected_target = document.relative_to(ROOT).as_posix()
            if targets_by_cell[1] != {expected_target}:
                report(
                    f"{label} 학습 순서의 문서 대응이 다릅니다: "
                    f"{position:02d} -> {expected_target}"
                )
            actual_examples = targets_by_cell[2]
            if actual_examples != example_targets_by_stage[position]:
                report(
                    f"{label} 학습 순서의 관찰 예제 대응이 다릅니다: "
                    f"{position:02d} -> {sorted(actual_examples)}"
                )
            if not example_targets_by_stage[position] and row[2] != "—":
                report(f"{label} Stage {position:02d}의 관찰 예제 없음 표기가 다릅니다")
            misplaced_examples = (
                set().union(*(targets_by_cell[index] for index in range(len(row)) if index != 2))
                & example_targets
            )
            if misplaced_examples:
                report(
                    f"{label} Stage {position:02d}의 관찰 예제 링크가 다른 column에 있습니다: "
                    f"{sorted(misplaced_examples)}"
                )
            if require_exercise:
                if position == 9:
                    if exercise_target in targets:
                        report("README Stage 09가 source 구현 exercise로 연결됐습니다")
                else:
                    if targets_by_cell[3] != {exercise_target}:
                        report(f"README Stage {position:02d} 직접 수행에 processor-model 연결이 없습니다")
                    if any(
                        exercise_target in targets_by_cell[index]
                        for index in range(len(row))
                        if index != 3
                    ):
                        report(f"README Stage {position:02d}의 processor-model 링크가 다른 column에 있습니다")

            expected_command = (
                f"make stage-{position:02d}"
                if position == 9
                else f"make stage-{position:02d} EXERCISE_IMPL=workspace"
            )
            if re.findall(r"`([^`]+)`", row[5]) != [expected_command]:
                report(f"{label} 학습 순서의 Stage {position:02d} 검증 명령이 다릅니다")
            if position == 9:
                if row[4] != "—" or "증거" not in row[3] or "증거" not in row[6]:
                    report(f"{label} Stage 09가 수정 없는 관찰 증거 checkpoint로 표시되지 않았습니다")
            else:
                expected_workspace = (
                    "exercises/processor-model/workspace/processor_model/" + modules[position]
                )
                expected_reference = (
                    "exercises/processor-model/reference/processor_model/" + modules[position]
                )
                if re.findall(r"`([^`]+)`", row[4]) != [expected_workspace]:
                    report(f"{label} Stage {position:02d} 수정 위치가 canonical workspace가 아닙니다")
                if re.findall(r"`([^`]+)`", row[6]) != [expected_reference]:
                    report(f"{label} Stage {position:02d} 완료 뒤 reference 대응이 다릅니다")
            if position < 10 and f"→ {position + 1:02d}" not in row[6]:
                report(f"{label} Stage {position:02d}에서 다음 단계가 명확하지 않습니다")
            if position == 10 and "전체 workspace" not in row[6]:
                report(f"{label} Stage 10의 종료점이 명확하지 않습니다")

    learner_entry_documents = [
        readme_path,
        roadmap_path,
        *EXPECTED_DOCUMENTS[1:],
        ROOT / "exercises/processor-model/README.md",
    ]
    for document in learner_entry_documents:
        CHECKS += 1
        document_text = document.read_text(encoding="utf-8") if document.is_file() else ""
        executable_text = "\n".join(fenced_code_lines(document_text))
        forbidden_patterns = {
            "EXERCISE_IMPL=skeleton": re.compile(
                r"\bEXERCISE_IMPL\s*=\s*(?:skeleton\b|['\"]skeleton['\"])"
            ),
            "skeleton processor source": re.compile(
                r"\b(?:exercises/processor-model/)?skeleton/"
                r"(?:processor_model/|processor-model\.py\b)"
            ),
        }
        forbidden = [
            name for name, pattern in forbidden_patterns.items() if pattern.search(executable_text)
        ]
        if forbidden:
            report(
                "학습 문서가 repository-owned skeleton을 직접 수정·검사합니다: "
                f"{document.relative_to(ROOT)} -> {forbidden}"
            )


def annotation_scope(path: Path) -> str | None:
    for name, (root, readme) in ANNOTATION_SCOPES.items():
        if path == readme or path == root or root in path.parents:
            return name
    return None


def annotation_key(identifier: str) -> tuple[int, int]:
    parts = [int(part) for part in identifier.split("-")]
    return (parts[0], 0 if len(parts) == 1 else parts[1])


def implementation_index(path: Path, scope: str) -> list[tuple[str, str]]:
    text = path.read_text(encoding="utf-8") if path.is_file() else ""
    body = section(text, "## 권장 구현 순서")
    lines = body.splitlines()
    tables: list[list[list[str]]] = []
    for index, line in enumerate(lines):
        if table_cells(line) != list(IMPLEMENTATION_INDEX_HEADER):
            continue
        separator = table_cells(lines[index + 1]) if index + 1 < len(lines) else None
        if separator is None or len(separator) != len(IMPLEMENTATION_INDEX_HEADER) or not all(
            re.fullmatch(r":?-{3,}:?", cell) for cell in separator
        ):
            report(f"{scope} scope의 권장 구현 순서 표 separator가 올바르지 않습니다")
        rows: list[list[str]] = []
        cursor = index + 2
        while cursor < len(lines):
            cells = table_cells(lines[cursor])
            if cells is None:
                break
            rows.append(cells)
            cursor += 1
        tables.append(rows)
    if len(tables) != 1:
        report(f"{scope} scope의 권장 구현 순서 표가 정확히 한 번이 아닙니다: {len(tables)}개")

    result: list[tuple[str, str]] = []
    for cells in tables[0] if tables else []:
        if len(cells) != len(IMPLEMENTATION_INDEX_HEADER) or any(not cell for cell in cells):
            report(f"{scope} scope의 권장 구현 순서 행은 비어 있지 않은 3개 field여야 합니다")
            continue
        candidate = cells[0].strip().strip("`")
        if IMPLEMENTATION_ID.fullmatch(candidate):
            result.append((candidate, cells[1]))
        else:
            report(f"{scope} scope의 권장 구현 순서 번호가 올바르지 않습니다: {cells[0]}")
    return result


def annotation_target_matches(path: Path, number: int, target: str) -> bool:
    target_match = re.match(r"^`([^`]+)`(?:\s|$)", target)
    if target_match is None:
        return False
    indexed_path, separator, symbol = target_match.group(1).partition("::")
    if indexed_path != path.name:
        return False
    if not separator or not symbol:
        return False
    lines = path.read_text(encoding="utf-8").splitlines()
    if path.suffix == ".py":
        try:
            tree = ast.parse("\n".join(lines), filename=str(path))
        except SyntaxError:
            return False
        declarations: dict[str, int] = {}

        def visit(body: list[ast.stmt], prefix: str = "") -> None:
            for node in body:
                name = getattr(node, "name", None)
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    qualified = f"{prefix}.{name}" if prefix else name
                    decorators = [decorator.lineno for decorator in node.decorator_list]
                    declarations[qualified] = min([node.lineno, *decorators])
                    if isinstance(node, ast.ClassDef):
                        visit(node.body, qualified)
                elif isinstance(node, (ast.Assign, ast.AnnAssign)):
                    targets = node.targets if isinstance(node, ast.Assign) else [node.target]
                    for assignment_target in targets:
                        if isinstance(assignment_target, ast.Name):
                            qualified = (
                                f"{prefix}.{assignment_target.id}"
                                if prefix
                                else assignment_target.id
                            )
                            declarations[qualified] = node.lineno

        visit(tree.body)
        return declarations.get(symbol) == number + 1

    following = [line.strip() for line in lines[number:] if line.strip()]
    if not following:
        return False
    declaration = following[0]
    if path.name == "Makefile":
        return re.match(rf"^{re.escape(symbol)}\s*:", declaration) is not None
    if path.suffix in {".c", ".h"}:
        return any(
            (
                re.search(rf"\b{re.escape(symbol)}\s*\(", declaration),
                re.match(rf"^(?:struct|union|enum)\s+{re.escape(symbol)}\b", declaration),
            )
        )
    return re.search(rf"\b{re.escape(symbol)}\b", declaration) is not None


def check_implementation_annotations() -> None:
    global CHECKS
    found: dict[str, list[tuple[str, Path, int]]] = {
        name: [] for name in ANNOTATION_SCOPES
    }
    for path in sorted(source_paths("*")):
        if not path.is_file():
            continue
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except UnicodeDecodeError:
            continue
        for number, line in enumerate(lines, 1):
            for candidate in IMPLEMENTATION_CANDIDATE.findall(line):
                CHECKS += 1
                match = IMPLEMENTATION_MARKER.fullmatch(candidate)
                if match is None:
                    report(
                        f"잘못된 {IMPLEMENTATION_WORD} annotation 형식입니다: "
                        f"{path.relative_to(ROOT)}:{number} -> {candidate}"
                    )
                    continue
                scope = annotation_scope(path)
                if scope is None:
                    report(
                        f"허용되지 않은 {IMPLEMENTATION_WORD} annotation 위치입니다: "
                        f"{path.relative_to(ROOT)}:{number}"
                    )
                    continue

                _, owner_readme = ANNOTATION_SCOPES[scope]
                stripped = line.lstrip()
                comment_ok = (
                    (path == owner_readme and path.suffix == ".md")
                    or (path.name == "Makefile" and stripped.startswith("#"))
                    or (path.suffix in {".py", ".sh"} and stripped.startswith("#"))
                    or (
                        path.suffix in {".c", ".h"}
                        and stripped.startswith(("//", "/*", "*"))
                    )
                )
                if not comment_ok:
                    report(
                        f"{IMPLEMENTATION_WORD} anchor가 comment 또는 owning README에 없습니다: "
                        f"{path.relative_to(ROOT)}:{number}"
                    )
                found[scope].append((match.group(1), path, number))

    for name, annotations in found.items():
        _, readme = ANNOTATION_SCOPES[name]
        CHECKS += 1
        readme_text = readme.read_text(encoding="utf-8") if readme.is_file() else ""
        if readme_text.count("## 권장 구현 순서") != 1:
            report(f"{name} scope의 권장 구현 순서가 정확히 한 번이 아닙니다")

        counts: dict[str, int] = {}
        for identifier, _, _ in annotations:
            counts[identifier] = counts.get(identifier, 0) + 1
        duplicates = sorted(identifier for identifier, count in counts.items() if count != 1)
        if duplicates:
            report(f"{name} scope에 중복된 {IMPLEMENTATION_WORD} annotation이 있습니다: {duplicates}")

        top = sorted(
            int(identifier)
            for identifier in counts
            if "-" not in identifier and identifier != "0"
        )
        CHECKS += 1
        if not top or top != list(range(1, max(top, default=0) + 1)):
            report(f"{name} scope의 {IMPLEMENTATION_WORD} top-level 번호가 연속하지 않습니다: {top}")

        children: dict[int, list[int]] = {}
        for identifier in counts:
            if "-" not in identifier:
                continue
            parent, child = (int(part) for part in identifier.split("-"))
            children.setdefault(parent, []).append(child)
        for parent, child_ids in children.items():
            ordered_children = sorted(child_ids)
            if str(parent) not in counts:
                report(f"{name} scope의 substep parent가 없습니다: {parent}")
            if ordered_children != list(range(1, max(ordered_children) + 1)):
                report(
                    f"{name} scope의 {parent} substep 번호가 연속하지 않습니다: "
                    f"{ordered_children}"
                )

        source_ids = sorted(counts, key=annotation_key)
        index_rows = implementation_index(readme, name)
        index_ids = [identifier for identifier, _ in index_rows]
        CHECKS += 1
        if index_ids != source_ids:
            report(
                f"{name} scope의 README index와 source anchor가 다릅니다: "
                f"index={index_ids}, source={source_ids}"
            )
        index_targets = dict(index_rows)
        for identifier, path, number in annotations:
            CHECKS += 1
            target = index_targets.get(identifier, "")
            if not annotation_target_matches(path, number, target):
                report(
                    f"{name} scope의 README index 위치와 source anchor가 다릅니다: "
                    f"{identifier} -> {target!r}, {path.relative_to(ROOT)}:{number}"
                )


def check_layout_manifest() -> None:
    global CHECKS
    manifest = ROOT / "scripts/layout-manifest.txt"
    CHECKS += 1
    if not manifest.is_file():
        return
    expected = {
        line.strip()
        for line in manifest.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.startswith("#")
    }
    actual: set[str] = set()
    for path in ROOT.rglob("*"):
        relative = path.relative_to(ROOT)
        if any(part in IGNORED_PARTS or part in {".git", ".guide"} for part in relative.parts):
            continue
        if path.is_file() or path.is_symlink():
            actual.add(relative.as_posix())
    if actual != expected:
        missing = sorted(expected - actual)
        extra = sorted(actual - expected)
        report(f"source path manifest가 다릅니다: missing={missing}, extra={extra}")


def check_runtime_contract() -> None:
    global CHECKS
    files_and_phrases = {
        ROOT / "prepare.sh": (
            "Python 3.12",
            ".guide/$GUIDE_ID",
            "PREPARE RESULT: PASS",
            "source_fingerprint",
            "index_fingerprint",
        ),
        ROOT / "verify.sh": (
            "Python 3.12",
            "skipped=0",
            "VERIFY LOG:",
            "RESULT: PASS",
            "scripts/test-validator.py",
        ),
        ROOT / "Makefile": ("prepare:", "check:", "verify:", "clean:"),
        ROOT / "reference/version-baseline.md": (
            "Python >= 3.12",
            "v20260120",
            "판본 `092`",
            "판본 `050`",
        ),
    }
    for path, phrases in files_and_phrases.items():
        text = path.read_text(encoding="utf-8") if path.is_file() else ""
        for phrase in phrases:
            CHECKS += 1
            if phrase not in text:
                report(f"실행·판본 계약이 없습니다: {path.relative_to(ROOT)} -> {phrase}")


def check_excluded_artifacts_and_comments() -> None:
    global CHECKS
    comment_prefixes = {
        ".py": ("#",),
        ".sh": ("#",),
        ".c": ("//", "/*"),
        ".h": ("//", "/*"),
    }
    for path in sorted(ROOT.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(ROOT)
        if any(part in IGNORED_PARTS for part in relative.parts):
            continue
        CHECKS += 1
        if path.name in FORBIDDEN_ARTIFACT_NAMES or re.fullmatch(
            r"integrate.*\.py", path.name, flags=re.IGNORECASE
        ):
            report(f"통합 전용 파일이 남았습니다: {relative}")

        prefixes = comment_prefixes.get(path.suffix)
        if prefixes is None:
            continue
        for number, line in enumerate(
            path.read_text(encoding="utf-8").splitlines(), start=1
        ):
            stripped = line.lstrip()
            if stripped.startswith("#!"):
                continue
            prefix = next(
                (candidate for candidate in prefixes if stripped.startswith(candidate)),
                None,
            )
            if prefix is None:
                continue
            if prefix == "#" and len(stripped) > 1 and not stripped[1].isspace():
                continue
            comment = stripped[len(prefix) :].strip()
            if re.search(r"[A-Za-z]", comment) and not re.search(r"[가-힣]", comment):
                report(f"영문으로만 작성한 코드 주석입니다: {relative}:{number}")


def check_navigation_and_boundaries() -> None:
    global CHECKS
    readme_path = ROOT / "README.md"
    roadmap_path = ROOT / "docs/00-roadmap.md"
    readme = readme_path.read_text(encoding="utf-8") if readme_path.is_file() else ""
    roadmap = roadmap_path.read_text(encoding="utf-8") if roadmap_path.is_file() else ""
    for document in EXPECTED_DOCUMENTS[1:]:
        target = document.relative_to(ROOT).as_posix()
        CHECKS += 2
        if target not in readme:
            report(f"README 읽는 순서에 문서가 없습니다: {target}")
        roadmap_target = Path(target).relative_to("docs").as_posix()
        if roadmap_target not in roadmap:
            report(f"로드맵에 문서가 없습니다: {roadmap_target}")

    boundary_requirements = {
        ROOT / "docs/00-roadmap.md": (
            "컴퓨터 구조가 소유하는 범위",
            "운영체제 가이드가 소유하는 범위",
            "언어·동시성 가이드가 소유하는 범위",
        ),
        ROOT / "docs/03-memory-hierarchy/07-address-translation-and-tlb.md": (
            "운영체제 정책과의 경계",
            "TLB 실패와 변환 예외를 구분합니다",
        ),
        ROOT / "docs/04-parallel-execution/08-superscalar-out-of-order-and-speculation.md": (
            "ISA 메모리 순서",
            "언어·동시성 가이드",
        ),
    }
    for path, phrases in boundary_requirements.items():
        text = path.read_text(encoding="utf-8") if path.is_file() else ""
        for phrase in phrases:
            CHECKS += 1
            if phrase not in text:
                report(f"범위 계약 문구가 없습니다: {path.relative_to(ROOT)} -> {phrase}")

    exercise_path = ROOT / "exercises/processor-model/README.md"
    exercise_readme = exercise_path.read_text(encoding="utf-8") if exercise_path.is_file() else ""
    CHECKS += 2
    if "spec/tiny-risc-isa.md" not in exercise_readme:
        report("processor-model README가 실습 ISA 명세를 가리키지 않습니다")
    if "../../scripts/new-workspace.sh ." not in exercise_readme:
        report("processor-model README의 workspace 생성 경로가 올바르지 않습니다")


def main() -> int:
    check_expected_tree()
    check_layout_manifest()
    check_markdown()
    check_python()
    check_scripts_and_sources()
    check_excluded_artifacts_and_comments()
    check_navigation_and_boundaries()
    check_pedagogy()
    check_learning_mapping()
    check_implementation_annotations()
    check_runtime_contract()
    if ERRORS:
        print(f"컴퓨터 구조 저장소 검사 실패: {len(ERRORS)}건", file=sys.stderr)
        for error in ERRORS:
            print(f"- {error}", file=sys.stderr)
        return 1
    print(f"컴퓨터 구조 저장소 검사 통과: {CHECKS}개 항목")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
