#!/usr/bin/env python3
from __future__ import annotations

import re
import sys
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]
LINK_RE = re.compile(r"!?(?:\[[^\]]*\])\(([^)]+)\)")

EXPECTED = [
    "README.md",
    "CONTRIBUTING.md",
    "LICENSE.md",
    "docs/00-roadmap.md",
    "docs/07-capstone.md",
    "docs/90-optional-extensions.md",
    "exercises/README.md",
    "exercises/10-capstone-local-coding-agent/README.md",
    "reference/standards-and-sources.md",
    "reference/capstone-review-rubric.md",
]

PART_COUNTS = {
    "docs/01-runtime-foundations": 4,
    "docs/02-repository-understanding": 5,
    "docs/03-tools-and-execution": 6,
    "docs/04-coding-loop": 6,
    "docs/05-safety-and-authority": 5,
    "docs/06-evaluation-and-operations": 5,
}

EXERCISE_DIRS = [
    "01-model-adapter",
    "02-repository-discovery",
    "03-context-selector",
    "04-filesystem-and-patch",
    "05-process-runner",
    "06-edit-test-repair",
    "07-permissions-and-sandbox",
    "08-checkpoint-resume",
    "09-evaluation-harness",
    "10-capstone-local-coding-agent",
]

EXERCISE_SECTIONS = [
    "## 목표",
    "## 필수 산출물",
    "## 검증 계획",
    "## 의도적 비범위",
]

CAPSTONE_TERMS = [
    "repository discovery",
    "multi-file",
    "Process runner",
    "Git adapter",
    "Edit-test-repair",
    "failure classifier",
    "ScriptedModelAdapter",
    "RealModelAdapter",
    "External evaluator",
    "crash",
    "resume",
]

FORBIDDEN_CORE_PHRASES = [
    "config/service.json을 현재 schema로 마이그레이션",
    "최대 write operation   1",
]


def fail(message: str) -> None:
    print(f"ERROR: {message}", file=sys.stderr)
    raise SystemExit(1)


def check_expected() -> None:
    for rel in EXPECTED:
        if not (ROOT / rel).is_file():
            fail(f"필수 파일이 없습니다: {rel}")

    for rel, expected_count in PART_COUNTS.items():
        path = ROOT / rel
        files = sorted(path.glob("*.md"))
        if len(files) != expected_count:
            fail(f"{rel}: Markdown {expected_count}개가 필요하지만 {len(files)}개입니다.")

    for exercise in EXERCISE_DIRS:
        path = ROOT / "exercises" / exercise / "README.md"
        if not path.is_file():
            fail(f"실습 README가 없습니다: {path.relative_to(ROOT)}")


def check_markdown_links() -> None:
    for path in sorted(ROOT.rglob("*.md")):
        text = path.read_text(encoding="utf-8")
        for raw_target in LINK_RE.findall(text):
            target = raw_target.strip().split("#", 1)[0]
            if not target or target.startswith(("http://", "https://", "mailto:")):
                continue
            target = unquote(target)
            resolved = (path.parent / target).resolve()
            try:
                resolved.relative_to(ROOT.resolve())
            except ValueError:
                fail(f"{path.relative_to(ROOT)}: 저장소 밖 링크 {raw_target}")
            if not resolved.exists():
                fail(f"{path.relative_to(ROOT)}: 깨진 링크 {raw_target}")


def check_exercise_contracts() -> None:
    for exercise in EXERCISE_DIRS:
        path = ROOT / "exercises" / exercise / "README.md"
        text = path.read_text(encoding="utf-8")
        for section in EXERCISE_SECTIONS:
            if section not in text:
                fail(f"{path.relative_to(ROOT)}: 필수 절 누락 {section}")


def check_capstone() -> None:
    paths = [
        ROOT / "docs/07-capstone.md",
        ROOT / "exercises/10-capstone-local-coding-agent/README.md",
    ]
    text = "\n".join(path.read_text(encoding="utf-8") for path in paths)
    lowered = text.lower()
    for term in CAPSTONE_TERMS:
        if term.lower() not in lowered:
            fail(f"Capstone 필수 개념이 없습니다: {term}")

    all_text = "\n".join(path.read_text(encoding="utf-8") for path in ROOT.rglob("*.md"))
    for phrase in FORBIDDEN_CORE_PHRASES:
        if phrase in all_text:
            fail(f"이전 단일 patch Capstone 문구가 남아 있습니다: {phrase}")


def check_orientation() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    required = [
        "에이전트 자체",
        "처음 보는 저장소",
        "여러 파일",
        "실패를 해석",
        "외부 verifier",
    ]
    for phrase in required:
        if phrase not in readme:
            fail(f"README 목적 문구 누락: {phrase}")

    if "python" not in readme or "git" not in readme or "unix-systems" not in readme:
        fail("README 필수 선행 경로가 불완전합니다.")


def main() -> None:
    check_expected()
    check_markdown_links()
    check_exercise_contracts()
    check_capstone()
    check_orientation()
    markdown_count = sum(1 for _ in ROOT.rglob("*.md"))
    print(f"DOCS OK markdown={markdown_count} exercises={len(EXERCISE_DIRS)}")


if __name__ == "__main__":
    main()
