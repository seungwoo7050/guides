#!/usr/bin/env python3
from __future__ import annotations

import ast
import json
import os
import re
import stat
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]
ERRORS: list[str] = []
RUNTIME_ROOTS = {".git", ".guide", ".workspace"}
REPOSITORY_MANIFEST = ROOT / "config/repository-files.txt"
MANAGED_ROOTS = {".mvn", "config", "docs", "exercises", "LICENSES", "scripts"}
GENERATED_NAMES = {".DS_Store"}
GENERATED_SUFFIXES = {".class", ".jar", ".log", ".pyc", ".pyo", ".jfr"}
KNOWN_GENERATED_DIRECTORIES = {
    "target",
    "scripts/__pycache__",
    *(
        f"exercises/{exercise}/{variant}/target"
        for exercise in (
            "application-boundaries",
            "security-boundaries",
            "transaction-locking",
            "idempotency-outbox",
            "kafka-avro-contract",
            "resilient-http-client",
            "single-service-capstone",
        )
        for variant in ("reference", "skeleton")
    ),
}

EXPECTED_DOCS = {
    "docs/00-roadmap.md",
    "docs/01-spring-core/01-application-context-and-lifecycle.md",
    "docs/01-spring-core/02-configuration-profiles-and-readiness.md",
    "docs/02-web-and-security/01-mvc-validation-and-problem-detail.md",
    "docs/02-web-and-security/02-spring-security-request-model.md",
    "docs/02-web-and-security/03-authentication-authorization-and-csrf.md",
    "docs/03-persistence-and-cache/01-jpa-transactions-and-locking.md",
    "docs/03-persistence-and-cache/02-flyway-and-schema-integration.md",
    "docs/03-persistence-and-cache/03-spring-data-redis.md",
    "docs/04-distributed-adapters/01-spring-kafka-and-avro.md",
    "docs/04-distributed-adapters/02-outbox-and-scheduling.md",
    "docs/04-distributed-adapters/03-resilience4j-http-clients.md",
    "docs/05-quality-and-operations/01-test-boundaries-testcontainers-and-wiremock.md",
    "docs/05-quality-and-operations/02-actuator-metrics-logging-and-tracing.md",
    "docs/06-capstone.md",
    "docs/90-appendix/01-version-and-environment.md",
    "docs/90-appendix/02-command-and-troubleshooting.md",
}

EXPECTED_LEARNING_ROWS: tuple[tuple[tuple[str, ...], str | None], ...] = (
    (
        (
            "docs/00-roadmap.md",
            "docs/90-appendix/01-version-and-environment.md",
        ),
        None,
    ),
    (
        (
            "docs/01-spring-core/01-application-context-and-lifecycle.md",
            "docs/01-spring-core/02-configuration-profiles-and-readiness.md",
            "docs/02-web-and-security/01-mvc-validation-and-problem-detail.md",
        ),
        "application-boundaries",
    ),
    (
        (
            "docs/02-web-and-security/02-spring-security-request-model.md",
            "docs/02-web-and-security/03-authentication-authorization-and-csrf.md",
        ),
        "security-boundaries",
    ),
    (
        (
            "docs/03-persistence-and-cache/01-jpa-transactions-and-locking.md",
            "docs/03-persistence-and-cache/02-flyway-and-schema-integration.md",
        ),
        "transaction-locking",
    ),
    (("docs/03-persistence-and-cache/03-spring-data-redis.md",), None),
    (
        ("docs/04-distributed-adapters/01-spring-kafka-and-avro.md",),
        "kafka-avro-contract",
    ),
    (
        ("docs/04-distributed-adapters/02-outbox-and-scheduling.md",),
        "idempotency-outbox",
    ),
    (
        ("docs/04-distributed-adapters/03-resilience4j-http-clients.md",),
        "resilient-http-client",
    ),
    (
        ("docs/05-quality-and-operations/01-test-boundaries-testcontainers-and-wiremock.md",),
        None,
    ),
    (
        (
            "docs/05-quality-and-operations/02-actuator-metrics-logging-and-tracing.md",
            "docs/06-capstone.md",
        ),
        "single-service-capstone",
    ),
)
REQUIRED_LEARNING_HANDOFFS = (
    (
        "docs/01-spring-core/01-application-context-and-lifecycle.md",
        "docs/01-spring-core/02-configuration-profiles-and-readiness.md",
    ),
    (
        "docs/01-spring-core/02-configuration-profiles-and-readiness.md",
        "docs/02-web-and-security/01-mvc-validation-and-problem-detail.md",
    ),
    (
        "docs/02-web-and-security/01-mvc-validation-and-problem-detail.md",
        "exercises/application-boundaries/README.md",
    ),
    (
        "exercises/application-boundaries/README.md",
        "docs/02-web-and-security/02-spring-security-request-model.md",
    ),
    (
        "docs/02-web-and-security/02-spring-security-request-model.md",
        "docs/02-web-and-security/03-authentication-authorization-and-csrf.md",
    ),
    (
        "docs/02-web-and-security/03-authentication-authorization-and-csrf.md",
        "exercises/security-boundaries/README.md",
    ),
    (
        "exercises/security-boundaries/README.md",
        "docs/03-persistence-and-cache/01-jpa-transactions-and-locking.md",
    ),
    (
        "docs/03-persistence-and-cache/01-jpa-transactions-and-locking.md",
        "docs/03-persistence-and-cache/02-flyway-and-schema-integration.md",
    ),
    (
        "docs/03-persistence-and-cache/02-flyway-and-schema-integration.md",
        "exercises/transaction-locking/README.md",
    ),
    (
        "exercises/transaction-locking/README.md",
        "docs/03-persistence-and-cache/03-spring-data-redis.md",
    ),
    (
        "docs/03-persistence-and-cache/03-spring-data-redis.md",
        "docs/04-distributed-adapters/01-spring-kafka-and-avro.md",
    ),
    (
        "docs/04-distributed-adapters/01-spring-kafka-and-avro.md",
        "exercises/kafka-avro-contract/README.md",
    ),
    (
        "exercises/kafka-avro-contract/README.md",
        "docs/04-distributed-adapters/02-outbox-and-scheduling.md",
    ),
    (
        "docs/04-distributed-adapters/02-outbox-and-scheduling.md",
        "exercises/idempotency-outbox/README.md",
    ),
    (
        "exercises/idempotency-outbox/README.md",
        "docs/04-distributed-adapters/03-resilience4j-http-clients.md",
    ),
    (
        "docs/04-distributed-adapters/03-resilience4j-http-clients.md",
        "exercises/resilient-http-client/README.md",
    ),
    (
        "exercises/resilient-http-client/README.md",
        "docs/05-quality-and-operations/01-test-boundaries-testcontainers-and-wiremock.md",
    ),
    (
        "docs/05-quality-and-operations/01-test-boundaries-testcontainers-and-wiremock.md",
        "docs/05-quality-and-operations/02-actuator-metrics-logging-and-tracing.md",
    ),
    (
        "docs/05-quality-and-operations/02-actuator-metrics-logging-and-tracing.md",
        "docs/06-capstone.md",
    ),
    ("docs/06-capstone.md", "exercises/single-service-capstone/README.md"),
)
LEARNING_MAP_START = "<!-- learning-map:start -->"
LEARNING_MAP_END = "<!-- learning-map:end -->"
IMPLEMENTATION_PREFIX = "[" + "Implementation "
IMPLEMENTATION_CANDIDATE = re.compile(
    re.escape("[" + "Implementation") + r"[^\]\r\n]*\]"
)
IMPLEMENTATION_LABEL = re.compile(
    re.escape(IMPLEMENTATION_PREFIX)
    + r"(?P<number>0|[1-9]\d*(?:-[1-9]\d*)?)\]"
)
DIRECT_IMPLEMENTATION_SUFFIXES = {".java", ".xml", ".yaml", ".yml"}
SIDECAR_IMPLEMENTATION_SUFFIXES = {".avsc", ".csv", ".json", ".sql"}

