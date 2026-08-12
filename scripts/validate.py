#!/usr/bin/env python3
"""Validate exact layout, learning contracts, links, source hygiene, and pins."""

from __future__ import annotations

import ast
import io
import os
import re
import subprocess
import sys
import tokenize
import unicodedata
from pathlib import Path
from urllib.parse import unquote

sys.dont_write_bytecode = True
from repository_state import source_manifest

ROOT = Path(os.environ.get("GUIDE_ROOT", Path(__file__).resolve().parents[1])).resolve()
ERRORS: list[str] = []
LAYOUT = ROOT / "scripts/layout-manifest.txt"

DOCS = {
    "docs/00-roadmap.md",
    "docs/01-link-and-path/01-layers-encapsulation-and-path.md",
    "docs/01-link-and-path/02-ethernet-mac-and-switching.md",
    "docs/01-link-and-path/03-arp-and-neighbor-discovery.md",
    "docs/02-internetworking/01-ip-addressing-subnets-and-lpm.md",
    "docs/02-internetworking/02-ip-forwarding-mtu-and-icmp.md",
    "docs/02-internetworking/03-nat-connection-tracking-and-firewalls.md",
    "docs/02-internetworking/04-routing-algorithms-and-protocols.md",
    "docs/03-transport/01-udp-and-tcp-service-contracts.md",
    "docs/03-transport/02-tcp-connection-state-and-sequences.md",
    "docs/03-transport/03-retransmission-rtt-and-sliding-windows.md",
    "docs/03-transport/04-flow-and-congestion-control.md",
    "docs/04-application-security-and-evidence/01-dns-http-tls-and-quic.md",
    "docs/04-application-security-and-evidence/02-network-failure-localization.md",
    "docs/90-standards-map.md",
}
CONCEPT_DOCS = DOCS - {"docs/00-roadmap.md", "docs/90-standards-map.md"}
EXERCISES = {
    "exercises/linux-routing-nat/README.md",
    "exercises/packet-observation/README.md",
    "exercises/path-diagnosis/README.md",
    "exercises/protocol-inspector/README.md",
}
CONCEPT_SECTIONS = ("학습 목표", "선행 개념", "연결 실습", "완료 기준")
EXERCISE_SECTIONS = ("목표", "완료 기준", "자기 설명", "검증")
TEXT_SUFFIXES = {".md", ".py", ".sh", ".txt", ".json", ".hex"}
GENERATED_NAMES = {"__pycache__", ".pytest_cache", ".guide", ".verify"}
SKIPPED_TREE_NAMES = GENERATED_NAMES | {".git", "workspace"}
ROOT_MAPPING_COLUMNS = (
    "순서",
    "문서",
    "관찰 예제",
    "직접 수행",
    "수정 위치",
    "검증",
    "완료 뒤 비교·다음",
)
ROOT_MAPPING_MATERIALS = {
    "examples/window-model/README.md",
    "exercises/linux-routing-nat/README.md",
    "exercises/packet-observation/README.md",
    "exercises/path-diagnosis/README.md",
    "exercises/protocol-inspector/README.md",
}
ANNOTATION_SCOPES = {
    "window-model": "examples/window-model/README.md",
    "protocol-inspector": "exercises/protocol-inspector/README.md",
    "packet-observation": "exercises/packet-observation/README.md",
    "linux-routing-nat": "exercises/linux-routing-nat/README.md",
    "path-diagnosis": "exercises/path-diagnosis/README.md",
}
IMPLEMENTATION_PREFIX = "[" + "Implementation "
IMPLEMENTATION_TOKEN = re.compile(re.escape(IMPLEMENTATION_PREFIX) + r"([^\]\r\n]+)\]")
VALID_IMPLEMENTATION_LABEL = re.compile(r"^(0|[1-9][0-9]*)(?:-([1-9][0-9]*))?$")
TABLE_SEPARATOR_CELL = re.compile(r"^:?-{3,}:?$")
SOURCE_BASENAME = re.compile(
    r"(?<![A-Za-z0-9_.-])([A-Za-z0-9][A-Za-z0-9_-]*\.(?:py|sh))(?=`|::|\s|,|;|$)"
)


