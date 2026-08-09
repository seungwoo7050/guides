#!/usr/bin/env python3
"""Validate the published learning contract, Markdown graph, and commands."""

from __future__ import annotations

import re
import shlex
import sys
import unicodedata
from pathlib import Path
from urllib.parse import unquote


ROOT = Path(__file__).resolve().parents[1]
LINK_RE = re.compile(r"!?(?:\[[^\]]*\])\(([^)]+)\)")
FENCE_RE = re.compile(r"^```(?:sh|bash|shell)\s*$([\s\S]*?)^```\s*$", re.MULTILINE | re.IGNORECASE)
HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*#*\s*$", re.MULTILINE)

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

EXERCISE_SECTIONS = ["## 목표", "## 필수 산출물", "## 검증 계획", "## 의도적 비범위"]

CATALOG = {
    "kind": "field-entry",
    "requires": ("python", "web-app"),
    "recommends": ("distributed-services", "cybersecurity", "machine-learning"),
    "connects": ("data-engineering", "platform-engineering", "web-infra"),
    "continues_to": ("platform-engineering",),
    "owns": (
        "모델 API와 구조화된 출력",
        "RAG와 출처·권한 경계",
        "도구 호출과 agent loop",
        "checkpoint·resume·취소·budget",
        "sandbox·identity·평가·trace",
    ),
    "excludes": (
        "모델 학습 원리 전체",
        "일반 웹 개발 재교육",
        "사이버보안 전체",
        "대규모 플랫폼 운영 전체",
    ),
    "exit_capabilities": (
        "도구를 사용하는 에이전트를 구현한다",
        "외부 verifier로 성공을 판정한다",
        "권한·네트워크·비용·실행 시간을 제한한다",
    ),
}

RELATION_LABELS = {
    "필수 선행": "requires",
    "권장 선행": "recommends",
    "연결 분야": "connects",
    "후속 경로": "continues_to",
}

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
    "cancel",
    "budget",
    "source",
    "citation",
]

FORBIDDEN_CORE_PHRASES = ["config/service.json을 현재 schema로 마이그레이션", "최대 write operation   1"]
PLACEHOLDER_RE = re.compile(
    r"\b(?:TODO|TBD|FIXME|XXX|PLACEHOLDER)\b|lorem ipsum|<\s*(?:fill|insert|replace)[^>]*>",
    re.IGNORECASE,
)

CANONICAL_COMMANDS = (
    "python3 scripts/new_workspace.py --destination .workspace/local-coding-agent",
    "python3 exercises/10-capstone-local-coding-agent/tests/run.py --implementation reference --stage all",
    "python3 exercises/10-capstone-local-coding-agent/tests/run.py --implementation .workspace/local-coding-agent --stage 01",
)
CANONICAL_MAKE_TARGETS = ("test-reference", "test-starter-contract", "test-mutants", "test-capstone")


def fail(message: str) -> None:
    print(f"ERROR: {message}", file=sys.stderr)
    raise SystemExit(1)


def markdown_files() -> list[Path]:
    return sorted(
        (path for path in ROOT.rglob("*.md") if not {".git", ".guide", ".workspace"}.intersection(path.parts)),
        key=lambda path: path.relative_to(ROOT).as_posix(),
    )


def check_expected() -> None:
    for relative in EXPECTED:
        if not (ROOT / relative).is_file():
            fail(f"필수 파일이 없습니다: {relative}")
    for relative, expected_count in PART_COUNTS.items():
        files = sorted((ROOT / relative).glob("*.md"))
        if len(files) != expected_count:
            fail(f"{relative}: Markdown {expected_count}개가 필요하지만 {len(files)}개입니다.")
    for exercise in EXERCISE_DIRS:
        path = ROOT / "exercises" / exercise / "README.md"
        if not path.is_file():
            fail(f"실습 README가 없습니다: {path.relative_to(ROOT)}")


def _slug(value: str) -> str:
    value = re.sub(r"<[^>]+>", "", value)
    value = re.sub(r"[`*_~]", "", value).strip().lower()
    value = "".join(character for character in value if unicodedata.category(character)[0] not in {"P", "S"} or character == "-")
    return re.sub(r"\s+", "-", value)


def _anchors(path: Path) -> set[str]:
    counts: dict[str, int] = {}
    result: set[str] = set()
    for match in HEADING_RE.finditer(path.read_text(encoding="utf-8")):
        base = _slug(match.group(2))
        occurrence = counts.get(base, 0)
        counts[base] = occurrence + 1
        result.add(base if occurrence == 0 else f"{base}-{occurrence}")
    return result


