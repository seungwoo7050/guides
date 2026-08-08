#!/usr/bin/env python3
"""저장소 구조, 문서 링크, exercise 계약을 검증한다."""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]

EXPECTED_DOCS = [
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

EXERCISES = [
    "exercises/01-relational-semantics-and-design/01-sql-semantics",
    "exercises/01-relational-semantics-and-design/02-schema-and-constraints",
    "exercises/02-storage-and-indexes/01-slotted-page",
    "exercises/02-storage-and-indexes/02-bplus-tree",
    "exercises/02-storage-and-indexes/03-buffer-pool-clock",
    "exercises/03-transactions-and-recovery/01-postgres-isolation",
    "exercises/03-transactions-and-recovery/02-wal-recovery",
    "exercises/04-execution-and-optimization/01-join-algorithms",
    "exercises/04-execution-and-optimization/02-query-plans-and-indexes",
    "exercises/04-execution-and-optimization/03-safe-migration-and-backfill",
    "exercises/05-capstones/01-application-database-review",
    "exercises/05-capstones/02-mini-storage-engine",
]

LEGACY_PATHS = [
    *(f"docs/{index:02d}-{name}" for index, name in []),
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

LINK_RE = re.compile(r"(?<!!)\[[^\]]*\]\(([^)]+)\)")
FENCE_RE = re.compile(r"^```")


def fail(errors: list[str], message: str) -> None:
    errors.append(message)


def check_required_paths(errors: list[str]) -> None:
    for rel in EXPECTED_DOCS:
        if not (ROOT / rel).is_file():
            fail(errors, f"필수 문서 없음: {rel}")

    for rel in EXERCISES:
        path = ROOT / rel
        if not path.is_dir():
            fail(errors, f"필수 exercise 없음: {rel}")
            continue
        for child in ("README.md", "skeleton", "reference", "tests"):
            if not (path / child).exists():
                fail(errors, f"exercise 구성 누락: {rel}/{child}")

    for rel in LEGACY_PATHS:
        if (ROOT / rel).exists():
            fail(errors, f"prepare 후 남아서는 안 되는 경로: {rel}")


def check_markdown_contract(errors: list[str]) -> None:
    for rel in EXPECTED_DOCS:
        text = (ROOT / rel).read_text(encoding="utf-8")
        if not text.startswith("# "):
            fail(errors, f"문서 제목 누락: {rel}")
        if rel != "docs/00-roadmap.md":
            for heading in ("## 학습 목표", "## 연결 연습", "## 완료 기준"):
                if heading not in text:
                    fail(errors, f"문서 계약 heading 누락 ({heading}): {rel}")
        if "TODO" in text or "TBD" in text:
            fail(errors, f"완성 문서에 TODO/TBD가 남음: {rel}")


def iter_markdown_files() -> list[Path]:
    roots = [*sorted(ROOT.glob("*.md")), ROOT / "docs", ROOT / "exercises"]
    files: list[Path] = []
    for item in roots:
        if item.is_file():
            files.append(item)
        elif item.is_dir():
            files.extend(sorted(item.rglob("*.md")))
    return files


def check_links(errors: list[str]) -> None:
    for path in iter_markdown_files():
        in_fence = False
        for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if FENCE_RE.match(line.strip()):
                in_fence = not in_fence
                continue
            if in_fence:
                continue
            for raw_target in LINK_RE.findall(line):
                target = raw_target.strip().split()[0].strip("<>")
                if not target or target.startswith(("http://", "https://", "mailto:", "#")):
                    continue
                target = unquote(target.split("#", 1)[0])
                if not target:
                    continue
                resolved = (path.parent / target).resolve()
                try:
                    resolved.relative_to(ROOT)
                except ValueError:
                    fail(errors, f"저장소 밖 링크: {path.relative_to(ROOT)}:{line_no} -> {raw_target}")
                    continue
                if not resolved.exists():
                    fail(errors, f"깨진 링크: {path.relative_to(ROOT)}:{line_no} -> {raw_target}")


def check_reference_quality(errors: list[str]) -> None:
    for exercise in EXERCISES:
        base = ROOT / exercise
        reference_files = [p for p in (base / "reference").rglob("*") if p.is_file()]
        skeleton_files = [p for p in (base / "skeleton").rglob("*") if p.is_file()]
        test_files = [p for p in (base / "tests").rglob("*") if p.is_file()]
        if not reference_files:
            fail(errors, f"reference가 비어 있음: {exercise}")
        if not skeleton_files:
            fail(errors, f"skeleton이 비어 있음: {exercise}")
        if not test_files:
            fail(errors, f"tests가 비어 있음: {exercise}")
        for file in reference_files:
            if file.suffix in {".py", ".sql", ".sh"}:
                text = file.read_text(encoding="utf-8")
                if "TODO" in text or "NotImplementedError" in text:
                    fail(errors, f"reference에 미완성 표식: {file.relative_to(ROOT)}")


def check_executables(errors: list[str]) -> None:
    required = [ROOT / "prepare.sh", ROOT / "verify.sh"]
    required.extend(sorted((ROOT / "scripts").glob("*.sh")))
    required.extend(sorted((ROOT / "exercises").rglob("*.sh")))
    for path in required:
        rel = path.relative_to(ROOT)
        if not path.is_file():
            fail(errors, f"실행 스크립트 없음: {rel}")
        elif not os.access(path, os.X_OK):
            fail(errors, f"실행 권한 없음: {rel}")


def main() -> int:
    errors: list[str] = []
    check_required_paths(errors)
    check_markdown_contract(errors)
    check_links(errors)
    check_reference_quality(errors)
    check_executables(errors)

    if errors:
        for error in errors:
            print(f"[FAIL] {error}", file=sys.stderr)
        print(f"{len(errors)}개 구조 오류", file=sys.stderr)
        return 1

    print(f"[PASS] 구조: {len(EXPECTED_DOCS)}개 문서, {len(EXERCISES)}개 exercise")
    print("[PASS] Markdown 내부 링크")
    print("[PASS] skeleton/reference/tests 계약")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