def error(message: str) -> None:
    ERRORS.append(message)


def section(text: str, title: str) -> str:
    match = re.search(rf"(?ms)^## {re.escape(title)}\s*$\n(.*?)(?=^## |\Z)", text)
    return match.group(1).strip() if match else ""


def bullets(text: str) -> list[str]:
    return [line for line in text.splitlines() if line.startswith("- ")]


def slug(text: str) -> str:
    value = re.sub(r"`([^`]*)`", r"\1", text)
    value = re.sub(r"<[^>]+>", "", value)
    value = unicodedata.normalize("NFKC", value).strip().casefold()
    value = re.sub(r"[^\w\-\s가-힣]", "", value)
    return re.sub(r"[\s_]+", "-", value).strip("-")


def headings(path: Path) -> set[str]:
    result: set[str] = set()
    seen: dict[str, int] = {}
    in_fence = False
    marker = ""
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.lstrip()
        match_fence = re.match(r"(`{3,}|~{3,})", stripped)
        if match_fence:
            current = match_fence.group(1)[0]
            if not in_fence:
                in_fence, marker = True, current
            elif current == marker:
                in_fence = False
            continue
        if in_fence:
            continue
        match = re.match(r"^#{1,6}\s+(.+?)\s*#*\s*$", line)
        if match:
            base = slug(match.group(1))
            count = seen.get(base, 0)
            seen[base] = count + 1
            result.add(base if count == 0 else f"{base}-{count}")
    return result


def markdown_without_fences(text: str) -> str:
    lines: list[str] = []
    in_fence = False
    marker = ""
    for line in text.splitlines():
        match = re.match(r"\s*(`{3,}|~{3,})", line)
        if match:
            current = match.group(1)[0]
            if not in_fence:
                in_fence, marker = True, current
            elif current == marker:
                in_fence = False
            continue
        if not in_fence:
            lines.append(line)
    return "\n".join(lines)


def source_files() -> list[Path]:
    """Return repository files without traversing generated or learner trees."""

    result: list[Path] = []
    for directory, names, files in os.walk(ROOT, topdown=True, followlinks=False):
        names[:] = sorted(name for name in names if name not in SKIPPED_TREE_NAMES)
        base = Path(directory)
        for name in sorted(files):
            candidate = base / name
            if name not in SKIPPED_TREE_NAMES and not candidate.is_symlink() and candidate.is_file():
                result.append(candidate)
    return result


def markdown_table_cells(line: str) -> list[str] | None:
    stripped = line.strip()
    if not stripped.startswith("|") or not stripped.endswith("|"):
        return None
    return [cell.replace(r"\|", "|").strip() for cell in re.split(r"(?<!\\)\|", stripped[1:-1])]


def first_markdown_table(text: str) -> tuple[list[str], bool, list[list[str]]] | None:
    """Parse the first contiguous pipe table without treating prose as table data."""

    lines = text.splitlines()
    for index, line in enumerate(lines):
        header = markdown_table_cells(line)
        if header is None:
            continue
        separator = markdown_table_cells(lines[index + 1]) if index + 1 < len(lines) else None
        separator_valid = separator is not None and len(separator) == len(header) and all(
            TABLE_SEPARATOR_CELL.fullmatch(cell) for cell in separator
        )
        rows: list[list[str]] = []
        for candidate in lines[index + 2 :]:
            cells = markdown_table_cells(candidate)
            if cells is None:
                break
            rows.append(cells)
        return header, separator_valid, rows
    return None


def implementation_order_key(label: str) -> tuple[int, int, int]:
    top, separator, child = label.partition("-")
    return int(top), 1 if separator else 0, int(child) if separator else 0


def annotation_scope(relative: str) -> str | None:
    if relative == "examples/window-model/window_model.py":
        return "window-model"
    if relative.startswith("exercises/protocol-inspector/reference/protocol_inspector/") and relative.endswith(".py"):
        return "protocol-inspector"
    if relative in {
        "exercises/packet-observation/scripts/analyze_tcpdump.py",
        "exercises/packet-observation/scripts/capture-loopback.sh",
    }:
        return "packet-observation"
    if relative.startswith("exercises/linux-routing-nat/scripts/") and relative.endswith((".py", ".sh")):
        return "linux-routing-nat"
    if relative.startswith("exercises/path-diagnosis/reference/path_diagnosis/") and relative.endswith(".py"):
        return "path-diagnosis"
    return None