def _link_target(raw_target: str) -> tuple[str, str]:
    value = raw_target.strip()
    # Markdown titles are not used by this guide; tolerate one if present.
    if " \"" in value:
        value = value.split(" \"", 1)[0]
    path, separator, fragment = value.partition("#")
    return unquote(path), unquote(fragment if separator else "")


def check_markdown_links() -> None:
    anchor_cache: dict[Path, set[str]] = {}
    for path in markdown_files():
        text = path.read_text(encoding="utf-8")
        for raw_target in LINK_RE.findall(text):
            target, fragment = _link_target(raw_target)
            if target.startswith(("http://", "https://", "mailto:")):
                continue
            resolved = (path.parent / (target or ".")).resolve()
            try:
                resolved.relative_to(ROOT.resolve())
            except ValueError:
                fail(f"{path.relative_to(ROOT)}: 저장소 밖 링크 {raw_target}")
            if not resolved.exists():
                fail(f"{path.relative_to(ROOT)}: 깨진 링크 {raw_target}")
            if fragment:
                if not resolved.is_file() or resolved.suffix.lower() != ".md":
                    fail(f"{path.relative_to(ROOT)}: Markdown가 아닌 대상의 anchor {raw_target}")
                anchors = anchor_cache.setdefault(resolved, _anchors(resolved))
                if fragment not in anchors:
                    fail(f"{path.relative_to(ROOT)}: 존재하지 않는 anchor {raw_target}")


def _numbered_items(text: str, start_marker: str, end_marker: str) -> tuple[str, ...]:
    try:
        section = text.split(start_marker, 1)[1].split(end_marker, 1)[0]
    except IndexError:
        fail(f"README 계약 절을 찾지 못했습니다: {start_marker}")
    return tuple(re.sub(r"[.]$", "", match.strip()) for match in re.findall(r"^\d+\.\s+(.+)$", section, re.MULTILINE))


def check_catalog_contract() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    if f"`main` 카탈로그에서 이 브랜치는 `{CATALOG['kind']}`" not in readme:
        fail(f"README kind가 catalog와 다릅니다: {CATALOG['kind']}")

    for label, key in RELATION_LABELS.items():
        match = re.search(rf"^- {re.escape(label)}:\s*(.+)$", readme, re.MULTILINE)
        if not match:
            fail(f"README catalog 관계가 없습니다: {label}")
        actual = tuple(re.findall(r"/tree/([A-Za-z0-9._-]+)", match.group(1)))
        if actual != CATALOG[key]:
            fail(f"README {key}가 catalog와 다릅니다: expected={CATALOG[key]} actual={actual}")

    owns = _numbered_items(readme, "이 브랜치가 소유하는 범위는 다음 다섯 가지입니다.", "모델 학습 원리 전체")
    if owns != CATALOG["owns"]:
        fail(f"README owns가 catalog와 다릅니다: expected={CATALOG['owns']} actual={owns}")
    for excluded in CATALOG["excludes"]:
        if excluded not in readme:
            fail(f"README excludes 누락: {excluded}")
    exclusion_sentence = ", ".join(CATALOG["excludes"]) + "는 이 브랜치가 소유하지 않습니다."
    if exclusion_sentence not in readme:
        fail("README excludes 문장이 catalog의 정확한 순서·내용과 다릅니다.")

    exits = _numbered_items(readme, "카탈로그가 선언한 종료 능력은 다음 세 가지이며", "다음 질문은")
    if exits != CATALOG["exit_capabilities"]:
        fail(f"README exit_capabilities가 catalog와 다릅니다: expected={CATALOG['exit_capabilities']} actual={exits}")

    roadmap = (ROOT / "docs/00-roadmap.md").read_text(encoding="utf-8")
    for owned in CATALOG["owns"]:
        if not re.search(rf"^\| {re.escape(owned)} \|", roadmap, re.MULTILINE):
            fail(f"roadmap owns→evidence 행 누락: {owned}")
    for capability in CATALOG["exit_capabilities"]:
        if not re.search(rf"^\| {re.escape(capability)} \|", roadmap, re.MULTILINE):
            fail(f"roadmap exit→evidence 행 누락: {capability}")


def check_exercise_contracts() -> None:
    for exercise in EXERCISE_DIRS:
        path = ROOT / "exercises" / exercise / "README.md"
        text = path.read_text(encoding="utf-8")
        for section in EXERCISE_SECTIONS:
            if section not in text:
                fail(f"{path.relative_to(ROOT)}: 필수 절 누락 {section}")


