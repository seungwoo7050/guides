#!/usr/bin/env python3
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STUB = re.compile(r"\b(?:TODO|TBD|FIXME|lorem ipsum)\b", re.IGNORECASE)


def main() -> int:
    failures: list[str] = []
    core: list[Path] = []
    for path in sorted((ROOT / "docs").glob("[0-9][0-9]-*/*.md")):
        prefix = path.name.split("-", 1)[0]
        if prefix.isdigit() and 1 <= int(prefix) <= 22:
            core.append(path)
    for path in core:
        text = path.read_text(encoding="utf-8")
        relative = path.relative_to(ROOT)
        lines = text.splitlines()
        if not lines or not lines[0].startswith("# "):
            failures.append(f"{relative}: H1 제목 없음")
        if "## 학습 목표" not in text:
            failures.append(f"{relative}: 학습 목표 없음")
        if len(text) < 2_000:
            failures.append(f"{relative}: 개념 문서가 지나치게 짧음 ({len(text)} chars)")
        if "```" not in text:
            failures.append(f"{relative}: 상태·구조 예제 code block 없음")
        if STUB.search(text):
            failures.append(f"{relative}: stub marker 발견")
    roadmap = (ROOT / "docs/00-roadmap.md").read_text(encoding="utf-8")
    for number in range(1, 23):
        if f"{number}. [" not in roadmap:
            failures.append(f"roadmap: 문서 번호 {number} 링크 없음")
    if failures:
        for failure in failures:
            print(f"ERROR {failure}", file=sys.stderr)
        return 1
    print(f"PASS docs core={len(core)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