def comment_lines(path: Path, text: str) -> set[int]:
    if path.suffix == ".py":
        try:
            return {
                token.start[0]
                for token in tokenize.generate_tokens(io.StringIO(text).readline)
                if token.type == tokenize.COMMENT
            }
        except (IndentationError, tokenize.TokenError):
            return set()
    if path.suffix == ".sh":
        return {
            number
            for number, line in enumerate(text.splitlines(), 1)
            if line.lstrip().startswith("#")
        }
    return set()


def check_numbering(scope: str, labels: list[str]) -> None:
    if len(labels) != len(set(labels)):
        duplicates = sorted(label for label in set(labels) if labels.count(label) > 1)
        error(f"Implementation annotation 중복: {scope}: {', '.join(duplicates)}")

    parsed: list[tuple[int, int | None]] = []
    for label in labels:
        top, separator, child = label.partition("-")
        parsed.append((int(top), int(child) if separator else None))
    if any(top == 0 and child is not None for top, child in parsed):
        error(f"Implementation 0에는 하위 번호를 사용할 수 없습니다: {scope}")

    top_levels = sorted({top for top, child in parsed if top > 0 and child is None})
    expected_top = list(range(1, max(top_levels, default=0) + 1))
    if top_levels != expected_top:
        error(f"Implementation 상위 번호가 1부터 연속이지 않습니다: {scope}")
    for top in top_levels:
        children = sorted({child for parent, child in parsed if parent == top and child is not None})
        expected_children = list(range(1, max(children, default=0) + 1))
        if children != expected_children:
            error(f"Implementation 하위 번호가 1부터 연속이지 않습니다: {scope}:{top}")
    orphaned = sorted({top for top, child in parsed if child is not None and top not in top_levels})
    if orphaned:
        error(f"Implementation 하위 번호의 parent가 없습니다: {scope}: {orphaned}")