OBSOLETE_PATHS = {
    "docs/00-spring-application-model.md",
    "docs/01-boot-startup-configuration-and-profiles.md",
    "docs/02-http-validation-and-problem-detail.md",
    "docs/03-jpa-transactions-and-locking.md",
    "docs/04-postgresql-and-flyway.md",
    "docs/05-redis-cache-and-idempotency.md",
    "docs/06-spring-kafka-and-avro.md",
    "docs/07-transactional-outbox-and-scheduling.md",
    "docs/08-http-clients-and-resilience4j.md",
    "docs/09-testcontainers-wiremock-and-test-slices.md",
    "docs/10-actuator-logging-metrics-and-tracing.md",
    "scripts/preflight.sh",
    "reference/command-reference.md",
    "reference/development-environment.md",
    "reference/environment-variable-checklist.md",
    "reference/troubleshooting-matrix.md",
    "reference/version-baseline.md",
}

EXPECTED_EXERCISES = {
    "application-boundaries",
    "security-boundaries",
    "transaction-locking",
    "idempotency-outbox",
    "kafka-avro-contract",
    "resilient-http-client",
    "single-service-capstone",
}
EXPECTED_MODULES = {
    f"exercises/{name}/reference" for name in EXPECTED_EXERCISES
}
RUBRIC_HEADINGS = ("## 목표", "## 완료 기준", "## 자기 설명", "## 검증")

FORBIDDEN_DOMAIN_WORDS = re.compile(
    r"\b(?:transfer|wallet|bet|betting|settlement|sportsbook)\b",
    re.IGNORECASE,
)


def add(message: str) -> None:
    ERRORS.append(message)