def check_capstone() -> None:
    paths = [ROOT / "docs/07-capstone.md", ROOT / "exercises/10-capstone-local-coding-agent/README.md"]
    text = "\n".join(path.read_text(encoding="utf-8") for path in paths)
    lowered = text.lower()
    for term in CAPSTONE_TERMS:
        if term.lower() not in lowered:
            fail(f"Capstone 필수 개념이 없습니다: {term}")
    all_text = "\n".join(path.read_text(encoding="utf-8") for path in markdown_files())
    for phrase in FORBIDDEN_CORE_PHRASES:
        if phrase in all_text:
            fail(f"이전 단일 patch Capstone 문구가 남아 있습니다: {phrase}")


def check_orientation() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    for phrase in ("에이전트 자체", "처음 보는 저장소", "여러 파일", "실패를 해석", "외부 verifier"):
        if phrase not in readme:
            fail(f"README 목적 문구 누락: {phrase}")
    for branch in ("python", "git", "unix-systems"):
        if branch not in readme:
            fail(f"README 선행 경로가 불완전합니다: {branch}")


def _shell_commands(text: str) -> list[str]:
    result: list[str] = []
    for block in FENCE_RE.findall(text):
        logical = re.sub(r"\\\s*\n\s*", " ", block)
        for raw_line in logical.splitlines():
            line = raw_line.strip()
            if line and not line.startswith(("#", "$")):
                result.append(re.sub(r"\s+", " ", line))
    return result


def _make_targets() -> set[str]:
    text = (ROOT / "Makefile").read_text(encoding="utf-8")
    return {match.group(1) for match in re.finditer(r"^([A-Za-z0-9_.-]+):(?:\s|$)", text, re.MULTILINE)}


def check_commands() -> None:
    all_commands: list[tuple[Path, str]] = []
    normalized_docs = "\n".join(path.read_text(encoding="utf-8") for path in markdown_files())
    normalized_docs = re.sub(r"\\\s*\n\s*", " ", normalized_docs)
    normalized_docs = re.sub(r"[ \t]+", " ", normalized_docs)
    for command in CANONICAL_COMMANDS:
        if command not in normalized_docs:
            fail(f"canonical 명령이 문서에 없습니다: {command}")

    targets = _make_targets()
    for target in CANONICAL_MAKE_TARGETS:
        if target not in targets:
            fail(f"Make target이 없습니다: {target}")
        if f"`make {target}`" not in normalized_docs and f"make {target}" not in normalized_docs:
            fail(f"canonical Make target이 문서화되지 않았습니다: {target}")
    for command in ("./prepare.sh", "./verify.sh"):
        if command not in normalized_docs:
            fail(f"준비/검증 명령이 문서화되지 않았습니다: {command}")

    for path in markdown_files():
        for command in _shell_commands(path.read_text(encoding="utf-8")):
            all_commands.append((path, command))
    for path, command in all_commands:
        try:
            words = shlex.split(command)
        except ValueError as exc:
            fail(f"{path.relative_to(ROOT)}: shell 명령을 해석할 수 없습니다: {command}: {exc}")
        if not words:
            continue
        if words[0] == "make" and len(words) > 1 and not words[1].startswith("-") and words[1] not in targets:
            fail(f"{path.relative_to(ROOT)}: 존재하지 않는 Make target: {words[1]}")
        candidate: str | None = None
        if words[0] in {"python", "python3"}:
            index = 1
            while index < len(words) and words[index] in {"-B", "-I", "-E", "-s", "-S"}:
                index += 1
            if index < len(words) and not words[index].startswith("-"):
                candidate = words[index]
        elif words[0].startswith("./"):
            candidate = words[0]
        if candidate and not any(character in candidate for character in "$*?{}"):
            resolved = (ROOT / candidate).resolve()
            try:
                resolved.relative_to(ROOT.resolve())
            except ValueError:
                fail(f"{path.relative_to(ROOT)}: 저장소 밖 실행 경로: {candidate}")
            if not resolved.is_file():
                fail(f"{path.relative_to(ROOT)}: 존재하지 않는 실행 파일: {candidate}")


def check_placeholders() -> None:
    for path in markdown_files():
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if PLACEHOLDER_RE.search(line):
                fail(f"{path.relative_to(ROOT)}:{number}: 미완성 placeholder: {line.strip()}")


def main() -> None:
    check_expected()
    check_markdown_links()
    check_catalog_contract()
    check_exercise_contracts()
    check_capstone()
    check_orientation()
    check_commands()
    check_placeholders()
    print(f"DOCS OK markdown={len(markdown_files())} exercises={len(EXERCISE_DIRS)} catalog=agentic-systems")


if __name__ == "__main__":
    main()
