#!/usr/bin/env python3
"""최종 가이드 구조와 로컬 Markdown 링크를 표준 라이브러리만으로 검사합니다."""

from __future__ import annotations

import re
import sys
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]

EXPECTED_DOCS = (
    "docs/00-roadmap.md",
    "docs/01-language-and-runtime/01-runtime-and-environment.md",
    "docs/01-language-and-runtime/02-objects-and-collections.md",
    "docs/01-language-and-runtime/03-functions-errors-and-types.md",
    "docs/01-language-and-runtime/04-iterators-generators-and-context-managers.md",
    "docs/02-automation/01-files-structured-data-and-cli.md",
    "docs/02-automation/02-subprocess-and-process-lifecycle.md",
    "docs/02-automation/03-concurrency-and-cancellation.md",
    "docs/03-quality/01-testing.md",
    "docs/03-quality/02-project-structure-packaging-and-typing.md",
    "docs/03-quality/03-cli-test-runner.md",
)

OLD_DOCS = (
    "docs/01-runtime-and-environment.md",
    "docs/02-objects-and-collections.md",
    "docs/03-functions-errors-and-types.md",
    "docs/04-files-and-cli.md",
    "docs/05-subprocess-and-automation.md",
    "docs/06-testing.md",
    "docs/07-cli-test-runner.md",
    "docs/08-algorithms-and-project-quality.md",
)

LINK_PATTERN = re.compile(r"!?\[[^\]]*\]\(([^)]+)\)")
HEADING_PATTERN = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
CODE_FENCE_PATTERN = re.compile(r"^\s*(```|~~~)")


def github_slug(text: str) -> str:
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"[`*_~]", "", text)
    text = text.strip().lower()
    text = re.sub(r"[^\w\-\s가-힣]", "", text, flags=re.UNICODE)
    return re.sub(r"[\s]+", "-", text)


def headings(path: Path) -> set[str]:
    result: set[str] = set()
    counts: dict[str, int] = {}
    in_fence = False
    for line in path.read_text(encoding="utf-8").splitlines():
        if CODE_FENCE_PATTERN.match(line):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        match = HEADING_PATTERN.match(line)
        if match is None:
            continue
        base = github_slug(match.group(2))
        if not base:
            continue
        count = counts.get(base, 0)
        counts[base] = count + 1
        result.add(base if count == 0 else f"{base}-{count}")
    return result


def link_target(raw: str) -> tuple[str, str]:
    value = raw.strip()
    if value.startswith("<") and value.endswith(">"):
        value = value[1:-1]
    if " " in value and not value.startswith("#"):
        value = value.split(" ", 1)[0]
    parsed = urlsplit(value)
    return unquote(parsed.path), unquote(parsed.fragment)


def markdown_files() -> list[Path]:
    roots = [ROOT / "README.md", ROOT / "CONTRIBUTING.md"]
    roots.extend(sorted((ROOT / "docs").rglob("*.md")))
    roots.extend(sorted((ROOT / "exercises").rglob("*.md")))
    return [path for path in roots if path.is_file()]


def main() -> int:
    errors: list[str] = []

    for relative in EXPECTED_DOCS:
        if not (ROOT / relative).is_file():
            errors.append(f"필수 문서 누락: {relative}")
    for relative in OLD_DOCS:
        if (ROOT / relative).exists():
            errors.append(f"이전 문서 경로가 남아 있습니다: {relative}")

    roadmap = (ROOT / "docs/00-roadmap.md").read_text(encoding="utf-8")
    for relative in EXPECTED_DOCS[1:]:
        target = Path(relative).relative_to("docs")
        expected_link = str(target).replace("\\", "/")
        if expected_link not in roadmap:
            errors.append(f"roadmap에 문서가 없습니다: {relative}")

    heading_cache: dict[Path, set[str]] = {}
    for source in markdown_files():
        text = source.read_text(encoding="utf-8")
        in_fence = False
        for line_number, line in enumerate(text.splitlines(), start=1):
            if CODE_FENCE_PATTERN.match(line):
                in_fence = not in_fence
                continue
            if in_fence:
                continue
            for match in LINK_PATTERN.finditer(line):
                raw = match.group(1)
                if raw.startswith(("http://", "https://", "mailto:")):
                    continue
                path_text, fragment = link_target(raw)
                if path_text.startswith("/"):
                    errors.append(
                        f"{source.relative_to(ROOT)}:{line_number}: 절대 로컬 경로는 사용할 수 없습니다: {raw}"
                    )
                    continue
                target = source if not path_text else (source.parent / path_text).resolve()
                try:
                    target.relative_to(ROOT)
                except ValueError:
                    errors.append(
                        f"{source.relative_to(ROOT)}:{line_number}: 저장소 밖 링크: {raw}"
                    )
                    continue
                if not target.exists():
                    errors.append(
                        f"{source.relative_to(ROOT)}:{line_number}: 대상 없음: {raw}"
                    )
                    continue
                if fragment and target.is_file() and target.suffix.lower() == ".md":
                    available = heading_cache.setdefault(target, headings(target))
                    if fragment.lower() not in available:
                        errors.append(
                            f"{source.relative_to(ROOT)}:{line_number}: 제목 anchor 없음: {raw}"
                        )

    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        print(f"문서 검사 실패: {len(errors)}건", file=sys.stderr)
        return 1

    print(f"문서 검사 통과: {len(markdown_files())}개 Markdown 파일")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