def check_learning_mapping_and_annotations() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    mapping = section(readme, "정본 학습 순서")
    if not mapping:
        error("root README 정본 학습 순서가 없습니다")
    mapping_table = first_markdown_table(mapping) if mapping else None
    mapping_rows: list[list[str]] = []
    if mapping_table is None:
        error("root README ordered mapping 표가 없습니다")
    else:
        header, separator_valid, rows = mapping_table
        if tuple(header) != ROOT_MAPPING_COLUMNS:
            for column in ROOT_MAPPING_COLUMNS:
                if column not in header:
                    error(f"root README ordered mapping 열 누락: {column}")
            error("root README ordered mapping 열 구성이 canonical columns와 다릅니다")
        if not separator_valid:
            error("root README ordered mapping 구분 행 형식이 잘못되었습니다")

        order: list[int] = []
        for position, cells in enumerate(rows, 1):
            if len(cells) != len(ROOT_MAPPING_COLUMNS):
                error(f"root README ordered mapping data row 열 수 오류: row={position}")
                continue
            mapping_rows.append(cells)
            if re.fullmatch(r"[0-9]+", cells[0]) is None:
                error(f"root README ordered mapping 순서가 정수가 아닙니다: {cells[0]}")
                continue
            order.append(int(cells[0]))
        expected_order = list(range(14))
        if order != expected_order:
            error("root README ordered mapping 순서는 0부터 13까지 유일하고 연속이어야 합니다")

    mapping_data = "\n".join(" | ".join(cells) for cells in mapping_rows)
    for relative in sorted(DOCS):
        if f"]({relative})" not in mapping_data:
            error(f"root README ordered mapping 문서 누락: {relative}")
    for relative in sorted(ROOT_MAPPING_MATERIALS):
        if f"]({relative})" not in mapping_data:
            error(f"root README ordered mapping 실행 자료 누락: {relative}")

    anchors_by_scope: dict[str, dict[str, tuple[str, int]]] = {
        scope: {} for scope in ANNOTATION_SCOPES
    }
    for path in source_files():
        relative_path = path.relative_to(ROOT)
        data = path.read_bytes()
        if IMPLEMENTATION_PREFIX.encode() not in data:
            continue
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError:
            error(f"Implementation annotation이 UTF-8 text 밖에 있습니다: {relative_path}")
            continue
        allowed_comment_lines = comment_lines(path, text)
        relative = relative_path.as_posix()
        for number, line in enumerate(text.splitlines(), 1):
            if IMPLEMENTATION_PREFIX not in line:
                continue
            matches = list(IMPLEMENTATION_TOKEN.finditer(line))
            if line.count(IMPLEMENTATION_PREFIX) != len(matches):
                error(f"Implementation annotation token 형식 오류: {relative}:{number}")
                continue
            if len(matches) > 1:
                error(f"Implementation annotation은 한 comment line에 하나만 둘 수 있습니다: {relative}:{number}")
            for match in matches:
                label = match.group(1)
                parsed = VALID_IMPLEMENTATION_LABEL.fullmatch(label)
                if parsed is None or (parsed.group(1) == "0" and parsed.group(2) is not None):
                    error(f"Implementation annotation 번호 형식 오류: {relative}:{number}: {label}")
                    continue
                scope = annotation_scope(relative)
                if scope is None or number not in allowed_comment_lines:
                    error(f"허용되지 않은 Implementation annotation 위치: {relative}:{number}")
                    continue
                if re.search(r"[가-힣]", line) is None:
                    error(f"Implementation annotation 설명은 한국어를 포함해야 합니다: {relative}:{number}")
                anchors = anchors_by_scope[scope]
                if label in anchors:
                    first_relative, first_line = anchors[label]
                    error(
                        f"Implementation annotation 중복: {scope}: {label}: "
                        f"{first_relative}:{first_line}, {relative}:{number}"
                    )
                else:
                    anchors[label] = (relative, number)

    for scope, readme_relative in ANNOTATION_SCOPES.items():
        anchors = anchors_by_scope[scope]
        labels = list(anchors)
        if not labels:
            error(f"Implementation annotation scope가 비어 있습니다: {scope}")
            continue
        check_numbering(scope, labels)
        readme_path = ROOT / readme_relative
        implementation_order = section(readme_path.read_text(encoding="utf-8"), "권장 구현 순서")
        if not implementation_order:
            error(f"README 권장 구현 순서가 없습니다: {readme_relative}")
            continue
        if IMPLEMENTATION_PREFIX in implementation_order:
            error(f"README index가 source exact annotation token을 중복합니다: {readme_relative}")

        index_table = first_markdown_table(implementation_order)
        if index_table is None:
            error(f"README 권장 구현 순서 표가 없습니다: {readme_relative}")
            continue
        index_header, index_separator_valid, index_rows = index_table
        if len(index_header) < 2 or index_header[:2] != ["번호", "파일·symbol"]:
            error(f"README 권장 구현 순서 표 header가 잘못되었습니다: {readme_relative}")
        if not index_separator_valid:
            error(f"README 권장 구현 순서 표 구분 행이 잘못되었습니다: {readme_relative}")

        index_labels: list[str] = []
        index_cells: dict[str, str] = {}
        for position, cells in enumerate(index_rows, 1):
            if len(cells) != len(index_header):
                error(f"README 권장 구현 순서 data row 열 수 오류: {readme_relative}: row={position}")
                continue
            label = cells[0]
            parsed = VALID_IMPLEMENTATION_LABEL.fullmatch(label)
            if parsed is None or (parsed.group(1) == "0" and parsed.group(2) is not None):
                error(f"README 구현 순서 번호 형식 오류: {readme_relative}: {label}")
                continue
            index_labels.append(label)
            index_cells.setdefault(label, cells[1])

        if len(index_labels) != len(set(index_labels)):
            error(f"README 구현 순서 번호가 중복됩니다: {readme_relative}")
        if set(index_labels) != set(labels):
            error(f"README 구현 순서와 source annotation이 다릅니다: {readme_relative}")
        elif index_labels != sorted(labels, key=implementation_order_key):
            error(f"README 구현 순서가 의미적 번호 순서와 다릅니다: {readme_relative}")

        for label in index_labels:
            if label not in anchors or label not in index_cells:
                continue
            expected_basename = Path(anchors[label][0]).name
            declared = set(SOURCE_BASENAME.findall(index_cells[label]))
            if declared != {expected_basename}:
                error(
                    f"README 구현 순서 파일과 source annotation이 다릅니다: "
                    f"{readme_relative}: {label}: expected={expected_basename} "
                    f"declared={sorted(declared)}"
                )


