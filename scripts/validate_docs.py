#!/usr/bin/env python3
from __future__ import annotations

import re
import sys
import unicodedata
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parent.parent
MARKDOWN = sorted(
    path for path in ROOT.rglob("*.md")
    if ".git" not in path.parts and "build" not in path.parts
)
REQUIRED = (
    ROOT / "docs/00-roadmap.md",
    ROOT / "docs/01-foundations",
    ROOT / "docs/02-c-language",
    ROOT / "docs/03-unix-programming",
    ROOT / "docs/04-concurrency",
    ROOT / "docs/90-appendix",
    ROOT / "exercises/Makefile",
)
LINK_RE = re.compile(r"!?\[[^\]]*\]\(([^)]+)\)")
HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$")


def die(path: Path, message: str) -> None:
    try:
        relative = path.relative_to(ROOT)
    except ValueError:
        relative = path
    print(f"문서 검사 실패: {relative}: {message}", file=sys.stderr)
    raise SystemExit(1)


def slugify(text: str) -> str:
    text = re.sub(r"`([^`]*)`", r"\1", text)
    text = re.sub(r"<[^>]+>", "", text)
    text = unicodedata.normalize("NFKC", text).strip().lower()
    text = re.sub(r"[^\w\-\s가-힣]", "", text)
    text = re.sub(r"[\s_]+", "-", text)
    return text.strip("-")


def outside_fence_lines(path: Path) -> list[tuple[int, str]]:
    lines: list[tuple[int, str]] = []
    fence_marker: str | None = None
    fence_length = 0
    for line_number, line in enumerate(
        path.read_text(encoding="utf-8").splitlines(), start=1
    ):
        stripped = line.lstrip()
        match = re.match(r"(`{3,}|~{3,})", stripped)
        if match:
            marker = match.group(1)
            if fence_marker is None:
                fence_marker = marker[0]
                fence_length = len(marker)
            elif marker[0] == fence_marker and len(marker) >= fence_length:
                fence_marker = None
                fence_length = 0
            continue
        if fence_marker is None:
            lines.append((line_number, line))
    if fence_marker is not None:
        die(path, "닫히지 않은 코드 블록이 있습니다")
    return lines


def anchors(path: Path) -> set[str]:
    result: set[str] = set()
    seen: dict[str, int] = {}
    for _, line in outside_fence_lines(path):
        match = HEADING_RE.match(line)
        if not match:
            continue
        base = slugify(match.group(2))
        count = seen.get(base, 0)
        seen[base] = count + 1
        result.add(base if count == 0 else f"{base}-{count}")
    return result


def check_link(source: Path, raw_target: str) -> None:
    target = raw_target.strip()
    if not target or target.startswith(("http://", "https://", "mailto:")):
        return
    if target.startswith("<") and target.endswith(">"):
        target = target[1:-1]
    path_text, separator, fragment = target.partition("#")
    path_text = unquote(path_text)
    destination = source if not path_text else (source.parent / path_text).resolve()
    try:
        destination.relative_to(ROOT)
    except ValueError:
        die(source, f"저장소 밖을 가리키는 연결입니다: {raw_target}")
    if not destination.exists():
        die(source, f"연결 대상이 없습니다: {raw_target}")
    if separator and fragment and destination.is_file() and destination.suffix == ".md":
        expected = unquote(fragment).lower()
        if expected not in anchors(destination):
            die(source, f"제목 앵커가 없습니다: {raw_target}")


def check_document(path: Path) -> None:
    outside = outside_fence_lines(path)
    h1 = [line for _, line in outside if line.startswith("# ")]
    if len(h1) != 1:
        die(path, f"최상위 제목이 1개여야 합니다(현재 {len(h1)}개)")
    for line_number, line in outside:
        if "\t" in line:
            die(path, f"본문 {line_number}행에 탭 문자가 있습니다")
    visible_text = "\n".join(line for _, line in outside)
    for target in LINK_RE.findall(visible_text):
        check_link(path, target)


def main() -> None:
    for required in REQUIRED:
        if not required.exists():
            die(required, "필수 경로가 없습니다")
    if not MARKDOWN:
        die(ROOT, "Markdown 문서가 없습니다")
    for document in MARKDOWN:
        check_document(document)
    print(f"문서 검사 통과: {len(MARKDOWN)}개")


if __name__ == "__main__":
    main()
