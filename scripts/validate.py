#!/usr/bin/env python3
"""Validate the exact guide layout, pedagogy, links, modes, and version pins."""

from __future__ import annotations

import os
import re
import stat
import sys
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(os.environ.get("GUIDE_ROOT", Path(__file__).resolve().parents[1])).resolve()
LAYOUT_MANIFEST = ROOT / "scripts/layout-manifest.txt"
EXERCISE_MANIFEST = ROOT / "scripts/exercises.txt"
LINK_RE = re.compile(r"(?<!!)\[[^\]]*\]\(([^)]+)\)")
FENCE_RE = re.compile(r"^```")
GENERATED_ROOTS = {".git", ".guide", ".verify"}
GENERATED_PARTS = {"__pycache__", ".pytest_cache"}
DOCS = [
    "docs/00-roadmap.md",
    "docs/01-relational-semantics-and-design/01-relational-model-and-algebra.md",
    "docs/01-relational-semantics-and-design/02-sql-semantics-and-query-shape.md",
    "docs/01-relational-semantics-and-design/03-er-normalization-and-constraints.md",
    "docs/02-storage-and-indexes/01-pages-records-and-files.md",
    "docs/02-storage-and-indexes/02-index-structures.md",
    "docs/02-storage-and-indexes/03-buffer-pool-and-replacement.md",
    "docs/03-transactions-and-recovery/01-transactions-isolation-and-locks.md",
    "docs/03-transactions-and-recovery/02-mvcc-wal-and-recovery.md",
    "docs/04-execution-and-optimization/01-query-execution-joins-and-sorting.md",
    "docs/04-execution-and-optimization/02-statistics-cost-model-and-explain.md",
    "docs/04-execution-and-optimization/03-schema-index-and-tuning-loop.md",
    "docs/05-capstones/01-application-database-review.md",
    "docs/05-capstones/02-mini-storage-engine.md",
    "docs/90-system-review.md",
]
LEGACY_PATHS = [
    "docs/01-relational-model-and-algebra.md",
    "docs/02-sql-semantics-and-query-shape.md",
    "docs/03-er-model-normalization-and-constraints.md",
    "docs/04-pages-records-and-file-organization.md",
    "docs/05-index-structures-btree-hash-brin.md",
    "docs/06-buffer-pool-and-replacement.md",
    "docs/07-transactions-isolation-and-locks.md",
    "docs/08-mvcc-wal-and-recovery.md",
    "docs/09-query-execution-joins-and-sorting.md",
    "docs/10-statistics-cost-model-and-explain.md",
    "docs/11-schema-index-and-tuning-loop.md",
    "docs/12-database-system-review.md",
    "exercises/buffer-pool-clock",
    "exercises/isolation-and-recovery",
    "exercises/join-algorithms",
    "exercises/slotted-page",
    "exercises/storage-index",
    "reference",
]


def fail(errors: list[str], message: str) -> None:
    errors.append(message)