def check_layout() -> None:
    if not LAYOUT.is_file():
        error("exact layout manifest가 없습니다")
        return
    expected = LAYOUT.read_text(encoding="utf-8").splitlines()
    if expected != sorted(set(expected)):
        error("exact layout manifest는 중복 없이 정렬되어야 합니다")
    actual_entries = source_manifest(ROOT)
    actual = sorted(
        str(entry["path"])
        for entry in actual_entries
        if entry["type"] != "directory"
    )
    missing = sorted(set(expected) - set(actual))
    unexpected = sorted(set(actual) - set(expected))
    if missing:
        error("exact layout 필수 파일 없음: " + ", ".join(missing))
    if unexpected:
        error("exact layout 예상 밖 파일: " + ", ".join(unexpected))
    for entry in actual_entries:
        if entry["type"] == "symlink":
            error(f"source symlink 금지: {entry['path']}")


def check_learning_contracts() -> None:
    actual_docs = {path.relative_to(ROOT).as_posix() for path in (ROOT / "docs").rglob("*.md")}
    if actual_docs != DOCS:
        error(f"본문 문서 구성이 다릅니다: missing={sorted(DOCS-actual_docs)} unexpected={sorted(actual_docs-DOCS)}")
    concept_completion: dict[str, str] = {}
    for relative in sorted(CONCEPT_DOCS):
        path = ROOT / relative
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8")
        positions = [text.find(f"## {title}\n") for title in CONCEPT_SECTIONS]
        if any(position < 0 for position in positions):
            error(f"개념 문서 학습 heading 누락: {relative}")
            continue
        if positions != sorted(positions):
            error(f"개념 문서 학습 heading 순서 오류: {relative}")
        if len(bullets(section(text, "학습 목표"))) < 2:
            error(f"학습 목표가 2개 미만입니다: {relative}")
        if not section(text, "선행 개념") or not section(text, "연결 실습"):
            error(f"선행 개념 또는 연결 실습이 비어 있습니다: {relative}")
        completion = section(text, "완료 기준")
        if len(bullets(completion)) < 3:
            error(f"개념 문서 완료 기준이 3개 미만입니다: {relative}")
        normalized = " ".join(completion.split())
        if normalized in concept_completion:
            error(f"개념 문서 복사형 완료 기준: {relative}, {concept_completion[normalized]}")
        concept_completion[normalized] = relative

    completion_owner: dict[str, str] = {}
    explanation_owner: dict[str, str] = {}
    for relative in sorted(EXERCISES):
        path = ROOT / relative
        if not path.is_file():
            error(f"실습 README가 없습니다: {relative}")
            continue
        text = path.read_text(encoding="utf-8")
        positions = [text.find(f"## {title}\n") for title in EXERCISE_SECTIONS]
        if any(position < 0 for position in positions):
            error(f"실습 학습 heading 누락: {relative}")
            continue
        if positions != sorted(positions):
            error(f"실습 학습 heading 순서 오류: {relative}")
        completion = section(text, "완료 기준")
        explanation = section(text, "자기 설명")
        if len(bullets(completion)) < 3:
            error(f"실습 완료 기준이 3개 미만입니다: {relative}")
        questions = bullets(explanation)
        if len(questions) < 2 or any(not question.rstrip().endswith("?") for question in questions):
            error(f"자기 설명 질문이 2개 미만이거나 물음표로 끝나지 않습니다: {relative}")
        normalized_completion = " ".join(completion.split())
        normalized_explanation = " ".join(explanation.split())
        if normalized_completion in completion_owner:
            error(f"실습 복사형 완료 기준: {relative}, {completion_owner[normalized_completion]}")
        if normalized_explanation in explanation_owner:
            error(f"실습 복사형 자기 설명: {relative}, {explanation_owner[normalized_explanation]}")
        completion_owner[normalized_completion] = relative
        explanation_owner[normalized_explanation] = relative

    roadmap = (ROOT / "docs/00-roadmap.md").read_text(encoding="utf-8")
    roadmap_requirements = (
        "## 대상 독자",
        "## 선행지식과 지원 환경",
        "필수 경로",
        "선택 경로",
        "## 문서와 실습의 대응",
        "## 완료 뒤 할 수 있어야 하는 일",
        "## 범위 밖 항목",
        "## 완료 기준",
        "## 자동 검증의 한계",
        "skipped=0",
    )
    for requirement in roadmap_requirements:
        if requirement not in roadmap:
            error(f"roadmap 학습 계약 누락: {requirement}")
    if "네임스페이스 실험을 건너뛰" in roadmap:
        error("roadmap이 필수 privileged Linux 실험의 skip을 허용합니다")


