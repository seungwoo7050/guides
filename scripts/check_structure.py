#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

REQUIRED = [
    "README.md",
    "CONTRIBUTING.md",
    "LICENSE.md",
    "LICENSES/MIT.txt",
    "LICENSES/CC-BY-4.0.txt",
    "Makefile",
    "prepare.sh",
    "verify.sh",
    "docs/00-roadmap.md",
    "docs/08-mica-capstone.md",
    "exercises/README.md",
    "exercises/08-mica-capstone/README.md",
    "exercises/08-mica-capstone/spec/language.md",
    "exercises/08-mica-capstone/spec/grammar.ebnf",
    "exercises/08-mica-capstone/spec/diagnostics.md",
    "exercises/08-mica-capstone/spec/conformance.md",
    "exercises/08-mica-capstone/spec/bytecode.md",
    "exercises/08-mica-capstone/fixtures/manifest.json",
    "exercises/08-mica-capstone/skeleton/src/mica/__main__.py",
    "exercises/08-mica-capstone/check_submission.py",
    "exercises/01-source-and-diagnostics/check.py",
    "exercises/01-source-and-diagnostics/fixtures/source-cases.json",
    "exercises/01-source-and-diagnostics/reference/unicode-diagnostic.json",
    "exercises/02-lexer-parser-and-ast/check.py",
    "exercises/02-lexer-parser-and-ast/fixtures/expressions.json",
    "exercises/02-lexer-parser-and-ast/reference/token-trace.json",
    "exercises/02-lexer-parser-and-ast/reference/ast-projection.json",
    "exercises/08-mica-capstone/skeleton/src/mica/token.py",
    "exercises/08-mica-capstone/skeleton/src/mica/lexer.py",
    "exercises/08-mica-capstone/skeleton/src/mica/syntax.py",
    "exercises/08-mica-capstone/skeleton/src/mica/parser.py",
    "scripts/run_labs.py",
    "reference/sources.md",
    "reference/project-entry-map.md",
]


def main() -> int:
    failures: list[str] = []
    for relative in REQUIRED:
        path = ROOT / relative
        if not path.is_file():
            failures.append(f"필수 파일 없음: {relative}")
        elif path.stat().st_size == 0:
            failures.append(f"빈 필수 파일: {relative}")

    core_docs = sorted((ROOT / "docs").glob("[0-9][0-9]-*/*.md"))
    numbered = []
    for path in core_docs:
        try:
            number = int(path.name.split("-", 1)[0])
        except ValueError:
            continue
        if 1 <= number <= 22:
            numbered.append(number)
    if numbered != list(range(1, 23)):
        failures.append(f"핵심 문서 번호가 01..22가 아님: {numbered}")

    exercise_dirs = [ROOT / "exercises" / f"{index:02d}-{name}" for index, name in [
        (1, "source-and-diagnostics"),
        (2, "lexer-parser-and-ast"),
        (3, "resolution-types-and-flow"),
        (4, "interpreter-and-vm"),
        (5, "ir-analysis-and-passes"),
        (6, "backend-boundaries"),
        (7, "language-tools"),
        (8, "mica-capstone"),
    ]]
    for directory in exercise_dirs:
        if not (directory / "README.md").is_file():
            failures.append(f"exercise README 없음: {directory.relative_to(ROOT)}")

    for path in ROOT.rglob("*"):
        if path.is_file() and path.stat().st_size == 0:
            failures.append(f"빈 파일: {path.relative_to(ROOT)}")

    license_path = ROOT / "LICENSES/CC-BY-4.0.txt"
    if license_path.is_file() and license_path.stat().st_size < 10_000:
        failures.append("CC-BY-4.0.txt가 canonical legal text보다 지나치게 짧음")

    for relative in ("prepare.sh", "verify.sh", "scripts/new-workspace.sh", "scripts/run_labs.py", "exercises/08-mica-capstone/check_submission.py"):
        path = ROOT / relative
        if path.exists() and not (path.stat().st_mode & 0o111):
            failures.append(f"실행 권한 없음: {relative}")

    if failures:
        for failure in failures:
            print(f"ERROR {failure}", file=sys.stderr)
        return 1
    print(f"PASS structure core_docs={len(numbered)} files={sum(1 for p in ROOT.rglob('*') if p.is_file())}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
