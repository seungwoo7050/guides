#!/usr/bin/env python3
from __future__ import annotations

import re
import sys
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]
LINK_RE = re.compile(r'(?<!!)\[[^\]]*\]\(([^)]+)\)')
IGNORED_PREFIXES = ('http://', 'https://', 'mailto:', '#')


def main() -> int:
    errors: list[str] = []
    markdown_files = sorted(ROOT.rglob('*.md'))
    for path in markdown_files:
        text = path.read_text(encoding='utf-8')
        for match in LINK_RE.finditer(text):
            raw_target = match.group(1).strip()
            if not raw_target or raw_target.startswith(IGNORED_PREFIXES):
                continue
            target = raw_target.split()[0].strip('<>')
            target = unquote(target.split('#', 1)[0])
            if not target:
                continue
            resolved = (path.parent / target).resolve()
            try:
                resolved.relative_to(ROOT.resolve())
            except ValueError:
                errors.append(f'{path.relative_to(ROOT)}: link escapes repository: {raw_target}')
                continue
            if not resolved.exists():
                errors.append(f'{path.relative_to(ROOT)}: missing link target: {raw_target}')
    if errors:
        for error in errors:
            print(f'ERROR: {error}', file=sys.stderr)
        return 1
    print(f'links OK: {len(markdown_files)} Markdown files')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
