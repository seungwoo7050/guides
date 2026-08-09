#!/usr/bin/env python3
from __future__ import annotations

import re
import sys
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]
LINK = re.compile(r"!?\[[^\]]*\]\(([^)]+)\)")


def normalize_target(raw: str) -> str:
    target = raw.strip()
    if target.startswith("<") and ">" in target:
        target = target[1:target.index(">")]
    elif " " in target:
        # Markdown optional title follows whitespace. Repository paths contain no spaces.
        target = target.split(None, 1)[0]
    return unquote(target)


def main() -> int:
    failures: list[str] = []
    checked = 0
    for document in sorted(ROOT.rglob("*.md")):
        if any(part in {".git", ".guide", ".workspaces", "__pycache__"} for part in document.parts):
            continue
        text = document.read_text(encoding="utf-8")
        for raw in LINK.findall(text):
            target = normalize_target(raw)
            if not target or target.startswith(("#", "http://", "https://", "mailto:")):
                continue
            path_part = target.split("#", 1)[0]
            if not path_part:
                continue
            resolved = (document.parent / path_part).resolve()
            try:
                resolved.relative_to(ROOT.resolve())
            except ValueError:
                failures.append(f"{document.relative_to(ROOT)}: repository 밖 링크 {raw}")
                continue
            checked += 1
            if not resolved.exists():
                failures.append(f"{document.relative_to(ROOT)}: 깨진 링크 {raw}")
    if failures:
        for failure in failures:
            print(f"ERROR {failure}", file=sys.stderr)
        return 1
    print(f"PASS markdown links checked={checked}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
