#!/usr/bin/env python3
"""Validate learning-map and implementation-construction annotations."""

from __future__ import annotations

import argparse
import os
import re
import shlex
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import NamedTuple


ROOT = Path(__file__).resolve().parents[1]

MARKER_WORD = "Implementation"
MARKER_START = "[" + MARKER_WORD
MARKER_PATTERN = re.compile(
    re.escape(MARKER_START)
    + r" (?P<top>0|[1-9][0-9]*)(?:-(?P<child>[1-9][0-9]*))?\]"
)
PLAIN_NUMBER_PATTERN = re.compile(r"(?P<top>0|[1-9][0-9]*)(?:-(?P<child>[1-9][0-9]*))?")

IMPLEMENTATION_BLOCK_PATTERN = re.compile(
    r"<!--\s*implementation-scope:\s*(?P<id>[a-z0-9-]+)\s*-->"
    r"(?P<body>.*?)"
    r"<!--\s*/implementation-scope\s*-->",
    re.DOTALL,
)
IMPLEMENTATION_START_PATTERN = re.compile(
    r"<!--\s*implementation-scope:\s*[a-z0-9-]+\s*-->"
)
IMPLEMENTATION_END_PATTERN = re.compile(r"<!--\s*/implementation-scope\s*-->")

LEARNING_MAP_PATTERN = re.compile(
    r"<!--\s*learning-map:\s*(?P<id>modern|cpp98)\s*-->"
    r"(?P<body>.*?)"
    r"<!--\s*/learning-map\s*-->",
    re.DOTALL,
)
LEARNING_MAP_START_PATTERN = re.compile(
    r"<!--\s*learning-map:\s*(?:modern|cpp98)\s*-->"
)
LEARNING_MAP_END_PATTERN = re.compile(r"<!--\s*/learning-map\s*-->")
LEARNING_ROW_PATTERN = re.compile(
    r"<!--\s*learning-row:\s*(?P<id>(?:modern|cpp98)-[0-9]{2})\s*-->"
)

FENCE_PATTERN = re.compile(r"^\s{0,3}(`{3,}|~{3,})(.*)$")
SHELL_FENCE_NAMES = {"bash", "console", "shell", "sh", "zsh"}
SOURCE_SUFFIXES = {".c", ".cc", ".cpp", ".cxx", ".h", ".hh", ".hpp", ".hxx"}
TEXT_SUFFIXES = SOURCE_SUFFIXES | {
    ".cmake",
    ".json",
    ".md",
    ".py",
    ".sh",
    ".txt",
    ".yaml",
    ".yml",
}
GENERATED_DIRECTORY_NAMES = {
    ".git",
    ".guide-probes",
    ".pytest_cache",
    ".workspace",
    "__pycache__",
    "build",
}


class ScopeSpec(NamedTuple):
    identifier: str
    readme: str
    source_files: tuple[str, ...]
    source_directories: tuple[str, ...]


class BlockRecord(NamedTuple):
    identifier: str
    path: Path
    body: str
    body_start: int
    body_end: int


class MarkerOccurrence(NamedTuple):
    label: str
    top: int
    child: int | None
    path: Path
    line: int


class IndexRow(NamedTuple):
    label: str
    exact_marker: bool
    line: str


