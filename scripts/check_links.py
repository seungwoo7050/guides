#!/usr/bin/env python3
from __future__ import annotations

import re
import sys
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]
LINK_RE = re.compile(r'(?<!!)\[[^\]]*\]\(([^)]+)\)')
SKIP_PREFIXES = ('http://', 'https://', 'mailto:', '#')


def main() -> int:
    errors: list[str] = []
    checked = 0
    for document in sorted(ROOT.rglob('*.md')):
        if any(part in {'.guide', '.workspace'} for part in document.relative_to(ROOT).parts):
            continue
        checked += 1
        text = document.read_text(encoding='utf-8')
        for raw in LINK_RE.findall(text):
            target = raw.strip().split()[0].strip('<>')
            if target.startswith(SKIP_PREFIXES):
                continue
            path_part = unquote(target.split('#', 1)[0])
            if not path_part:
                continue
            resolved = (document.parent / path_part).resolve()
            try:
                resolved.relative_to(ROOT.resolve())
            except ValueError:
                errors.append(f'{document.relative_to(ROOT)}: 저장소 밖 링크 {target}')
                continue
            if not resolved.exists():
                errors.append(f'{document.relative_to(ROOT)}: 없는 링크 {target}')
    if errors:
        for error in errors:
            print(f'ERROR: {error}', file=sys.stderr)
        return 1
    print(f'links OK: {checked} Markdown files')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
