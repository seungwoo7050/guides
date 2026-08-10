#!/usr/bin/env python3
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class EvidenceRoute:
    owns: str
    exit_capability: str
    paths: tuple[str, ...]


ROUTES = (
    EvidenceRoute(
        "문법·parser·AST",
        "작은 언어의 frontend를 만듭니다.",
        (
            "docs/02-front-end/04-lexing-and-token-streams.md",
            "docs/02-front-end/05-grammar-recursive-descent-and-pratt.md",
            "docs/02-front-end/06-cst-ast-and-normalization.md",
            "exercises/02-lexer-parser-and-ast/check.py",
            "exercises/02-lexer-parser-and-ast/reference/ast-projection.json",
            "exercises/08-mica-capstone/spec/normalized-ast.md",
            "exercises/08-mica-capstone/fixtures/golden/arithmetic.ast.json",
        ),
    ),
    EvidenceRoute(
        "scope·symbol·type checking·diagnostic",
        "정적 타입과 실행 모델을 구현합니다.",
        (
            "docs/01-language-contract/03-diagnostics-errors-and-recovery.md",
            "docs/03-semantics/07-scopes-symbols-and-name-resolution.md",
            "docs/03-semantics/08-types-constraints-and-checking.md",
            "docs/03-semantics/09-control-flow-definite-assignment-and-effects.md",
            "exercises/03-resolution-types-and-flow/check.py",
            "exercises/03-resolution-types-and-flow/reference/semantic-summary.json",
            "exercises/08-mica-capstone/spec/semantic.schema.json",
            "exercises/08-mica-capstone/fixtures/golden/shadowing.semantic.json",
        ),
    ),
    EvidenceRoute(
        "interpreter·VM·runtime",
        "정적 타입과 실행 모델을 구현합니다.",
        (
            "docs/04-execution/10-tree-walk-interpreter-and-environments.md",
            "docs/04-execution/11-functions-closures-and-runtime-errors.md",
            "docs/04-execution/12-bytecode-vm-and-call-frames.md",
            "exercises/04-interpreter-and-vm/check.py",
            "exercises/04-interpreter-and-vm/reference/runtime-trace.json",
            "exercises/06-backend-boundaries/reference/bytecode-trace.json",
            "exercises/08-mica-capstone/fixtures/runtime/min-div-overflow.mica",
        ),
    ),
    EvidenceRoute(
        "IR·CFG·data-flow·optimization",
        "분석·진단·변환 도구를 확장합니다.",
        (
            "docs/05-ir-and-analysis/14-lowering-basic-blocks-and-cfg.md",
            "docs/05-ir-and-analysis/15-dataflow-dominance-and-ssa.md",
            "docs/05-ir-and-analysis/16-optimization-correctness-and-verification.md",
            "exercises/05-ir-analysis-and-passes/check.py",
            "exercises/05-ir-analysis-and-passes/reference/ir-pipeline.json",
            "examples/ir-pipeline/ir_pipeline.py",
            "exercises/08-mica-capstone/skeleton/EVIDENCE.md",
        ),
    ),
    EvidenceRoute(
        "formatter·linter·static analyzer·language server",
        "분석·진단·변환 도구를 확장합니다.",
        (
            "docs/07-language-tooling/20-formatters-linters-and-refactoring.md",
            "docs/07-language-tooling/21-incremental-analysis-and-language-servers.md",
            "exercises/07-language-tools/check.py",
            "exercises/07-language-tools/reference/lint.json",
            "exercises/07-language-tools/reference/lsp-transcript.json",
            "exercises/08-mica-capstone/fixtures/lint/tooling.mica",
        ),
    ),
)


def main() -> int:
    failures: list[str] = []
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    roadmap = (ROOT / "docs/00-roadmap.md").read_text(encoding="utf-8")
    for route in ROUTES:
        if route.owns not in roadmap:
            failures.append(f"ownership label not declared in roadmap: {route.owns}")
        entry_marker = route.owns.split("·", 1)[0]
        if entry_marker not in readme:
            failures.append(f"ownership area not discoverable from README: {entry_marker}")
        if route.exit_capability not in roadmap:
            failures.append(f"exit capability not declared in roadmap: {route.exit_capability}")
        for relative in route.paths:
            path = ROOT / relative
            if not path.is_file():
                failures.append(f"traceability evidence missing: {route.owns} -> {relative}")
            elif path.stat().st_size == 0:
                failures.append(f"traceability evidence empty: {route.owns} -> {relative}")

    capstone = (ROOT / "exercises/08-mica-capstone/README.md").read_text(encoding="utf-8")
    for phrase in (
        "IR·CFG·data-flow·pass 누적 증거",
        "실행 확장 하나",
        "Tooling 확장 하나",
        "--stage all",
        "EVIDENCE.md",
    ):
        if phrase not in capstone:
            failures.append(f"capstone completion contract missing phrase: {phrase}")

    if failures:
        for failure in failures:
            print(f"ERROR {failure}", file=sys.stderr)
        return 1
    print(
        f"PASS learning-contract owns={len(ROUTES)} exits=3; "
        "mechanical traceability only, educational completion is not proven"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