def scope_registry() -> tuple[ScopeSpec, ...]:
    modern = "exercises/01-modern-cpp"
    cpp98 = "exercises/02-cpp98-systems"
    command = f"{cpp98}/object-model/command-service"
    generic = f"{cpp98}/generic-programming"
    http = f"{cpp98}/networking/http-server"

    return (
        ScopeSpec(
            "modern-cmake",
            f"{modern}/README.md",
            (f"{modern}/CMakeLists.txt",),
            (),
        ),
        ScopeSpec(
            "modern-strong-types",
            f"{modern}/01-strong-types-and-cmake/README.md",
            (f"{modern}/01-strong-types-and-cmake/CMakeLists.txt",),
            (f"{modern}/01-strong-types-and-cmake/reference",),
        ),
        ScopeSpec(
            "modern-unique-file",
            f"{modern}/02-unique-file/README.md",
            (f"{modern}/02-unique-file/CMakeLists.txt",),
            (f"{modern}/02-unique-file/reference",),
        ),
        ScopeSpec(
            "modern-query-pipeline",
            f"{modern}/03-query-pipeline/README.md",
            (f"{modern}/03-query-pipeline/CMakeLists.txt",),
            (f"{modern}/03-query-pipeline/reference",),
        ),
        ScopeSpec(
            "modern-local-job-runner",
            f"{modern}/04-local-job-runner/README.md",
            (
                f"{modern}/04-local-job-runner/CMakeLists.txt",
                f"{modern}/04-local-job-runner/app/main.cpp",
            ),
            (f"{modern}/04-local-job-runner/reference",),
        ),
        ScopeSpec(
            "cpp98-command-01",
            f"{command}/01-procedural/README.md",
            (),
            (f"{command}/01-procedural/reference",),
        ),
        ScopeSpec(
            "cpp98-command-02",
            f"{command}/02-value-ownership/README.md",
            (),
            (f"{command}/02-value-ownership/reference",),
        ),
        ScopeSpec(
            "cpp98-command-03",
            f"{command}/03-responsibilities/README.md",
            (),
            (f"{command}/03-responsibilities/reference",),
        ),
        ScopeSpec(
            "cpp98-command-04",
            f"{command}/04-polymorphism/README.md",
            (),
            (f"{command}/04-polymorphism/reference",),
        ),
        ScopeSpec(
            "cpp98-command-05",
            f"{command}/05-errors/README.md",
            (),
            (f"{command}/05-errors/reference",),
        ),
        ScopeSpec(
            "cpp98-template-array",
            f"{generic}/template-array/README.md",
            (f"{generic}/template-array/demo.cpp",),
            (f"{generic}/template-array/reference",),
        ),
        ScopeSpec(
            "cpp98-mini-vector",
            f"{generic}/mini-vector/README.md",
            (f"{generic}/mini-vector/demo.cpp",),
            (f"{generic}/mini-vector/reference",),
        ),
        ScopeSpec(
            "cpp98-date-lookup",
            f"{generic}/stl-problems/README.md",
            (),
            (f"{generic}/stl-problems/date-lookup/reference",),
        ),
        ScopeSpec(
            "cpp98-rpn",
            f"{generic}/stl-problems/README.md",
            (),
            (f"{generic}/stl-problems/rpn/reference",),
        ),
        ScopeSpec(
            "cpp98-sorter",
            f"{generic}/stl-problems/README.md",
            (),
            (f"{generic}/stl-problems/sorter/reference",),
        ),
        ScopeSpec(
            "cpp98-line-server",
            f"{cpp98}/networking/line-server/README.md",
            (f"{cpp98}/networking/line-server/Makefile",),
            (f"{cpp98}/networking/line-server/reference",),
        ),
        ScopeSpec(
            "cpp98-http-01",
            f"{http}/01-parser/README.md",
            (f"{http}/01-parser/demo.cpp",),
            (f"{http}/01-parser/reference",),
        ),
        ScopeSpec(
            "cpp98-http-02",
            f"{http}/02-config-router/README.md",
            (f"{http}/02-config-router/demo.cpp",),
            (f"{http}/02-config-router/reference",),
        ),
        ScopeSpec(
            "cpp98-http-03",
            f"{http}/03-nonblocking-server/README.md",
            (),
            (f"{http}/03-nonblocking-server/reference",),
        ),
        ScopeSpec(
            "cpp98-http-04",
            f"{http}/04-cgi-process/README.md",
            (),
            (f"{http}/04-cgi-process/reference",),
        ),
        ScopeSpec(
            "cpp98-http-05",
            f"{http}/05-integrated-server/README.md",
            (),
            (f"{http}/05-integrated-server/reference",),
        ),
    )


