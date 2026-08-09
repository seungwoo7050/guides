#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from urllib.parse import unquote

LINK_RE = re.compile(r"!?(?:\[[^\]]*\])\(([^)]+)\)")
REQUIRED = [
    "README.md",
    "docs/00-roadmap.md",
    "docs/90-system-review.md",
    "exercises/model-lifecycle/README.md",
    "reference/glossary.md",
    "reference/reading-list.md",
]


def verify(root: Path) -> list[str]:
    errors: list[str] = []
    root = root.resolve()
    for relative in REQUIRED:
        if not (root / relative).is_file():
            errors.append(f"missing required file: {relative}")

    markdown_files = sorted(root.rglob("*.md"))
    if len(markdown_files) < 30:
        errors.append(f"expected at least 30 Markdown files, found {len(markdown_files)}")

    for path in markdown_files:
        text = path.read_text(encoding="utf-8")
        if "\r" in text:
            errors.append(f"CR character in {path.relative_to(root)}")
        for raw_target in LINK_RE.findall(text):
            target = raw_target.strip()
            if target.startswith("<") and target.endswith(">"):
                target = target[1:-1]
            target = target.split("#", 1)[0].strip()
            if not target or target.startswith(("http://", "https://", "mailto:", "data:")):
                continue
            if " " in target and not target.startswith("./") and not target.startswith("../"):
                # Markdown titles may follow a quoted target. This guide does not use them.
                target = target.split(" ", 1)[0]
            decoded = unquote(target)
            candidate = (path.parent / decoded).resolve()
            try:
                candidate.relative_to(root)
            except ValueError:
                errors.append(f"link escapes repository: {path.relative_to(root)} -> {raw_target}")
                continue
            if not candidate.exists():
                errors.append(f"broken link: {path.relative_to(root)} -> {raw_target}")

    for path in sorted(root.rglob("*.json")):
        if any(part == "workspace" for part in path.parts):
            continue
        try:
            json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:  # noqa: BLE001 - report all parse failures
            errors.append(f"invalid JSON: {path.relative_to(root)}: {exc}")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    errors = verify(args.root)
    if errors:
        for error in errors:
            print(f"ERROR {error}")
        return 1
    print("DOCS OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
