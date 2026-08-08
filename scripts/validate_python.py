#!/usr/bin/env python3
"""의존성을 import하지 않고 모든 Python 파일의 구문을 검사합니다."""

from __future__ import annotations

import ast
import io
from pathlib import Path
import re
import sys
import tokenize

ROOT = Path(__file__).resolve().parents[1]
errors: list[str] = []
files = sorted(ROOT.rglob("*.py"))
for path in files:
    try:
        source = path.read_text(encoding="utf-8")
        if "\x00" in source:
            errors.append(f"NUL 문자가 있습니다: {path.relative_to(ROOT)}")
            continue
        ast.parse(source, filename=str(path))
        for token in tokenize.generate_tokens(io.StringIO(source).readline):
            if token.type != tokenize.COMMENT or token.string.startswith("#!"):
                continue
            comment = token.string.removeprefix("#").strip()
            if re.search(r"[A-Za-z]{2,}", comment) and not re.search(r"[가-힣]", comment):
                errors.append(
                    "영문으로만 작성된 Python 주석입니다: "
                    f"{path.relative_to(ROOT)}:{token.start[0]}"
                )
    except (OSError, SyntaxError, UnicodeError) as error:
        errors.append(f"{path.relative_to(ROOT)}: {error}")

for path in sorted(ROOT.rglob("*.sh")):
    try:
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            stripped = line.strip()
            if not stripped.startswith("#") or stripped.startswith("#!"):
                continue
            comment = stripped.removeprefix("#").strip()
            if comment.startswith("shellcheck "):
                continue
            if re.search(r"[A-Za-z]{2,}", comment) and not re.search(r"[가-힣]", comment):
                errors.append(
                    f"영문으로만 작성된 셸 주석입니다: {path.relative_to(ROOT)}:{number}"
                )
    except (OSError, UnicodeError) as error:
        errors.append(f"{path.relative_to(ROOT)}: {error}")

if errors:
    print(f"Python·셸 소스 검사 실패: {len(errors)}건", file=sys.stderr)
    for error in errors:
        print(f"- {error}", file=sys.stderr)
    raise SystemExit(1)
print(f"Python·셸 소스 검사 통과: Python {len(files)}개")