def relative(path: Path, root: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return str(path)


def ignored_directory(name: str) -> bool:
    return name in GENERATED_DIRECTORY_NAMES or name.startswith("build-") or name.endswith(".dSYM")


def repository_files(root: Path, *, markdown_only: bool = False):
    for current_text, directory_names, file_names in os.walk(
        root, topdown=True, followlinks=False
    ):
        current = Path(current_text)
        directory_names[:] = [
            name
            for name in directory_names
            if not ignored_directory(name) and not (current / name).is_symlink()
        ]
        for name in file_names:
            path = current / name
            if path.is_symlink():
                continue
            if markdown_only:
                if path.suffix.lower() == ".md":
                    yield path
            elif path.name in {"CMakeLists.txt", "Makefile"} or path.suffix.lower() in TEXT_SUFFIXES:
                yield path


def marker_label(top: int, child: int | None) -> str:
    return str(top) if child is None else f"{top}-{child}"


def marker_sort_key(label: str) -> tuple[int, int]:
    match = PLAIN_NUMBER_PATTERN.fullmatch(label)
    if match is None:
        raise ValueError(label)
    child = match.group("child")
    return int(match.group("top")), 0 if child is None else int(child)


def resolve_scope_sources(
    root: Path, scope: ScopeSpec, errors: list[str]
) -> set[Path]:
    result: set[Path] = set()
    for path_text in scope.source_files:
        path = root / path_text
        if not path.is_file():
            errors.append(f"annotation source 누락: {scope.identifier} -> {path_text}")
        else:
            result.add(path)

    for directory_text in scope.source_directories:
        directory = root / directory_text
        if not directory.is_dir():
            errors.append(
                f"annotation source directory 누락: {scope.identifier} -> {directory_text}"
            )
            continue
        for path in directory.rglob("*"):
            if path.is_file() and not path.is_symlink() and path.suffix.lower() in SOURCE_SUFFIXES:
                result.add(path)
    return result


def collect_implementation_blocks(
    root: Path, scopes: tuple[ScopeSpec, ...], errors: list[str]
) -> dict[str, BlockRecord]:
    expected = {scope.identifier: (root / scope.readme).resolve() for scope in scopes}
    found: defaultdict[str, list[BlockRecord]] = defaultdict(list)

    for path in repository_files(root, markdown_only=True):
        text = path.read_text(encoding="utf-8")
        matches = list(IMPLEMENTATION_BLOCK_PATTERN.finditer(text))
        starts = list(IMPLEMENTATION_START_PATTERN.finditer(text))
        ends = list(IMPLEMENTATION_END_PATTERN.finditer(text))
        if len(matches) != len(starts) or len(matches) != len(ends):
            errors.append(f"implementation scope sentinel 짝이 맞지 않음: {relative(path, root)}")
        for match in matches:
            record = BlockRecord(
                match.group("id"),
                path.resolve(),
                match.group("body"),
                match.start("body"),
                match.end("body"),
            )
            found[record.identifier].append(record)

    for identifier in sorted(set(found) - set(expected)):
        for record in found[identifier]:
            errors.append(
                f"등록되지 않은 implementation scope: {identifier} -> "
                f"{relative(record.path, root)}"
            )

    records: dict[str, BlockRecord] = {}
    for identifier, owner in expected.items():
        candidates = found.get(identifier, [])
        if len(candidates) != 1:
            errors.append(
                f"implementation scope sentinel은 정확히 하나여야 함: "
                f"{identifier} ({len(candidates)}개)"
            )
            continue
        record = candidates[0]
        if record.path != owner:
            errors.append(
                f"implementation scope owner 불일치: {identifier} -> "
                f"{relative(record.path, root)} (expected {relative(owner, root)})"
            )
            continue
        records[identifier] = record
    return records


def parse_index_rows(
    scope: ScopeSpec, block: BlockRecord, errors: list[str]
) -> list[IndexRow]:
    rows: list[IndexRow] = []
    for line in block.body.splitlines():
        stripped = line.strip()
        if not stripped.startswith("|") or not stripped.endswith("|"):
            continue
        cells = [cell.strip() for cell in stripped[1:-1].split("|")]
        if not cells:
            continue
        first = cells[0].strip().strip("`").strip()
        if not first or first in {"번호", "순서"} or re.fullmatch(r":?-{3,}:?", first):
            continue

        exact = MARKER_PATTERN.fullmatch(first)
        plain = PLAIN_NUMBER_PATTERN.fullmatch(first)
        match = exact or plain
        if match is None:
            errors.append(
                f"implementation index 첫 열 형식 오류: {scope.identifier} -> {first!r}"
            )
            continue
        top = int(match.group("top"))
        child_text = match.group("child")
        child = None if child_text is None else int(child_text)
        rows.append(IndexRow(marker_label(top, child), exact is not None, line))

    if not rows:
        errors.append(f"implementation index data row 누락: {scope.identifier}")
    return rows


def validate_numbering(
    scope: ScopeSpec,
    occurrences: list[MarkerOccurrence],
    rows: list[IndexRow],
    errors: list[str],
) -> None:
    if not occurrences:
        errors.append(f"implementation marker 누락: {scope.identifier}")
        return

    occurrence_counts = Counter(item.label for item in occurrences)
    for label, count in sorted(occurrence_counts.items(), key=lambda item: marker_sort_key(item[0])):
        if count != 1:
            errors.append(
                f"implementation marker 중복: {scope.identifier} -> {label} ({count}개)"
            )

    if any(item.top == 0 for item in occurrences):
        errors.append(f"이 branch에는 Implementation 0을 사용하지 않음: {scope.identifier}")

    top_numbers = sorted({item.top for item in occurrences if item.child is None and item.top != 0})
    expected_top = list(range(1, top_numbers[-1] + 1)) if top_numbers else []
    if top_numbers != expected_top:
        errors.append(
            f"top-level implementation 번호가 1부터 연속적이지 않음: "
            f"{scope.identifier} -> {top_numbers}"
        )

    top_set = set(top_numbers)
    children: defaultdict[int, set[int]] = defaultdict(set)
    for item in occurrences:
        if item.child is None:
            continue
        if item.top not in top_set:
            errors.append(
                f"parent marker 없는 substep: {scope.identifier} -> {item.label}"
            )
        children[item.top].add(item.child)
    for parent, values in sorted(children.items()):
        ordered = sorted(values)
        expected = list(range(1, ordered[-1] + 1))
        if ordered != expected:
            errors.append(
                f"implementation substep 번호가 1부터 연속적이지 않음: "
                f"{scope.identifier} -> {parent}: {ordered}"
            )

    row_counts = Counter(row.label for row in rows)
    for label, count in sorted(row_counts.items(), key=lambda item: marker_sort_key(item[0])):
        if count != 1:
            errors.append(
                f"implementation index 번호 중복: {scope.identifier} -> {label} ({count}개)"
            )

    marker_labels = set(occurrence_counts)
    row_labels = set(row_counts)
    if marker_labels != row_labels:
        errors.append(
            f"source/README implementation index 불일치: {scope.identifier} "
            f"(source-only={sorted(marker_labels-row_labels, key=marker_sort_key)}, "
            f"index-only={sorted(row_labels-marker_labels, key=marker_sort_key)})"
        )

    row_order = [row.label for row in rows]
    expected_order = sorted(row_labels, key=marker_sort_key)
    if len(row_order) == len(row_labels) and row_order != expected_order:
        errors.append(
            f"implementation index가 construction order가 아님: "
            f"{scope.identifier} -> {row_order}"
        )


def validate_annotation_contracts(
    root: Path, scopes: tuple[ScopeSpec, ...] | None = None
) -> list[str]:
    root = root.resolve()
    active_scopes = scope_registry() if scopes is None else scopes
    errors: list[str] = []
    scope_by_id = {scope.identifier: scope for scope in active_scopes}
    if len(scope_by_id) != len(active_scopes):
        errors.append("annotation scope registry ID 중복")

    blocks = collect_implementation_blocks(root, active_scopes, errors)
    source_to_scope: dict[Path, str] = {}
    for scope in active_scopes:
        readme = root / scope.readme
        if not readme.is_file():
            errors.append(f"implementation scope README 누락: {scope.identifier} -> {scope.readme}")
        for source in resolve_scope_sources(root, scope, errors):
            resolved = source.resolve()
            previous = source_to_scope.get(resolved)
            if previous is not None and previous != scope.identifier:
                errors.append(
                    f"annotation source가 여러 scope에 등록됨: {relative(resolved, root)} -> "
                    f"{previous}, {scope.identifier}"
                )
            source_to_scope[resolved] = scope.identifier

    blocks_by_path: defaultdict[Path, list[BlockRecord]] = defaultdict(list)
    for block in blocks.values():
        blocks_by_path[block.path].append(block)

    occurrences: defaultdict[str, list[MarkerOccurrence]] = defaultdict(list)
    for path in repository_files(root):
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        exact_matches = list(MARKER_PATTERN.finditer(text))
        exact_starts = {match.start() for match in exact_matches}

        position = text.find(MARKER_START)
        while position != -1:
            if position not in exact_starts:
                line = text.count("\n", 0, position) + 1
                errors.append(
                    f"malformed implementation marker: {relative(path, root)}:{line}"
                )
            position = text.find(MARKER_START, position + len(MARKER_START))

        resolved = path.resolve()
        for match in exact_matches:
            top = int(match.group("top"))
            child_text = match.group("child")
            child = None if child_text is None else int(child_text)
            label = marker_label(top, child)
            line = text.count("\n", 0, match.start()) + 1

            identifier = source_to_scope.get(resolved)
            if identifier is None:
                containing = [
                    block
                    for block in blocks_by_path.get(resolved, [])
                    if block.body_start <= match.start() < block.body_end
                ]
                if len(containing) == 1:
                    identifier = containing[0].identifier
                else:
                    errors.append(
                        f"금지 경계의 implementation marker: "
                        f"{relative(path, root)}:{line} -> {label}"
                    )
                    continue
            occurrences[identifier].append(
                MarkerOccurrence(label, top, child, resolved, line)
            )

    for scope in active_scopes:
        block = blocks.get(scope.identifier)
        if block is None:
            continue
        rows = parse_index_rows(scope, block, errors)
        scope_occurrences = occurrences.get(scope.identifier, [])

        exact_index_labels = {row.label for row in rows if row.exact_marker}
        for occurrence in scope_occurrences:
            if occurrence.path == block.path and occurrence.label not in exact_index_labels:
                errors.append(
                    f"README sidecar marker는 index 첫 열에 있어야 함: "
                    f"{scope.identifier} -> {occurrence.label}"
                )

        validate_numbering(scope, scope_occurrences, rows, errors)

        row_by_label = {row.label: row for row in rows}
        for occurrence in scope_occurrences:
            if occurrence.path == block.path:
                continue
            row = row_by_label.get(occurrence.label)
            if row is None:
                continue
            candidates = {
                relative(occurrence.path, root),
                relative(occurrence.path, block.path.parent),
                occurrence.path.name,
            }
            if not any(candidate in row.line for candidate in candidates):
                errors.append(
                    f"implementation index에 anchor 파일 경로 누락: "
                    f"{scope.identifier} -> {occurrence.label} "
                    f"({relative(occurrence.path, root)})"
                )
    return errors


def split_markdown_row(line: str) -> list[str]:
    stripped = line.strip()
    if not stripped.startswith("|") or not stripped.endswith("|"):
        return []
    return [cell.strip() for cell in stripped[1:-1].split("|")]


def validate_learning_maps(root: Path) -> list[str]:
    root = root.resolve()
    readme = root / "README.md"
    if not readme.is_file():
        return ["learning map owner README.md 누락"]
    text = readme.read_text(encoding="utf-8")
    errors: list[str] = []
    matches = list(LEARNING_MAP_PATTERN.finditer(text))
    if len(matches) != len(list(LEARNING_MAP_START_PATTERN.finditer(text))) or len(matches) != len(
        list(LEARNING_MAP_END_PATTERN.finditer(text))
    ):
        errors.append("README learning-map sentinel 짝이 맞지 않음")

    found: defaultdict[str, list[re.Match[str]]] = defaultdict(list)
    for match in matches:
        found[match.group("id")].append(match)

    expected_rows = {
        "modern": [f"modern-{number:02d}" for number in range(1, 10)],
        "cpp98": [f"cpp98-{number:02d}" for number in range(1, 10)],
    }
    header_checks = (
        lambda cell: "순서" in cell,
        lambda cell: "문서" in cell,
        lambda cell: "관찰" in cell and "예제" in cell,
        lambda cell: "직접" in cell and "수행" in cell,
        lambda cell: "수정" in cell and "위치" in cell,
        lambda cell: "검증" in cell,
        lambda cell: "완료" in cell and ("비교" in cell or "다음" in cell),
    )

    for map_id, required_order in expected_rows.items():
        required = set(required_order)
        candidates = found.get(map_id, [])
        if len(candidates) != 1:
            errors.append(
                f"learning-map sentinel은 정확히 하나여야 함: {map_id} ({len(candidates)}개)"
            )
            continue
        body = candidates[0].group("body")
        table_lines = [line for line in body.splitlines() if split_markdown_row(line)]
        if len(table_lines) < 3:
            errors.append(f"learning-map Markdown table 누락: {map_id}")
            continue
        header = split_markdown_row(table_lines[0])
        if len(header) != 7 or any(
            not check(cell) for check, cell in zip(header_checks, header)
        ):
            errors.append(f"learning-map canonical 7개 열 불일치: {map_id} -> {header}")

        row_ids: list[str] = []
        for line in table_lines[1:]:
            cells = split_markdown_row(line)
            if cells and all(re.fullmatch(r":?-{3,}:?", cell) for cell in cells):
                continue
            row_matches = list(LEARNING_ROW_PATTERN.finditer(line))
            if len(row_matches) != 1:
                errors.append(
                    f"learning-map data row에는 ID가 정확히 하나여야 함: {map_id} -> {line.strip()}"
                )
                continue
            if len(cells) != 7:
                errors.append(
                    f"learning-map data row 열 개수 불일치: {map_id} -> {row_matches[0].group('id')}"
                )
            row_ids.append(row_matches[0].group("id"))

        counts = Counter(row_ids)
        for row_id, count in sorted(counts.items()):
            if count != 1:
                errors.append(f"learning row ID 중복: {row_id} ({count}개)")
        actual = set(row_ids)
        if actual != required:
            errors.append(
                f"learning-map row coverage 불일치: {map_id} "
                f"(missing={sorted(required-actual)}, extra={sorted(actual-required)})"
            )
        if len(row_ids) == len(actual) and row_ids != required_order:
            errors.append(
                f"learning-map row 순서 불일치: {map_id} -> {row_ids}"
            )
    return errors


def validate_fenced_shell_cd(root: Path) -> list[str]:
    root = root.resolve()
    errors: list[str] = []

    def validate_command(path: Path, number: int, command: str) -> None:
        if command.startswith("$ "):
            command = command[2:].lstrip()
        for segment in re.split(r"\s*(?:&&|\|\||;)\s*", command):
            if not segment or segment.startswith("#"):
                continue
            try:
                tokens = shlex.split(segment, comments=True)
            except ValueError as error:
                errors.append(
                    f"shell fence 명령 파싱 실패: {relative(path, root)}:{number}: {error}"
                )
                continue
            if not tokens or tokens[0] != "cd":
                continue
            arguments = tokens[1:]
            if arguments and arguments[0] == "--":
                arguments = arguments[1:]
            if len(arguments) != 1:
                errors.append(
                    f"shell fence cd target은 하나여야 함: {relative(path, root)}:{number}"
                )
                continue
            target_text = arguments[0]
            if (
                any(character in target_text for character in ("$", "`", "*", "?"))
                or target_text.startswith("~")
                or Path(target_text).is_absolute()
            ):
                errors.append(
                    f"shell fence cd target은 repo-root 정적 상대 경로여야 함: "
                    f"{relative(path, root)}:{number} -> {target_text}"
                )
                continue
            resolved = (root / target_text).resolve()
            try:
                resolved.relative_to(root)
            except ValueError:
                errors.append(
                    f"shell fence cd가 repository 밖을 가리킴: "
                    f"{relative(path, root)}:{number} -> {target_text}"
                )
                continue
            if not resolved.is_dir():
                errors.append(
                    f"shell fence cd target이 없음: "
                    f"{relative(path, root)}:{number} -> {target_text}"
                )

    for path in repository_files(root, markdown_only=True):
        marker: str | None = None
        marker_length = 0
        shell_block = False
        pending = ""
        pending_line = 0
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            fence = FENCE_PATTERN.match(line)
            if fence:
                token = fence.group(1)
                if marker is None:
                    marker = token[0]
                    marker_length = len(token)
                    info = fence.group(2).strip().split(None, 1)
                    shell_block = bool(info) and info[0].lower() in SHELL_FENCE_NAMES
                elif token[0] == marker and len(token) >= marker_length:
                    if shell_block and pending:
                        validate_command(path, pending_line, pending)
                    pending = ""
                    pending_line = 0
                    marker = None
                    marker_length = 0
                    shell_block = False
                continue
            if not shell_block:
                continue

            command = line.strip()
            if not pending:
                pending_line = number
            continued = command.endswith("\\")
            fragment = command[:-1].rstrip() if continued else command
            pending = f"{pending} {fragment}".strip()
            if not continued:
                validate_command(path, pending_line, pending)
                pending = ""
                pending_line = 0
        if shell_block and pending:
            validate_command(path, pending_line, pending)
    return errors


def validate_repository_contracts(root: Path = ROOT) -> list[str]:
    errors = validate_annotation_contracts(root)
    errors.extend(validate_learning_maps(root))
    errors.extend(validate_fenced_shell_cd(root))
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", nargs="?", default=str(ROOT))
    args = parser.parse_args()
    root = Path(args.root).resolve()

    errors = validate_repository_contracts(root)
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1

    print(
        f"학습 map·implementation annotation 검사: "
        f"scope {len(scope_registry())}개, map row 18개"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