def check_markdown() -> None:
    markdown = sorted(path for path in source_files() if path.suffix == ".md")
    link_pattern = re.compile(r"!?\[[^]]*\]\(([^)]+)\)")
    for path in markdown:
        text = path.read_text(encoding="utf-8")
        lines = text.splitlines()
        relative = path.relative_to(ROOT)
        if not lines or not lines[0].startswith("# ") or sum(line.startswith("# ") for line in lines) != 1:
            error(f"H1 제목은 첫 줄에 정확히 하나여야 합니다: {relative}")
        prose = markdown_without_fences(text)
        for raw in link_pattern.findall(prose):
            target = raw.strip()
            if target.startswith("<") and ">" in target:
                target = target[1 : target.index(">")]
            else:
                target = target.split(maxsplit=1)[0]
            if target.startswith(("https://", "http://", "mailto:")):
                continue
            decoded = unquote(target)
            path_text, separator, fragment = decoded.partition("#")
            resolved = path if not path_text else (path.parent / path_text).resolve()
            try:
                resolved.relative_to(ROOT)
            except ValueError:
                error(f"저장소 밖 링크: {relative} -> {target}")
                continue
            if not resolved.exists():
                error(f"깨진 링크: {relative} -> {target}")
            elif separator and fragment and resolved.suffix == ".md" and slug(fragment) not in headings(resolved):
                error(f"깨진 anchor: {relative} -> {target}")


def check_source() -> None:
    for path in source_files():
        relative = path.relative_to(ROOT)
        if path.suffix in {".pyc", ".pyo"}:
            error(f"생성 bytecode가 남았습니다: {relative}")
        if path.name != "Makefile" and path.suffix not in TEXT_SUFFIXES:
            continue
        data = path.read_bytes()
        if b"\x00" in data or b"\r" in data:
            error(f"텍스트에 NUL 또는 CR이 있습니다: {relative}")
            continue
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError:
            error(f"UTF-8 텍스트가 아닙니다: {relative}")
            continue
        for number, line in enumerate(text.splitlines(), 1):
            if line.rstrip(" \t") != line:
                error(f"줄 끝 공백: {relative}:{number}")
        if path.suffix == ".py":
            try:
                ast.parse(text, filename=str(path))
            except SyntaxError as exception:
                error(f"Python 구문 오류: {relative}: {exception}")

    for reference in sorted((ROOT / "exercises").rglob("reference/**/*.py")):
        text = reference.read_text(encoding="utf-8")
        if re.search(r"\b(?:TODO|TBD|FIXME)\b|NotImplementedError", text):
            error(f"reference 미완성 표식: {reference.relative_to(ROOT)}")

    for script in sorted([ROOT / "prepare.sh", ROOT / "verify.sh", *(ROOT / "scripts").glob("*.sh"), *(ROOT / "exercises").rglob("*.sh")]):
        if script.is_file():
            outcome = subprocess.run(["sh", "-n", str(script)], capture_output=True, text=True)
            if outcome.returncode:
                error(f"Shell 구문 오류: {script.relative_to(ROOT)}: {outcome.stderr.strip()}")
            if os.name == "posix" and not os.access(script, os.X_OK):
                error(f"실행 권한 없음: {script.relative_to(ROOT)}")
    for script in sorted((ROOT / "scripts").glob("*.py")):
        if script.is_file() and script.read_bytes().startswith(b"#!") and os.name == "posix" and not os.access(script, os.X_OK):
            error(f"실행 권한 없음: {script.relative_to(ROOT)}")