def relative(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def runtime_excluded(path: Path) -> bool:
    parts = path.relative_to(ROOT).parts
    return bool(parts) and parts[0] in RUNTIME_ROOTS


def source_files(pattern: str) -> list[Path]:
    return [
        path
        for path in sorted(ROOT.rglob(pattern))
        if path.is_file() and not runtime_excluded(path)
    ]


def check_text_hygiene(path: Path, text: str) -> None:
    if "\r" in text:
        add(f"CRLF 또는 CR 문자가 남아 있습니다: {relative(path)}")
    for number, line in enumerate(text.splitlines(), start=1):
        if line.rstrip() != line:
            add(f"줄 끝 공백이 있습니다: {relative(path)}:{number}")


def markdown_fence(line: str) -> tuple[str, int] | None:
    match = re.match(r"^ {0,3}(?P<marker>`{3,}|~{3,})", line)
    if match is None:
        return None
    marker = match.group("marker")
    return marker[0], len(marker)


def markdown_headings(text: str) -> list[tuple[str, str]]:
    result: list[tuple[str, str]] = []
    heading_pattern = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
    fence_character = ""
    fence_length = 0
    for line in text.splitlines():
        marker = markdown_fence(line)
        if marker is not None:
            character, length = marker
            if not fence_character:
                fence_character, fence_length = character, length
            elif character == fence_character and length >= fence_length:
                fence_character, fence_length = "", 0
            continue
        if fence_character or line.lstrip().startswith("|"):
            continue
        heading = heading_pattern.fullmatch(line)
        if heading is not None:
            result.append((heading.group(1), heading.group(2)))
    return result


def markdown_ignored_annotation_ranges(text: str) -> list[tuple[int, int]]:
    """Return fenced and inline-code ranges that describe labels, not anchors."""

    ignored: list[tuple[int, int]] = []
    fence_character = ""
    fence_length = 0
    offset = 0
    for line_with_ending in text.splitlines(keepends=True):
        line = line_with_ending.rstrip("\r\n")
        line_end = offset + len(line_with_ending)
        marker = markdown_fence(line)
        if marker is not None:
            character, length = marker
            ignored.append((offset, line_end))
            if not fence_character:
                fence_character, fence_length = character, length
            elif character == fence_character and length >= fence_length:
                fence_character, fence_length = "", 0
            offset = line_end
            continue
        if fence_character:
            ignored.append((offset, line_end))
            offset = line_end
            continue

        cursor = 0
        while cursor < len(line):
            if line[cursor] != "`":
                cursor += 1
                continue
            run_end = cursor
            while run_end < len(line) and line[run_end] == "`":
                run_end += 1
            delimiter = line[cursor:run_end]
            closing = line.find(delimiter, run_end)
            while closing >= 0 and closing + len(delimiter) < len(line) \
                    and line[closing + len(delimiter)] == "`":
                closing = line.find(delimiter, closing + len(delimiter) + 1)
            if closing < 0:
                cursor = run_end
                continue
            ignored.append((offset + cursor, offset + closing + len(delimiter)))
            cursor = closing + len(delimiter)
        offset = line_end
    return ignored


def check_markdown() -> None:
    link_pattern = re.compile(r"!?\[[^\]]*\]\(([^)]+)\)")

    def anchors(markdown: Path) -> set[str]:
        result: set[str] = set()
        counts: dict[str, int] = {}
        content = markdown.read_text(encoding="utf-8")
        for _level, heading in markdown_headings(content):
            plain = re.sub(r"[`*_~]", "", heading).strip().lower()
            plain = re.sub(r"[^0-9a-z가-힣 _-]", "", plain)
            slug = re.sub(r"\s+", "-", plain)
            slug = re.sub(r"-+", "-", slug).strip("-")
            count = counts.get(slug, 0)
            counts[slug] = count + 1
            result.add(slug if count == 0 else f"{slug}-{count}")
        return result

    for path in source_files("*.md"):
        text = path.read_text(encoding="utf-8")
        check_text_hygiene(path, text)
        if not text.startswith("# "):
            add(f"H1 제목이 없습니다: {relative(path)}")
        if text.count("```") % 2:
            add(f"코드 블록이 닫히지 않았습니다: {relative(path)}")

        h1_count = sum(1 for level, _ in markdown_headings(text) if level == "#")
        if h1_count != 1:
            add(f"H1은 하나여야 합니다: {relative(path)} ({h1_count})")

        for raw_target in link_pattern.findall(text):
            target = raw_target.strip().split()[0].strip("<>")
            if target.startswith(("http://", "https://", "mailto:")):
                continue
            decoded = unquote(target)
            file_part, separator, anchor = decoded.partition("#")
            resolved = path if not file_part else (path.parent / file_part).resolve()
            try:
                resolved.relative_to(ROOT)
            except ValueError:
                add(f"저장소 밖을 가리키는 링크입니다: {relative(path)} -> {target}")
                continue
            if not resolved.exists():
                add(f"대상이 없는 링크입니다: {relative(path)} -> {target}")
                continue
            if separator and anchor:
                if not resolved.is_file() or resolved.suffix.lower() != ".md":
                    add(f"Markdown가 아닌 대상의 anchor입니다: {relative(path)} -> {target}")
                elif anchor not in anchors(resolved):
                    add(f"대상이 없는 Markdown anchor입니다: {relative(path)} -> {target}")


def marked_block(path: Path, start: str, end: str, label: str) -> str | None:
    text = path.read_text(encoding="utf-8")
    if text.count(start) != 1 or text.count(end) != 1:
        add(f"{label} marker는 정확히 한 쌍이어야 합니다: {relative(path)}")
        return None
    start_at = text.index(start) + len(start)
    end_at = text.index(end)
    if start_at >= end_at:
        add(f"{label} marker 순서가 잘못되었습니다: {relative(path)}")
        return None
    return text[start_at:end_at]


def markdown_table_rows(block: str) -> list[list[str]]:
    rows: list[list[str]] = []
    for line in block.splitlines():
        stripped = line.strip()
        if not stripped.startswith("|") or not stripped.endswith("|"):
            continue
        cells = [cell.strip() for cell in stripped[1:-1].split("|")]
        if cells and all(re.fullmatch(r":?-+:?", cell) for cell in cells):
            continue
        rows.append(cells)
    return rows


def markdown_link_targets(text: str) -> list[str]:
    targets: list[str] = []
    for raw in re.findall(r"!?\[[^\]]*\]\(([^)]+)\)", text):
        target = unquote(raw.strip().split()[0].strip("<>"))
        targets.append(target.partition("#")[0])
    return targets


def inline_code_value(text: str) -> str:
    stripped = text.strip()
    if len(stripped) >= 2 and stripped.startswith("`") and stripped.endswith("`"):
        return stripped[1:-1]
    return stripped


def repository_markdown_targets(path: Path) -> set[str]:
    result: set[str] = set()
    text = path.read_text(encoding="utf-8")
    for target in markdown_link_targets(text):
        if not target or target.startswith(("http://", "https://", "mailto:")):
            continue
        resolved = (path.parent / target).resolve()
        try:
            result.add(resolved.relative_to(ROOT).as_posix())
        except ValueError:
            continue
    return result


def check_learning_handoffs() -> None:
    for source, target in REQUIRED_LEARNING_HANDOFFS:
        path = ROOT / source
        if path.is_file() and target not in repository_markdown_targets(path):
            add(f"필수 학습 handoff link가 없습니다: {source} -> {target}")


def check_learning_map() -> None:
    readme = ROOT / "README.md"
    if not readme.is_file():
        return
    block = marked_block(readme, LEARNING_MAP_START, LEARNING_MAP_END, "학습 순서")
    if block is None:
        return
    rows = markdown_table_rows(block)
    if not rows or len(rows[0]) != 7:
        add("README 학습 순서 표는 7개 semantic column이 필요합니다.")
        return
    data_rows = rows[1:]
    if len(data_rows) != len(EXPECTED_LEARNING_ROWS) or any(
        len(row) != 7 for row in data_rows
    ):
        add("README 학습 순서 표는 모든 data row에 7개 semantic cell이 필요합니다.")
    if any(len(row) == 7 and row[2] != "—" for row in data_rows):
        add("example이 없는 branch의 관찰 예제 cell은 —여야 합니다.")
    if any(len(row) == 7 and not row[6] for row in data_rows):
        add("README 학습 순서 표의 완료 뒤 비교·다음 cell이 비어 있습니다.")

    for position, (row, expected) in enumerate(
        zip(data_rows, EXPECTED_LEARNING_ROWS, strict=False), start=1
    ):
        if len(row) != 7:
            continue
        expected_docs, exercise = expected
        actual_docs = tuple(markdown_link_targets(row[1]))
        if actual_docs != expected_docs:
            add(
                f"README 학습 순서 {position}행의 문서 grouping이 다릅니다: "
                f"예상={list(expected_docs)}, 실제={list(actual_docs)}"
            )

        contract_cells = row[3:7]
        if exercise is None:
            joined = " | ".join(contract_cells)
            linked = [
                target
                for cell in contract_cells
                for target in markdown_link_targets(cell)
            ]
            if any(
                target.startswith("exercises/")
                for target in linked
            ) or any(
                value in joined
                for value in (".workspace/", "check-workspace.sh")
            ):
                add(f"README 학습 순서 {position}행에 예상하지 않은 실습 계약이 있습니다.")
            continue

        readme_link = f"exercises/{exercise}/README.md"
        workspace = f".workspace/{exercise}/src/main"
        check = f"./scripts/check-workspace.sh {exercise}"
        reference = f"exercises/{exercise}/reference/"
        if markdown_link_targets(row[3]) != [readme_link]:
            add(f"README 학습 순서의 docs와 실습 연결이 다릅니다: {exercise}")
        if inline_code_value(row[4]) != workspace:
            add(f"README 학습 순서의 수정 위치 cell이 다릅니다: {exercise}")
        if inline_code_value(row[5]) != check:
            add(f"README 학습 순서의 검증 cell이 다릅니다: {exercise}")
        if reference not in markdown_link_targets(row[6]):
            add(f"README 학습 순서의 완료 뒤 reference cell이 다릅니다: {exercise}")
        if any(
            reference in markdown_link_targets(cell)
            for cell in row[3:6]
        ):
            add(f"README 학습 순서의 reference가 비교 전 cell에 있습니다: {exercise}")


def managed_utf8_text_files() -> list[tuple[Path, str]]:
    result: list[tuple[Path, str]] = []
    for name in sorted(load_repository_manifest()):
        path = ROOT / name
        if not path.is_file() or path.is_symlink():
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        result.append((path, text))
    return result


def implementation_scope(path: Path) -> str | None:
    parts = path.relative_to(ROOT).parts
    if len(parts) >= 3 and parts[0] == "exercises" and parts[1] in EXPECTED_EXERCISES:
        return parts[1]
    return None


def versioned_migration(path: Path) -> bool:
    parts = path.relative_to(ROOT).parts
    return (
        len(parts) >= 9
        and parts[0] == "exercises"
        and parts[1] in EXPECTED_EXERCISES
        and parts[2:8] == ("reference", "src", "main", "resources", "db", "migration")
        and path.suffix.lower() == ".sql"
    )


def direct_annotation_is_comment(path: Path, text: str, start: int, end: int) -> bool:
    suffix = path.suffix.lower()
    line_start = text.rfind("\n", 0, start) + 1
    prefix = text[line_start:start].lstrip()
    if suffix == ".java":
        return prefix.startswith("//")
    if suffix in {".yaml", ".yml"}:
        return prefix.startswith("#")
    if suffix == ".xml":
        opening = text.rfind("<!--", 0, start)
        previous_close = text.rfind("-->", 0, start)
        closing = text.find("-->", end)
        return opening > previous_close and closing >= end
    return False


def implementation_block_bounds(path: Path, scope: str) -> tuple[int, int] | None:
    text = path.read_text(encoding="utf-8")
    start = (
        "<!-- implementation-order:start "
        f"scope=exercises/{scope}/reference semantics=recommended -->"
    )
    end = "<!-- implementation-order:end -->"
    if text.count(start) != 1 or text.count(end) != 1:
        add(f"권장 구현 순서 marker는 정확히 한 쌍이어야 합니다: {relative(path)}")
        return None
    start_at = text.index(start) + len(start)
    end_at = text.index(end)
    if start_at >= end_at:
        add(f"권장 구현 순서 marker 순서가 잘못되었습니다: {relative(path)}")
        return None
    return start_at, end_at


def check_implementation_annotations() -> None:
    occurrences: dict[str, dict[str, list[str]]] = {
        exercise: {} for exercise in EXPECTED_EXERCISES
    }
    readme_bounds: dict[str, tuple[int, int] | None] = {}
    for exercise in EXPECTED_EXERCISES:
        readme_bounds[exercise] = implementation_block_bounds(
            ROOT / f"exercises/{exercise}/README.md", exercise
        )

    for path, text in managed_utf8_text_files():
        ignored_markdown = (
            markdown_ignored_annotation_ranges(text)
            if path.suffix.lower() == ".md"
            else []
        )
        for candidate in IMPLEMENTATION_CANDIDATE.finditer(text):
            if any(
                start <= candidate.start() < end
                for start, end in ignored_markdown
            ):
                continue
            valid = IMPLEMENTATION_LABEL.fullmatch(candidate.group(0))
            if valid is None:
                add(
                    "Implementation label 형식이 잘못되었습니다: "
                    f"{relative(path)} -> {candidate.group(0)}"
                )
                continue
            number = valid.group("number")
            scope = implementation_scope(path)
            parts = path.relative_to(ROOT).parts
            allowed = False
            if scope is not None and parts == ("exercises", scope, "README.md"):
                bounds = readme_bounds[scope]
                allowed = bounds is not None and bounds[0] < candidate.start() < bounds[1]
            elif scope is not None and len(parts) >= 4 and parts[2] == "reference":
                in_test = len(parts) >= 5 and parts[3:5] == ("src", "test")
                if versioned_migration(path):
                    add(
                        "versioned migration Implementation은 README sidecar여야 합니다: "
                        f"{relative(path)}"
                    )
                    continue
                allowed = (
                    not in_test
                    and path.suffix.lower() in DIRECT_IMPLEMENTATION_SUFFIXES
                )
                if allowed and not direct_annotation_is_comment(
                    path, text, candidate.start(), candidate.end()
                ):
                    add(
                        "Implementation source anchor는 허용된 comment여야 합니다: "
                        f"{relative(path)}"
                    )
                    continue
            if not allowed:
                add(f"Implementation annotation 금지 위치입니다: {relative(path)}")
                continue
            occurrences[scope].setdefault(number, []).append(relative(path))

    plain_number = re.compile(r"0|[1-9]\d*(?:-[1-9]\d*)?")
    link_pattern = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
    for exercise in sorted(EXPECTED_EXERCISES):
        readme = ROOT / f"exercises/{exercise}/README.md"
        bounds = readme_bounds[exercise]
        if bounds is None:
            continue
        text = readme.read_text(encoding="utf-8")
        rows = markdown_table_rows(text[bounds[0]:bounds[1]])
        if not rows or len(rows[0]) != 3:
            add(f"권장 구현 순서 표는 3개 semantic column이 필요합니다: {relative(readme)}")
            continue

        indexed: dict[str, tuple[str, bool]] = {}
        for row in rows[1:]:
            if len(row) != 3:
                add(f"권장 구현 순서 표의 cell 수가 다릅니다: {relative(readme)}")
                continue
            sidecar_match = IMPLEMENTATION_LABEL.fullmatch(row[0])
            sidecar = sidecar_match is not None
            number = sidecar_match.group("number") if sidecar_match else row[0]
            if plain_number.fullmatch(number) is None:
                add(f"권장 구현 순서 index 형식이 잘못되었습니다: {relative(readme)} -> {row[0]}")
                continue
            if number in indexed:
                add(f"권장 구현 순서 index가 중복됩니다: {exercise} {number}")
                continue
            link = link_pattern.search(row[1])
            if link is None:
                add(f"권장 구현 순서 index에 기준 파일 link가 없습니다: {exercise} {number}")
                continue
            raw_target = unquote(link.group(1).strip().split()[0].strip("<>"))
            file_part = raw_target.partition("#")[0]
            target = (readme.parent / file_part).resolve()
            try:
                target_relative = target.relative_to(ROOT).as_posix()
            except ValueError:
                add(f"권장 구현 순서 index가 저장소 밖을 가리킵니다: {exercise} {number}")
                continue
            if not target.is_file():
                add(f"권장 구현 순서 index 대상 파일이 없습니다: {exercise} {number}")
            reference_root = (ROOT / f"exercises/{exercise}/reference").resolve()
            try:
                target_in_reference = target.relative_to(reference_root)
            except ValueError:
                add(
                    "Implementation sidecar/source가 scope reference 밖을 가리킵니다: "
                    f"{exercise} {number} -> {target_relative}"
                )
            else:
                if target_in_reference.parts[:2] == ("src", "test"):
                    add(
                        "Implementation sidecar/source가 repository test를 가리킵니다: "
                        f"{exercise} {number}"
                    )
            indexed[number] = (target_relative, sidecar)

        top_level = sorted(
            int(number)
            for number in indexed
            if number != "0" and "-" not in number
        )
        if not top_level or top_level != list(range(1, max(top_level) + 1)):
            add(f"Implementation top-level 번호가 1부터 연속하지 않습니다: {exercise}")
        children: dict[int, list[int]] = {}
        for number in indexed:
            if "-" not in number:
                continue
            parent, child = (int(value) for value in number.split("-", 1))
            children.setdefault(parent, []).append(child)
        for parent, values in children.items():
            if str(parent) not in indexed:
                add(f"Implementation substep의 parent가 없습니다: {exercise} {parent}")
            ordered = sorted(values)
            if ordered != list(range(1, max(ordered) + 1)):
                add(f"Implementation substep 번호가 1부터 연속하지 않습니다: {exercise} {parent}")

        if set(indexed) != set(occurrences[exercise]):
            add(
                f"권장 구현 순서 index와 authoritative anchor가 다릅니다: {exercise} "
                f"index={sorted(indexed)}, anchor={sorted(occurrences[exercise])}"
            )
        for number, (target, sidecar) in indexed.items():
            actual = occurrences[exercise].get(number, [])
            if sidecar:
                if Path(target).suffix.lower() not in SIDECAR_IMPLEMENTATION_SUFFIXES:
                    add(f"Implementation sidecar가 주석 불가 파일을 가리키지 않습니다: {exercise} {number}")
                if Path(target).suffix.lower() == ".sql" and not versioned_migration(
                    ROOT / target
                ):
                    add(f"Implementation SQL sidecar가 versioned migration이 아닙니다: {exercise} {number}")
                expected = [relative(readme)]
            else:
                if Path(target).suffix.lower() not in DIRECT_IMPLEMENTATION_SUFFIXES:
                    add(f"Implementation source anchor 대상 형식이 잘못되었습니다: {exercise} {number}")
                expected = [target]
            if actual != expected:
                add(
                    f"Implementation anchor가 index의 기준 파일과 일치하지 않습니다: "
                    f"{exercise} {number} 예상={expected}, 실제={actual}"
                )


def load_repository_manifest() -> dict[str, str]:
    if not REPOSITORY_MANIFEST.is_file():
        add("정확한 repository file manifest가 없습니다: config/repository-files.txt")
        return {}
    expected: dict[str, str] = {}
    for number, line in enumerate(
        REPOSITORY_MANIFEST.read_text(encoding="utf-8").splitlines(), start=1
    ):
        if not line or line.startswith("#"):
            continue
        match = re.fullmatch(r"(100644|100755|120000)\t(.+)", line)
        if match is None:
            add(f"repository manifest 형식이 잘못되었습니다: {number}")
            continue
        mode, path = match.groups()
        if path in expected:
            add(f"repository manifest 경로가 중복됩니다: {path}")
        expected[path] = mode
    return expected


def check_exact_repository_tree() -> None:
    expected = load_repository_manifest()
    if not expected:
        return
    actual: dict[str, str] = {}
    for path in ROOT.rglob("*"):
        relative_path = path.relative_to(ROOT).as_posix()
        first = relative_path.split("/", 1)[0]
        if first in RUNTIME_ROOTS:
            continue
        metadata = path.lstat()
        if stat.S_ISLNK(metadata.st_mode):
            actual[relative_path] = "120000"
        elif stat.S_ISREG(metadata.st_mode):
            actual[relative_path] = (
                "100755" if stat.S_IMODE(metadata.st_mode) & 0o111 else "100644"
            )
    expected_paths = set(expected)
    actual_paths = set(actual)
    if actual_paths != expected_paths:
        add(
            "정확한 managed tree가 다릅니다: "
            f"누락={sorted(expected_paths - actual_paths)}, "
            f"추가={sorted(actual_paths - expected_paths)}"
        )
    for path in sorted(expected_paths & actual_paths):
        if actual[path] != expected[path]:
            add(
                f"파일 mode가 manifest와 다릅니다: {path} "
                f"예상={expected[path]}, 실제={actual[path]}"
            )

    for path in ROOT.rglob("*"):
        relative_path = path.relative_to(ROOT).as_posix()
        if relative_path.split("/", 1)[0] in RUNTIME_ROOTS:
            continue
        if path.name in GENERATED_NAMES or path.suffix.lower() in GENERATED_SUFFIXES:
            add(f"생성물이 source tree에 남아 있습니다: {relative_path}")
        first = relative_path.split("/", 1)[0]
        if path.is_dir() and (
            relative_path in KNOWN_GENERATED_DIRECTORIES
            or (
                first in MANAGED_ROOTS
                and path.name in {"target", "__pycache__", ".workspace"}
            )
        ):
            add(
                "허용되지 않은 생성 directory가 source tree에 남아 있습니다: "
                f"{relative_path}"
            )


def check_structured_files() -> None:
    for path in source_files("pom.xml"):
        try:
            ET.parse(path)
        except ET.ParseError as exception:
            add(f"POM XML 오류: {relative(path)}: {exception}")

    for path in source_files("*.json") + source_files("*.avsc"):
        try:
            json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exception:
            add(f"JSON 오류: {relative(path)}: {exception}")

    for path in source_files("*.yml") + source_files("*.yaml"):
        text = path.read_text(encoding="utf-8")
        check_text_hygiene(path, text)
        for number, line in enumerate(text.splitlines(), start=1):
            if "\t" in line:
                add(f"YAML에 tab이 있습니다: {relative(path)}:{number}")


def check_java_sources() -> None:
    package_pattern = re.compile(r"^package\s+([\w.]+);", re.MULTILINE)
    english_comment = re.compile(
        r"^\s*//\s*(?=.*[A-Za-z])(?!.+[가-힣]).+$",
        re.MULTILINE,
    )

    for path in source_files("*.java"):
        text = path.read_text(encoding="utf-8")
        check_text_hygiene(path, text)
        package = package_pattern.search(text)
        if not package:
            add(f"package 선언이 없습니다: {relative(path)}")
            continue

        expected_suffix = Path(*package.group(1).split(".")) / path.name
        posix = path.as_posix()
        if "/src/main/java/" in posix or "/src/test/java/" in posix:
            if not posix.endswith(expected_suffix.as_posix()):
                add(f"package와 경로가 다릅니다: {relative(path)}")

        brace_source = re.sub(r'"(?:\\.|[^"\\])*"', '""', text)
        brace_source = re.sub(r"'(?:\\.|[^'\\])*'", "''", brace_source)
        brace_source = re.sub(
            r"//.*?$|/\*.*?\*/",
            "",
            brace_source,
            flags=re.MULTILINE | re.DOTALL,
        )
        if brace_source.count("{") != brace_source.count("}"):
            add(f"중괄호 수가 다릅니다: {relative(path)}")
        if english_comment.search(text):
            add(f"영문 코드 주석이 남아 있습니다: {relative(path)}")

        if "/reference/src/" in posix and re.search(r"\b(?:TODO|FIXME)\b", text):
            add(f"reference에 미완성 표식이 있습니다: {relative(path)}")
        if (
            re.search(
                r"@(PreAuthorize|PostAuthorize|Transactional|CircuitBreaker|Retry|"
                r"TimeLimiter|RateLimiter|Bulkhead|Cacheable|CacheEvict|Async)\b",
                text,
            )
            and re.search(r"\bpublic\s+final\s+class\b", text)
        ):
            add(f"AOP proxy 대상 bean이 final class입니다: {relative(path)}")


def check_reference_completion() -> None:
    """Reject unfinished markers in every textual reference artifact."""

    text_suffixes = {
        ".avsc",
        ".java",
        ".json",
        ".md",
        ".properties",
        ".sql",
        ".xml",
        ".yaml",
        ".yml",
    }
    for path in sorted(ROOT.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in text_suffixes:
            continue
        if "reference" not in path.parts or runtime_excluded(path):
            continue
        if re.search(r"\b(?:TODO|FIXME)\b", path.read_text(encoding="utf-8")):
            add(f"reference에 미완성 표식이 있습니다: {relative(path)}")


def xml_text(parent: ET.Element, path: str) -> str | None:
    namespace = {"m": "http://maven.apache.org/POM/4.0.0"}
    element = parent.find(path, namespace)
    return element.text.strip() if element is not None and element.text else None


def test_file_map(root: Path) -> dict[str, bytes]:
    if not root.is_dir():
        return {}
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in sorted(root.rglob("*.java"))
        if path.is_file()
    }


def check_exercises() -> None:
    exercises_root = ROOT / "exercises"
    if not exercises_root.is_dir():
        add("exercises directory가 없습니다.")
        return

    actual_exercises = {
        path.name for path in exercises_root.iterdir() if path.is_dir()
    }
    if actual_exercises != EXPECTED_EXERCISES:
        add(
            "실습 경로가 다릅니다: "
            f"예상={sorted(EXPECTED_EXERCISES)}, 실제={sorted(actual_exercises)}"
        )

    self_explanations: dict[str, str] = {}
    for exercise in sorted(EXPECTED_EXERCISES):
        exercise_root = exercises_root / exercise
        readme = exercise_root / "README.md"
        required = [
            readme,
            exercise_root / "skeleton/pom.xml",
            exercise_root / "reference/pom.xml",
        ]
        for path in required:
            if not path.is_file():
                add(f"실습 필수 파일이 없습니다: {relative(path)}")

        if readme.is_file():
            text = readme.read_text(encoding="utf-8")
            reference_artifact = f":{exercise}-reference"
            if reference_artifact not in text:
                add(f"reference 실행 명령이 없습니다: {relative(readme)}")
            workspace_create = f"./scripts/new-workspace.sh {exercise}"
            workspace_check = f"./scripts/check-workspace.sh {exercise}"
            if workspace_create not in text or workspace_check not in text:
                add(f"안전한 canonical workspace 명령이 없습니다: {relative(readme)}")
            direct_skeleton = f"./mvnw -f exercises/{exercise}/skeleton/pom.xml test"
            if direct_skeleton in text:
                add(f"tracked skeleton 직접 수정·실행 흐름이 남았습니다: {relative(readme)}")
            if "tracked skeleton" not in text or ".workspace/" not in text:
                add(f"canonical skeleton 불변 학습 흐름이 없습니다: {relative(readme)}")

            heading_positions = [text.find(heading) for heading in RUBRIC_HEADINGS]
            if any(position < 0 for position in heading_positions):
                add(f"실습 루브릭 heading이 빠졌습니다: {relative(readme)}")
            elif heading_positions != sorted(heading_positions):
                add(f"실습 루브릭 순서가 다릅니다: {relative(readme)}")
            else:
                completion = text[
                    heading_positions[1] + len(RUBRIC_HEADINGS[1]):heading_positions[2]
                ]
                explanation = text[
                    heading_positions[2] + len(RUBRIC_HEADINGS[2]):heading_positions[3]
                ].strip()
                if len(re.findall(r"^- ", completion, re.MULTILINE)) < 3:
                    add(f"관찰 가능한 완료 기준이 3개 미만입니다: {relative(readme)}")
                if explanation.count("?") < 2:
                    add(f"자기 설명 질문이 2개 미만입니다: {relative(readme)}")
                if len(explanation) < 80:
                    add(f"자기 설명이 지나치게 짧습니다: {relative(readme)}")
                self_explanations[exercise] = re.sub(r"\s+", " ", explanation)

        skeleton_tests = test_file_map(exercise_root / "skeleton/src/test/java")
        reference_tests = test_file_map(exercise_root / "reference/src/test/java")
        if not skeleton_tests:
            add(f"skeleton test가 없습니다: {exercise}")
        if not reference_tests:
            add(f"reference test가 없습니다: {exercise}")
        if skeleton_tests.keys() != reference_tests.keys():
            add(f"skeleton과 reference의 test 경로가 다릅니다: {exercise}")
        else:
            for name in sorted(skeleton_tests):
                if skeleton_tests[name] != reference_tests[name]:
                    add(
                        "skeleton과 reference가 같은 test 계약을 사용하지 않습니다: "
                        f"{exercise}/{name}"
                    )

        for variant in ("skeleton", "reference"):
            pom = exercise_root / variant / "pom.xml"
            if not pom.is_file():
                continue
            tree = ET.parse(pom)
            artifact = xml_text(tree.getroot(), "./m:artifactId")
            expected_artifact = f"{exercise}-{variant}"
            if artifact != expected_artifact:
                add(
                    f"artifactId가 경로와 다릅니다: {relative(pom)} "
                    f"예상={expected_artifact}, 실제={artifact}"
                )

        nested_readmes = list(exercise_root.glob("*/README.md"))
        for path in nested_readmes:
            add(f"skeleton/reference 하위의 형식적 README입니다: {relative(path)}")

    explanations = list(self_explanations.values())
    if len(explanations) != len(set(explanations)):
        add("서로 다른 실습에 복사된 자기 설명 문구가 있습니다.")

    policy_files = source_files("NeverPullPolicy.java")
    if len(policy_files) != 8:
        add(f"Testcontainers no-pull 정책 파일은 8개여야 합니다: {len(policy_files)}")
    for path in policy_files:
        text = path.read_text(encoding="utf-8")
        if "implements ImagePullPolicy" not in text or "return false;" not in text:
            add(f"Testcontainers no-pull 정책 구현이 다릅니다: {relative(path)}")


def check_layout() -> None:
    required_files = {
        "README.md",
        "CONTRIBUTING.md",
        "LICENSE.md",
        "pom.xml",
        "Makefile",
        ".gitignore",
        "mvnw",
        ".mvn/wrapper/maven-wrapper.properties",
        "prepare.sh",
        "verify.sh",
        "scripts/validate.py",
        "scripts/validator_self_test.py",
        "scripts/check-skeleton-report.py",
        "scripts/check-effective-pom.py",
        "scripts/check-workspace.sh",
        "scripts/new-workspace.sh",
        "scripts/source_fingerprint.py",
        "scripts/mvn-guide.sh",
        "scripts/verify-workspaces.sh",
        "scripts/workspace.py",
        *EXPECTED_DOCS,
    }
    for required in sorted(required_files):
        if not (ROOT / required).is_file():
            add(f"필수 파일이 없습니다: {required}")

    actual_docs = {
        relative(path) for path in source_files("*.md") if "docs" in path.parts
    }
    if actual_docs != EXPECTED_DOCS:
        add(
            "docs 파일 구성이 다릅니다: "
            f"누락={sorted(EXPECTED_DOCS - actual_docs)}, "
            f"추가={sorted(actual_docs - EXPECTED_DOCS)}"
        )

    for obsolete in sorted(OBSOLETE_PATHS):
        if (ROOT / obsolete).exists() or (ROOT / obsolete).is_symlink():
            add(f"prepare.sh가 삭제해야 할 폐기 경로가 남아 있습니다: {obsolete}")

    reference_docs = [
        path for path in (ROOT / "reference").glob("*.md")
    ] if (ROOT / "reference").is_dir() else []
    for path in reference_docs:
        add(f"필수 내용이 docs 밖에 남아 있습니다: {relative(path)}")

    root_pom = ROOT / "pom.xml"
    if root_pom.is_file():
        tree = ET.parse(root_pom)
        namespace = {"m": "http://maven.apache.org/POM/4.0.0"}
        modules = {
            module.text.strip()
            for module in tree.findall("./m:modules/m:module", namespace)
            if module.text
        }
        if modules != EXPECTED_MODULES:
            add(
                "Maven reference 모듈이 다릅니다: "
                f"예상={sorted(EXPECTED_MODULES)}, 실제={sorted(modules)}"
            )
        for module in modules:
            if not (ROOT / module / "pom.xml").is_file():
                add(f"Maven module POM이 없습니다: {module}")

        parent_version = xml_text(tree.getroot(), "./m:parent/m:version")
        version_doc = ROOT / "docs/90-appendix/01-version-and-environment.md"
        if parent_version and version_doc.is_file():
            if f"| Spring Boot | {parent_version} |" not in version_doc.read_text(
                encoding="utf-8"
            ):
                add("root POM과 버전 문서의 Spring Boot 기준이 다릅니다.")

    for executable in (
        "mvnw",
        "prepare.sh",
        "verify.sh",
        "scripts/check-skeleton-report.py",
        "scripts/check-effective-pom.py",
        "scripts/check-workspace.sh",
        "scripts/guide_state.py",
        "scripts/mvn-guide.sh",
        "scripts/new-workspace.sh",
        "scripts/run_in_session.py",
        "scripts/source_fingerprint.py",
        "scripts/validate.py",
        "scripts/validator_self_test.py",
        "scripts/verify-skeletons.sh",
        "scripts/verify-workspaces.sh",
        "scripts/workspace.py",
    ):
        path = ROOT / executable
        if path.exists() and not os.access(path, os.X_OK):
            add(f"실행 권한이 없습니다: {executable}")

    readme = (
        (ROOT / "README.md").read_text(encoding="utf-8")
        if (ROOT / "README.md").exists()
        else ""
    )
    if "VERIFY_LOG=" not in readme:
        add("README에 외부 검증 로그 계약이 없습니다.")
    gitignore = (
        (ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()
        if (ROOT / ".gitignore").is_file()
        else []
    )
    required_ignores = {
        "/target/",
        "/exercises/*/reference/target/",
        "/exercises/*/skeleton/target/",
        "/scripts/__pycache__/",
        "/.guide/",
        "/.workspace/",
    }
    if not required_ignores.issubset(gitignore):
        add(".gitignore의 path-specific generated allowlist가 빠졌습니다.")
    if any(line in {"target/", "**/target/", ".workspace/", "**/.workspace/"} for line in gitignore):
        add(".gitignore가 learner target/.workspace를 광범위하게 제외합니다.")
    contributing = (
        (ROOT / "CONTRIBUTING.md").read_text(encoding="utf-8")
        if (ROOT / "CONTRIBUTING.md").is_file()
        else ""
    )
    for document_name, document in (
        ("README.md", readme),
        ("CONTRIBUTING.md", contributing),
    ):
        for command in ("make prepare", "make check", "make verify", "make clean"):
            if command not in document:
                add(f"{document_name}에 공개 명령이 없습니다: {command}")

    forbidden_names = {
        "CATALOG.md",
        "INTEGRATION.md",
        ".DS_Store",
        ".idea",
        ".vscode",
    }
    for path in ROOT.rglob("*"):
        if runtime_excluded(path):
            continue
        if path.name in forbidden_names:
            add(f"포함하지 않는 파일 또는 directory입니다: {relative(path)}")
    check_exercises()


def check_wrapper() -> None:
    properties_path = ROOT / ".mvn/wrapper/maven-wrapper.properties"
    wrapper_path = ROOT / "mvnw"
    if not properties_path.exists() or not wrapper_path.exists():
        return

    properties = properties_path.read_text(encoding="utf-8")
    wrapper = wrapper_path.read_text(encoding="utf-8")
    parsed: dict[str, str] = {}
    for line in properties.splitlines():
        if not line or line.lstrip().startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        parsed[key.strip()] = value.strip()
    required_values = {
        "wrapperVersion": "3.3.4",
        "distributionUrl": (
            "https://repo.maven.apache.org/maven2/org/apache/maven/apache-maven/"
            "3.9.16/apache-maven-3.9.16-bin.zip"
        ),
        "distributionSha256Sum": (
            "5af3b743dd8b876b5c45da33b676251e5f1687712644abb4ee519ca56e1d89ce"
        ),
    }
    for key, value in sorted(required_values.items()):
        if parsed.get(key) != value:
            add(f"Maven Wrapper effective 설정이 다릅니다: {key}")
    if "Apache Maven Wrapper startup batch script, version 3.3.4" not in wrapper:
        add("공식 Maven Wrapper 3.3.4 script가 아닙니다.")


def shell_array(text: str, name: str) -> set[str]:
    match = re.search(
        rf"^{re.escape(name)}=\(\n(?P<body>.*?)^\)",
        text,
        flags=re.MULTILINE | re.DOTALL,
    )
    if not match:
        return set()
    return set(re.findall(r'^\s*"([^"\n]+)"\s*$', match.group("body"), re.MULTILINE))


def check_script_contracts() -> None:
    prepare_path = ROOT / "prepare.sh"
    verify_path = ROOT / "verify.sh"
    if not prepare_path.is_file() or not verify_path.is_file():
        return

    prepare = prepare_path.read_text(encoding="utf-8")
    verify = verify_path.read_text(encoding="utf-8")
    check_text_hygiene(prepare_path, prepare)
    check_text_hygiene(verify_path, verify)

    for required in (
        'MARKER="$CACHE_DIR/prepared.json"',
        '"$STATE_TOOL" capture',
        '"$STATE_TOOL" index-state',
        '"$STATE_TOOL" copy',
        '"$STATE_TOOL" write-marker',
        '"$STATE_TOOL" validate-marker',
        '"$RUNNER"',
        "dependency:go-offline",
        "org.apache.maven.surefire:surefire-junit-platform:3.5.6",
        "org.apache.maven.plugins:maven-help-plugin:3.5.1:effective-pom",
        "scripts/check-effective-pom.py",
        "docker pull",
        "PREPARE RESULT: PASS",
    ):
        if required not in prepare:
            add(f"prepare.sh 준비 계약이 빠졌습니다: {required}")
    if re.search(r"^\s*\./verify\.sh\s*$", prepare, re.MULTILINE):
        add("prepare.sh가 verify.sh를 직접 실행합니다.")

    for forbidden in ("dependency:go-offline", "docker pull"):
        if forbidden in verify:
            add(f"verify.sh가 준비 작업을 수행합니다: {forbidden}")
    for required in (
        "VERIFY_LOG",
        'DEFAULT_LOG="/tmp/guide-backend-spring-boot-verify-',
        "log_preflight_fail",
        "SUMMARY: passed=0 failed=1 skipped=0",
        "scripts/validate.py",
        "scripts/validator_self_test.py",
        "scripts/verify-skeletons.sh",
        "scripts/verify-workspaces.sh",
        "scripts/check-effective-pom.py",
        "maven-help-plugin:3.5.1:effective-pom",
        "--self-test",
        "dev.guides.spring.testinfra.NeverPullPolicy",
        '"$STATE_TOOL" copy',
        'cd "$WORK_TREE"',
        "RESULT: $result",
        '"$STATE_TOOL" capture',
        '"$STATE_TOOL" index-state',
        '"$STATE_TOOL" validate-marker',
        "snapshot_docker_managed",
        "remove_new_docker_resources",
        '"$RUNNER"',
    ):
        if required not in verify:
            add(f"verify.sh 전체 검사 계약이 빠졌습니다: {required}")
    skeleton_script = ROOT / "scripts/verify-skeletons.sh"
    if skeleton_script.is_file():
        skeleton_text = skeleton_script.read_text(encoding="utf-8")
        for exercise in EXPECTED_EXERCISES:
            if exercise not in skeleton_text:
                add(f"skeleton 지정 실패 계약이 빠졌습니다: {exercise}")
    workspace_files = {
        "scripts/new-workspace.sh": ("workspace.py", "create"),
        "scripts/check-workspace.sh": ("workspace.py", "validate", " -o "),
        "scripts/verify-workspaces.sh": tuple(sorted(EXPECTED_EXERCISES)),
    }
    for name, required_values in workspace_files.items():
        path = ROOT / name
        text = path.read_text(encoding="utf-8") if path.is_file() else ""
        for required in required_values:
            if required not in text:
                add(f"workspace 공개·검증 계약이 빠졌습니다: {name} -> {required}")
    runner_path = ROOT / "scripts/run_in_session.py"
    runner_text = runner_path.read_text(encoding="utf-8") if runner_path.is_file() else ""
    for required in (
        "os.setsid()",
        "signal.SIGHUP, signal.SIGINT, signal.SIGTERM",
        "signal.SIG_DFL",
        "os.execvp",
    ):
        if required not in runner_text:
            add(f"process-group signal helper 계약이 빠졌습니다: {required}")
    if re.search(r"^\s*\./prepare\.sh\s*$", verify, re.MULTILINE):
        add("verify.sh가 prepare.sh를 대신 실행합니다.")

    for forbidden in (
        "EXPECTED_REPOSITORY",
        "EXPECTED_BASE_COMMIT",
        "woopinbell/guide-backend-spring-boot",
    ):
        if forbidden in prepare or forbidden in verify:
            add(f"독립 branch를 깨는 저장소 결합이 남았습니다: {forbidden}")


def check_version_contract() -> None:
    root_path = ROOT / "pom.xml"
    root_pom = root_path.read_text(encoding="utf-8")
    tree = ET.parse(root_path)
    root = tree.getroot()
    namespace = {"m": "http://maven.apache.org/POM/4.0.0"}
    parent_version = xml_text(root, "./m:parent/m:version")
    if parent_version != "4.1.0":
        add(f"effective Spring Boot parent version이 다릅니다: {parent_version}")
    properties_element = root.find("./m:properties", namespace)
    properties: dict[str, str] = {}
    if properties_element is not None:
        for child in properties_element:
            properties[child.tag.rsplit("}", 1)[-1]] = (child.text or "").strip()
    required_properties = {
        "java.version": "21",
        "maven.compiler.release": "21",
        "testcontainers.version": "2.0.5",
        "avro.version": "1.12.1",
        "resilience4j.version": "2.4.0",
        "wiremock.version": "3.12.1",
        "kafka.version": "4.3.1",
    }
    for key, value in sorted(required_properties.items()):
        if properties.get(key) != value:
            add(
                f"root POM effective property가 다릅니다: {key} "
                f"예상={value}, 실제={properties.get(key)}"
            )

    plugin_versions = {
        element.text.strip()
        for element in root.findall(
            ".//m:plugin[m:artifactId='maven-surefire-plugin']/m:version", namespace
        )
        if element.text
    }
    # Spring Boot's parent owns the plugin version. A direct version here would
    # silently fork the platform baseline; plugin dependencies below use the
    # parent's effective properties explicitly.
    if plugin_versions:
        add("maven-surefire-plugin은 Spring Boot parent 관리 판본을 사용해야 합니다.")
    dependency_versions = {
        (
            xml_text(dependency, "./m:artifactId"),
            xml_text(dependency, "./m:version"),
        )
        for dependency in root.findall(".//m:dependency", namespace)
    }
    for required_dependency in {
        ("surefire-junit-platform", "${maven-surefire-plugin.version}"),
        ("junit-platform-launcher", "${junit-jupiter.version}"),
    }:
        if required_dependency not in dependency_versions:
            add(f"root POM effective dependency pin이 빠졌습니다: {required_dependency[0]}")

    all_text = "\n".join(
        path.read_text(encoding="utf-8")
        for path in source_files("*.xml") + source_files("*.java")
        + source_files("*.sh") + source_files("*.md")
    )
    forbidden_values = {
        "resilience4j-spring-boot3",
        "org.testcontainers.containers.PostgreSQLContainer",
        "<artifactId>junit-jupiter</artifactId>",
        "<artifactId>postgresql</artifactId><scope>test</scope>",
        "com.fasterxml.jackson.databind.ObjectMapper",
        "postgres:16-alpine",
        "redis:7-alpine",
    }
    for value in sorted(forbidden_values):
        if value in all_text:
            add(f"이전 stack 계약이 남았습니다: {value}")

    required_images = {
        "postgres:18.4-alpine@sha256:9a8afca54e7861fd90fab5fdf4c42477a6b1cb7d293595148e674e0a3181de15",
        "redis:8.8.0-alpine@sha256:9d317178eceac8454a2284a9e6df2466b93c745529947f0cd42a0fa9609d7005",
        "apache/kafka:4.3.1@sha256:77e3df9054047a88b520d0cc46e16696d3b22022e1d580aeccd2632df6532837",
        "testcontainers/ryuk:0.14.0@sha256:7c1a8a9a47c780ed0f983770a662f80deb115d95cce3e2daa3d12115b8cd28f0",
    }
    for image in sorted(required_images):
        if image not in all_text:
            add(f"immutable image 계약이 빠졌습니다: {image}")

    image_by_prefix = {
        "postgres:": next(image for image in required_images if image.startswith("postgres:")),
        "redis:": next(image for image in required_images if image.startswith("redis:")),
        "apache/kafka:": next(
            image for image in required_images if image.startswith("apache/kafka:")
        ),
        "testcontainers/ryuk:": next(
            image for image in required_images if image.startswith("testcontainers/ryuk:")
        ),
    }
    executable_image_counts = {image: 0 for image in required_images}
    for java_path in source_files("*.java"):
        java_text = java_path.read_text(encoding="utf-8")
        java_text = re.sub(
            r"//.*?$|/\*.*?\*/", "", java_text, flags=re.MULTILINE | re.DOTALL
        )
        for literal in re.findall(r'"([^"\n]+)"', java_text):
            for prefix, expected in image_by_prefix.items():
                if literal.startswith(prefix):
                    if literal != expected:
                        add(
                            "실행 Java 코드의 Docker image reference가 정확하지 않습니다: "
                            f"{relative(java_path)} -> {literal}"
                        )
                    else:
                        executable_image_counts[expected] += 1
    expected_java_image_counts = {
        image_by_prefix["postgres:"]: 6,
        image_by_prefix["redis:"]: 4,
        image_by_prefix["apache/kafka:"]: 2,
        image_by_prefix["testcontainers/ryuk:"]: 0,
    }
    if executable_image_counts != expected_java_image_counts:
        add(
            "실행 Java 코드의 immutable Docker image reference 수가 다릅니다: "
            f"예상={expected_java_image_counts}, 실제={executable_image_counts}"
        )

    shell_image_names = {
        "POSTGRES_IMAGE": image_by_prefix["postgres:"],
        "REDIS_IMAGE": image_by_prefix["redis:"],
        "KAFKA_IMAGE": image_by_prefix["apache/kafka:"],
        "RYUK_IMAGE": image_by_prefix["testcontainers/ryuk:"],
    }
    for shell_path in (ROOT / "prepare.sh", ROOT / "verify.sh"):
        shell_text = shell_path.read_text(encoding="utf-8")
        for name, expected in shell_image_names.items():
            match = re.search(rf'^{name}="([^"]+)"$', shell_text, re.MULTILINE)
            if match is None or match.group(1) != expected:
                add(f"{relative(shell_path)}의 {name} effective image pin이 다릅니다.")

    state_tree = ast.parse(
        (ROOT / "scripts/guide_state.py").read_text(encoding="utf-8")
    )
    state_image_refs: tuple[str, ...] | None = None
    for node in state_tree.body:
        if isinstance(node, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id == "IMAGE_REFS"
            for target in node.targets
        ):
            value = ast.literal_eval(node.value)
            if isinstance(value, tuple) and all(isinstance(item, str) for item in value):
                state_image_refs = value
    if state_image_refs is None or set(state_image_refs) != required_images \
            or len(state_image_refs) != len(required_images):
        add("guide_state.py의 effective IMAGE_REFS가 정확하지 않습니다.")
    artifact_ids: list[str] = []
    for pom_path in source_files("pom.xml"):
        pom_root = ET.parse(pom_path).getroot()
        artifact_ids.extend(
            element.text.strip()
            for element in pom_root.findall(".//m:dependency/m:artifactId", namespace)
            if element.text
        )
    if artifact_ids.count("spring-boot-flyway") != 6:
        add("Boot 4 Flyway 통합 모듈 선언은 DB 실습 양쪽에 6개여야 합니다.")
    if artifact_ids.count("flyway-database-postgresql") != 6:
        add("Flyway PostgreSQL database 모듈 선언은 DB 실습 양쪽에 6개여야 합니다.")
    if artifact_ids.count("testcontainers-kafka") != 2:
        add("Kafka 4.3.1 container 모듈 선언은 실습 양쪽에 2개여야 합니다.")
    if artifact_ids.count("spring-boot-starter-kafka") != 4:
        add("Boot 4 Kafka starter 선언은 Kafka 실습과 capstone 양쪽에 4개여야 합니다.")
    if artifact_ids.count("spring-boot-starter-restclient") != 4:
        add("Boot 4 RestClient starter 선언은 HTTP 실습과 capstone 양쪽에 4개여야 합니다.")
    if all_text.count("HttpClient.Version.HTTP_1_1") != 2:
        add("capstone WireMock 경계의 결정적 HTTP/1.1 설정은 양쪽에 2개여야 합니다.")
    if all_text.count('.asCompatibleSubstituteFor("postgres")') != 6:
        add("digest 고정 PostgreSQL Testcontainers 호환 선언은 6개여야 합니다.")
    if all_text.count('.asCompatibleSubstituteFor("apache/kafka")') != 2:
        add("digest 고정 Kafka Testcontainers 호환 선언은 2개여야 합니다.")


def check_project_independence() -> None:
    text_suffixes = {
        ".md",
        ".java",
        ".xml",
        ".yml",
        ".yaml",
        ".sql",
        ".avsc",
        ".py",
        ".sh",
    }
    for path in ROOT.rglob("*"):
        if not path.is_file() or path.suffix not in text_suffixes:
            continue
        if path.resolve() == Path(__file__).resolve():
            continue
        if runtime_excluded(path):
            continue
        text = path.read_text(encoding="utf-8")
        match = FORBIDDEN_DOMAIN_WORDS.search(text)
        if match:
            add(
                "특정 프로젝트를 연상시키는 표현이 남아 있습니다: "
                f"{relative(path)} ({match.group(0)})"
            )


def main() -> int:
    check_exact_repository_tree()
    check_markdown()
    check_learning_map()
    check_learning_handoffs()
    check_implementation_annotations()
    check_structured_files()
    check_java_sources()
    check_reference_completion()
    check_layout()
    check_wrapper()
    check_script_contracts()
    check_version_contract()
    check_project_independence()

    if ERRORS:
        print(f"검사 실패: {len(ERRORS)}건", file=sys.stderr)
        for error in ERRORS:
            print(f"- {error}", file=sys.stderr)
        return 1

    print("Spring Boot 가이드 문서·구조 검사 통과")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