def load_lines(path: Path) -> list[str]:
    return [line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def should_ignore(relative: Path) -> bool:
    parts = relative.parts
    if parts and parts[0] in GENERATED_ROOTS:
        return True
    if any(part in GENERATED_PARTS for part in parts) or relative.suffix in {".pyc", ".pyo"}:
        return True
    # Learner workspaces are generated only at
    # exercises/<stage>/<exercise>/workspace (or its atomic temporary peer).
    return (
        len(parts) >= 4
        and parts[0] == "exercises"
        and (parts[3] == "workspace" or parts[3].startswith("workspace.tmp."))
    )


def check_exact_tree(errors: list[str]) -> None:
    if not LAYOUT_MANIFEST.is_file():
        fail(errors, "exact-tree manifest 없음: scripts/layout-manifest.txt")
        return
    expected = load_lines(LAYOUT_MANIFEST)
    if expected != sorted(set(expected)):
        fail(errors, "layout manifest는 중복 없이 정렬되어야 함")
    actual: list[str] = []
    for path in ROOT.rglob("*"):
        relative = path.relative_to(ROOT)
        if should_ignore(relative):
            continue
        mode = path.lstat().st_mode
        if stat.S_ISLNK(mode):
            fail(errors, f"source tree symlink 금지: {relative}")
            actual.append(relative.as_posix())
        elif stat.S_ISREG(mode):
            actual.append(relative.as_posix())
        elif not stat.S_ISDIR(mode):
            fail(errors, f"source tree 특수 파일 금지: {relative}")
    actual.sort()
    missing = sorted(set(expected) - set(actual))
    unexpected = sorted(set(actual) - set(expected))
    for relative in missing:
        fail(errors, f"exact-tree 필수 파일 없음: {relative}")
    for relative in unexpected:
        fail(errors, f"exact-tree 예상 밖 파일: {relative}")


def exercises(errors: list[str]) -> list[str]:
    if not EXERCISE_MANIFEST.is_file():
        fail(errors, "exercise manifest 없음")
        return []
    values = load_lines(EXERCISE_MANIFEST)
    if values != sorted(set(values)):
        fail(errors, "exercise manifest는 중복 없이 정렬되어야 함")
    return values


def section(text: str, heading: str) -> str:
    match = re.search(rf"(?ms)^{re.escape(heading)}\s*$\n(.*?)(?=^##\s|\Z)", text)
    return match.group(1).strip() if match else ""


def check_required_and_pedagogy(errors: list[str], exercise_paths: list[str]) -> None:
    for relative in DOCS:
        path = ROOT / relative
        if not path.is_file():
            fail(errors, f"필수 문서 없음: {relative}")
            continue
        text = path.read_text(encoding="utf-8")
        if not text.startswith("# "):
            fail(errors, f"문서 H1 누락: {relative}")
        if relative != "docs/00-roadmap.md":
            for heading in ("## 학습 목표", "## 연결 연습", "## 완료 기준"):
                if heading not in text:
                    fail(errors, f"문서 heading 누락 ({heading}): {relative}")
        if re.search(r"\b(?:TODO|TBD)\b", text):
            fail(errors, f"완성 문서 TODO/TBD 금지: {relative}")

    completion_bodies: set[str] = set()
    explanation_bodies: set[str] = set()
    required_headings = ("## 목표", "## 완료 기준", "## 자기 설명", "## 검증")
    for relative in exercise_paths:
        base = ROOT / relative
        for child in ("README.md", "skeleton", "reference", "tests"):
            if not (base / child).exists():
                fail(errors, f"exercise 구성 누락: {relative}/{child}")
        readme = base / "README.md"
        if not readme.is_file():
            continue
        text = readme.read_text(encoding="utf-8")
        positions = [
            match.start() if (match := re.search(rf"(?m)^{re.escape(heading)}\s*$", text)) else -1
            for heading in required_headings
        ]
        if any(position < 0 for position in positions):
            fail(errors, f"학습 heading 누락: {relative}")
            continue
        if positions != sorted(positions):
            fail(errors, f"학습 heading 순서 오류: {relative}")
        completion = section(text, "## 완료 기준")
        explanation = section(text, "## 자기 설명")
        verification = section(text, "## 검증")
        if len(re.findall(r"(?m)^- ", completion)) < 3:
            fail(errors, f"관찰 가능한 완료 기준 3개 미만: {relative}")
        questions = re.findall(r"(?m)^\d+\. (.+)$", explanation)
        if len(questions) < 2 or not all(question.rstrip().endswith("?") for question in questions):
            fail(errors, f"자기 설명 질문 2개 미만: {relative}")
        canonical_command = f"./scripts/check-workspace.sh {relative}"
        if canonical_command not in verification:
            fail(errors, f"실행 가능한 검증 명령 누락: {relative}")
        normalized_completion = re.sub(r"\s+", " ", completion).casefold()
        normalized_explanation = re.sub(r"\s+", " ", explanation).casefold()
        if normalized_completion in completion_bodies:
            fail(errors, f"복사형 완료 기준: {relative}")
        if normalized_explanation in explanation_bodies:
            fail(errors, f"복사형 자기 설명: {relative}")
        completion_bodies.add(normalized_completion)
        explanation_bodies.add(normalized_explanation)

    for relative in LEGACY_PATHS:
        if os.path.lexists(ROOT / relative):
            fail(errors, f"legacy 경로 잔존: {relative}")


def markdown_files() -> list[Path]:
    return sorted(path for path in ROOT.rglob("*.md") if not should_ignore(path.relative_to(ROOT)))


def heading_slugs(path: Path) -> set[str]:
    counts: dict[str, int] = {}
    slugs: set[str] = set()
    in_fence = False
    for line in path.read_text(encoding="utf-8").splitlines():
        if FENCE_RE.match(line.strip()):
            in_fence = not in_fence
            continue
        if in_fence or not re.match(r"^#{1,6}\s+", line):
            continue
        heading = re.sub(r"^#{1,6}\s+", "", line).strip().casefold()
        heading = re.sub(r"[`*_~]", "", heading)
        heading = re.sub(r"[^\w\-\s]", "", heading, flags=re.UNICODE)
        slug = re.sub(r"\s+", "-", heading).strip("-")
        count = counts.get(slug, 0)
        counts[slug] = count + 1
        slugs.add(slug if count == 0 else f"{slug}-{count}")
    return slugs


def check_links(errors: list[str]) -> None:
    for path in markdown_files():
        in_fence = False
        for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if FENCE_RE.match(line.strip()):
                in_fence = not in_fence
                continue
            if in_fence:
                continue
            for raw_target in LINK_RE.findall(line):
                target = raw_target.strip().split()[0].strip("<>")
                if not target or target.startswith(("http://", "https://", "mailto:")):
                    continue
                decoded = unquote(target)
                file_part, _, fragment = decoded.partition("#")
                resolved = path if not file_part else (path.parent / file_part).resolve()
                try:
                    resolved.relative_to(ROOT)
                except ValueError:
                    fail(errors, f"저장소 밖 링크: {path.relative_to(ROOT)}:{line_no} -> {raw_target}")
                    continue
                if not resolved.exists():
                    fail(errors, f"깨진 링크: {path.relative_to(ROOT)}:{line_no} -> {raw_target}")
                    continue
                if fragment and resolved.suffix.lower() == ".md" and fragment not in heading_slugs(resolved):
                    fail(errors, f"깨진 anchor: {path.relative_to(ROOT)}:{line_no} -> {raw_target}")


def check_reference_and_tests(errors: list[str], exercise_paths: list[str]) -> None:
    for relative in exercise_paths:
        base = ROOT / relative
        for kind in ("reference", "skeleton", "tests"):
            files = [path for path in (base / kind).rglob("*") if path.is_file()]
            if not files:
                fail(errors, f"{kind}가 비어 있음: {relative}")
        for path in (base / "reference").rglob("*"):
            if path.is_file() and path.suffix in {".py", ".sql", ".sh"}:
                text = path.read_text(encoding="utf-8")
                if re.search(r"\bTODO\b|NotImplementedError", text):
                    fail(errors, f"reference 미완성 표식: {path.relative_to(ROOT)}")


def check_files_and_modes(errors: list[str]) -> None:
    for path in ROOT.rglob("*"):
        relative = path.relative_to(ROOT)
        if should_ignore(relative) or not path.is_file():
            continue
        raw = path.read_bytes()
        if b"\x00" in raw:
            fail(errors, f"NUL byte 금지: {relative}")
            continue
        if b"\r\n" in raw:
            fail(errors, f"CRLF 금지: {relative}")
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError:
            fail(errors, f"UTF-8 아님: {relative}")
            continue
        for line_no, line in enumerate(text.splitlines(), 1):
            if line.rstrip(" \t") != line:
                fail(errors, f"trailing whitespace: {relative}:{line_no}")
    required_executable = {"prepare.sh", "verify.sh"}
    required_executable.update(path.relative_to(ROOT).as_posix() for path in (ROOT / "scripts").glob("*.sh"))
    required_executable.update(path.relative_to(ROOT).as_posix() for path in (ROOT / "exercises").rglob("*.sh"))
    for relative in sorted(required_executable):
        path = ROOT / relative
        if not path.is_file() or not os.access(path, os.X_OK):
            fail(errors, f"실행 권한 누락: {relative}")


def check_version_contract(errors: list[str]) -> None:
    prepare = (ROOT / "prepare.sh").read_text(encoding="utf-8")
    required = (
        "postgres:18.4-alpine@sha256:9a8afca54e7861fd90fab5fdf4c42477a6b1cb7d293595148e674e0a3181de15",
        'GUIDE_ID="database-systems"',
        "prepared.json",
        "PREPARE RESULT: PASS",
    )
    for token in required:
        if token not in prepare:
            fail(errors, f"prepare version/marker 계약 누락: {token}")
    forbidden = ("woopinbell/", "EXPECTED_BASE_COMMIT", "postgres:16", "prepared.env")
    for token in forbidden:
        for path in (ROOT / "prepare.sh", ROOT / "verify.sh", ROOT / "scripts/run-postgres-exercises.sh"):
            if token in path.read_text(encoding="utf-8"):
                fail(errors, f"legacy prepare 계약 잔존 ({token}): {path.relative_to(ROOT)}")


def require_tokens(errors: list[str], relative: str, tokens: tuple[str, ...], contract: str) -> None:
    path = ROOT / relative
    if not path.is_file():
        return
    text = path.read_text(encoding="utf-8")
    for token in tokens:
        if token not in text:
            fail(errors, f"{contract} 누락 ({token}): {relative}")


def check_public_and_capstone_contract(errors: list[str]) -> None:
    require_tokens(
        errors,
        "README.md",
        ("make prepare", "make check", "make verify", "make clean"),
        "공개 make 명령 계약",
    )
    require_tokens(
        errors,
        "CONTRIBUTING.md",
        (
            "make prepare\n",
            "make check\n",
            "VERIFY_LOG=/tmp/database-systems-verify.log make verify\n",
            "make clean\n",
        ),
        "기여 안내 공개 make 명령 계약",
    )
    require_tokens(
        errors,
        "scripts/check-workspace.sh",
        (
            'PYTHONPATH="$workspace"',
            "python3 -m unittest discover",
            '"$ROOT/scripts/run-postgres-exercises.sh" --workspace "$requested"',
            "[PASS] learner workspace",
        ),
        "workspace checker 계약",
    )
    require_tokens(
        errors,
        "scripts/run-postgres-exercises.sh",
        (
            "exercises/01-relational-semantics-and-design/01-sql-semantics",
            "exercises/01-relational-semantics-and-design/02-schema-and-constraints",
            "exercises/03-transactions-and-recovery/01-postgres-isolation",
            "exercises/04-execution-and-optimization/02-query-plans-and-indexes",
            "exercises/04-execution-and-optimization/03-safe-migration-and-backfill",
            "exercises/05-capstones/01-application-database-review",
            "--workspace",
            "learner workspace designated start-state",
            "run_capstone_index_runtime_mutant",
            "queue index definition mismatch",
        ),
        "PostgreSQL workspace dispatcher 계약",
    )
    require_tokens(
        errors,
        "exercises/05-capstones/01-application-database-review/reference/queries.sql",
        ("q_org_open_tickets", "q_assignee_queue", "q_project_backlog"),
        "application capstone workload 계약",
    )
    require_tokens(
        errors,
        "exercises/05-capstones/01-application-database-review/reference/indexes.sql",
        (
            "ON tickets(org_id, priority DESC, created_at DESC, id DESC)",
            "ON tickets(org_id, assignee_id, priority DESC, created_at, id)",
            "ON tickets(org_id, project_id, created_at, id)",
            "WHERE status <> 'DONE'",
        ),
        "application capstone index 계약",
    )
    require_tokens(
        errors,
        "exercises/05-capstones/01-application-database-review/tests/verify.sh",
        (
            "pg_get_indexdef",
            "EXPLAIN (ANALYZE, COSTS OFF, TIMING OFF, SUMMARY OFF)",
            "tickets_org_open_priority_created_idx",
            "tickets_assignee_queue_idx",
            "tickets_project_open_created_idx",
            "plan contains an explicit Sort",
            "concurrency review remains scaffold",
            "concurrency review SQL evidence fewer than 3 lines",
        ),
        "application capstone plan 계약",
    )
    require_tokens(
        errors,
        "exercises/05-capstones/01-application-database-review/tests/verify.sql",
        (
            "ORDER BY priority DESC, created_at DESC, id DESC",
            "(priority, created_at, id)",
            "ORDER BY priority DESC, created_at, id",
            "organization keyset page mismatch",
        ),
        "application capstone result 계약",
    )
    require_tokens(
        errors,
        "exercises/05-capstones/01-application-database-review/reference/concurrency-review.md",
        ("자동 SQL fixture가 보장하는 범위", "두 session 순서", "bounded retry", "application 책임"),
        "application capstone concurrency 산출물",
    )
    require_tokens(
        errors,
        "exercises/05-capstones/02-mini-storage-engine/reference/mini_storage.py",
        ("class OrderedLeafIndex", "self.index = OrderedLeafIndex()"),
        "ordered leaf index 명칭 계약",
    )

    forbidden_docs = (
        "guide-web-applications",
        "guide-backend-spring-boot",
        "guide-distributed-services",
        "guide-web-infrastructure",
        "PostgreSQL 16",
    )
    for path in markdown_files():
        text = path.read_text(encoding="utf-8")
        for token in forbidden_docs:
            if token in text:
                fail(errors, f"stale guides/버전 참조 ({token}): {path.relative_to(ROOT)}")
    mini_reference = ROOT / "exercises/05-capstones/02-mini-storage-engine/reference/mini_storage.py"
    if mini_reference.is_file() and "BPlusTreeIndex" in mini_reference.read_text(encoding="utf-8"):
        fail(errors, "ordered leaf index를 B+ tree로 과장함: exercises/05-capstones/02-mini-storage-engine/reference/mini_storage.py")


def main() -> int:
    errors: list[str] = []
    check_exact_tree(errors)
    exercise_paths = exercises(errors)
    check_required_and_pedagogy(errors, exercise_paths)
    check_links(errors)
    check_reference_and_tests(errors, exercise_paths)
    check_files_and_modes(errors)
    check_version_contract(errors)
    check_public_and_capstone_contract(errors)
    if errors:
        for message in errors:
            print(f"[FAIL] {message}", file=sys.stderr)
        print(f"[FAIL] validator: {len(errors)} errors", file=sys.stderr)
        return 1
    print(f"[PASS] exact tree: {len(load_lines(LAYOUT_MANIFEST))} files")
    print(f"[PASS] pedagogy: {len(DOCS)} docs, {len(exercise_paths)} tailored exercises")
    print("[PASS] links, anchors, modes, reference quality, PostgreSQL 18.4 pin")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