def check_interfaces_and_pins() -> None:
    makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
    for target in ("prepare", "check", "static-check", "meta-check", "reference-check", "skeleton-check", "test-quality-check", "docker-e2e", "verify", "clean"):
        if re.search(rf"(?m)^{re.escape(target)}\s*:", makefile) is None:
            error(f"공개 Make target 누락: {target}")
    if re.search(r"(?m)^EXERCISE_IMPL := workspace$", makefile) is None:
        error("protocol 학습자 Make 기본값은 workspace여야 합니다")
    if re.search(r"(?m)^PATH_EXERCISE_IMPL := workspace$", makefile) is None:
        error("path 학습자 Make 기본값은 workspace여야 합니다")
    reference_target = re.search(
        r"(?ms)^reference-check:\s*\n(.*?)(?=^[^\t\n][^\n]*:|\Z)",
        makefile,
    )
    reference_recipe = reference_target.group(1) if reference_target else ""
    if "protocol-check EXERCISE_IMPL=reference" not in reference_recipe:
        error("reference-check가 protocol reference를 명시하지 않습니다")
    if "path-diagnosis-check PATH_EXERCISE_IMPL=reference" not in reference_recipe:
        error("reference-check가 path reference를 명시하지 않습니다")
    prepare = (ROOT / "prepare.sh").read_text(encoding="utf-8")
    verify = (ROOT / "verify.sh").read_text(encoding="utf-8")
    expected = "python:3.12-slim-bookworm@sha256:4766d8b510c428e595d74b9cc5bbb2fae8e26316fffb4adc89908d79aacd58a2"
    image_helper = (ROOT / "scripts/prepare_network_image.py").read_text(encoding="utf-8")
    if expected not in image_helper or "latest" in image_helper:
        error("고정 Python 3.12 verifier image digest 계약이 없습니다")
    package_pins = (
        "DEBIAN_SNAPSHOT = \"20260803T000000Z\"",
        '"iproute2": "6.1.0-3"',
        '"iptables": "1.8.9-2"',
        '"iputils-ping": "3:20221126-1+deb12u1"',
        '"tcpdump": "4.99.3-1"',
        '"procps": "2:4.0.2-3"',
    )
    if any(pin not in image_helper for pin in package_pins):
        error("Debian snapshot·network tool package version pin 계약이 없습니다")
    if "--check-state" not in verify or "package_versions" not in verify:
        error("verify가 verifier image package attestation을 재검사하지 않습니다")
    if "--pull=never" not in verify or "--privileged" not in verify:
        error("verify의 no-pull privileged Docker 계약이 없습니다")
    if "PREPARE RESULT: PASS" not in prepare or "VERIFY LOG:" not in verify or "RESULT: PASS" not in verify:
        error("prepare/verify 결과 출력 계약이 없습니다")
    combined = "\n".join((prepare, verify, (ROOT / "README.md").read_text(encoding="utf-8")))
    if "Python 3.11" in combined:
        error("지원 종료 기준인 Python 3.11 계약이 남았습니다")


def main() -> int:
    check_layout()
    check_learning_contracts()
    check_learning_mapping_and_annotations()
    check_markdown()
    check_source()
    check_interfaces_and_pins()
    if ERRORS:
        print(f"네트워크 가이드 검사 실패: {len(ERRORS)}건", file=sys.stderr)
        for message in ERRORS:
            print(f"- {message}", file=sys.stderr)
        return 1
    print(f"[PASS] exact layout, docs={len(DOCS)}, exercises={len(EXERCISES)}, pedagogy, links, source, pins")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
