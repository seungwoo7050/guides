#!/usr/bin/env python3
"""Validate exact layout, learning contracts, links, source hygiene, and pins."""

from __future__ import annotations

import ast
import os
import re
import subprocess
import sys
import unicodedata
from pathlib import Path
from urllib.parse import unquote

sys.dont_write_bytecode = True
from repository_state import source_manifest

ROOT = Path(os.environ.get("GUIDE_ROOT", Path(__file__).resolve().parents[1])).resolve()
ERRORS: list[str] = []
LAYOUT = ROOT / "scripts/layout-manifest.txt"

DOCS = {
    "docs/00-roadmap.md",
    "docs/01-link-and-path/01-layers-encapsulation-and-path.md",
    "docs/01-link-and-path/02-ethernet-mac-and-switching.md",
    "docs/01-link-and-path/03-arp-and-neighbor-discovery.md",
    "docs/02-internetworking/01-ip-addressing-subnets-and-lpm.md",
    "docs/02-internetworking/02-ip-forwarding-mtu-and-icmp.md",
    "docs/02-internetworking/03-nat-connection-tracking-and-firewalls.md",
    "docs/02-internetworking/04-routing-algorithms-and-protocols.md",
    "docs/03-transport/01-udp-and-tcp-service-contracts.md",
    "docs/03-transport/02-tcp-connection-state-and-sequences.md",
    "docs/03-transport/03-retransmission-rtt-and-sliding-windows.md",
    "docs/03-transport/04-flow-and-congestion-control.md",
    "docs/04-application-security-and-evidence/01-dns-http-tls-and-quic.md",
    "docs/04-application-security-and-evidence/02-network-failure-localization.md",
    "docs/90-standards-map.md",
}
CONCEPT_DOCS = DOCS - {"docs/00-roadmap.md", "docs/90-standards-map.md"}
EXERCISES = {
    "exercises/linux-routing-nat/README.md",
    "exercises/packet-observation/README.md",
    "exercises/path-diagnosis/README.md",
    "exercises/protocol-inspector/README.md",
}
CONCEPT_SECTIONS = ("학습 목표", "선행 개념", "연결 실습", "완료 기준")
EXERCISE_SECTIONS = ("목표", "완료 기준", "자기 설명", "검증")
TEXT_SUFFIXES = {".md", ".py", ".sh", ".txt", ".json", ".hex"}
GENERATED_NAMES = {"__pycache__", ".pytest_cache", ".guide", ".verify"}


def error(message: str) -> None:
    ERRORS.append(message)


def section(text: str, title: str) -> str:
    match = re.search(rf"(?ms)^## {re.escape(title)}\s*$\n(.*?)(?=^## |\Z)", text)
    return match.group(1).strip() if match else ""


def bullets(text: str) -> list[str]:
    return [line for line in text.splitlines() if line.startswith("- ")]


def slug(text: str) -> str:
    value = re.sub(r"`([^`]*)`", r"\1", text)
    value = re.sub(r"<[^>]+>", "", value)
    value = unicodedata.normalize("NFKC", value).strip().casefold()
    value = re.sub(r"[^\w\-\s가-힣]", "", value)
    return re.sub(r"[\s_]+", "-", value).strip("-")


def headings(path: Path) -> set[str]:
    result: set[str] = set()
    seen: dict[str, int] = {}
    in_fence = False
    marker = ""
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.lstrip()
        match_fence = re.match(r"(`{3,}|~{3,})", stripped)
        if match_fence:
            current = match_fence.group(1)[0]
            if not in_fence:
                in_fence, marker = True, current
            elif current == marker:
                in_fence = False
            continue
        if in_fence:
            continue
        match = re.match(r"^#{1,6}\s+(.+?)\s*#*\s*$", line)
        if match:
            base = slug(match.group(1))
            count = seen.get(base, 0)
            seen[base] = count + 1
            result.add(base if count == 0 else f"{base}-{count}")
    return result


def markdown_without_fences(text: str) -> str:
    lines: list[str] = []
    in_fence = False
    marker = ""
    for line in text.splitlines():
        match = re.match(r"\s*(`{3,}|~{3,})", line)
        if match:
            current = match.group(1)[0]
            if not in_fence:
                in_fence, marker = True, current
            elif current == marker:
                in_fence = False
            continue
        if not in_fence:
            lines.append(line)
    return "\n".join(lines)


def check_layout() -> None:
    if not LAYOUT.is_file():
        error("exact layout manifest가 없습니다")
        return
    expected = LAYOUT.read_text(encoding="utf-8").splitlines()
    if expected != sorted(set(expected)):
        error("exact layout manifest는 중복 없이 정렬되어야 합니다")
    actual_entries = source_manifest(ROOT)
    actual = sorted(
        str(entry["path"])
        for entry in actual_entries
        if entry["type"] != "directory"
    )
    missing = sorted(set(expected) - set(actual))
    unexpected = sorted(set(actual) - set(expected))
    if missing:
        error("exact layout 필수 파일 없음: " + ", ".join(missing))
    if unexpected:
        error("exact layout 예상 밖 파일: " + ", ".join(unexpected))
    for entry in actual_entries:
        if entry["type"] == "symlink":
            error(f"source symlink 금지: {entry['path']}")


def check_learning_contracts() -> None:
    actual_docs = {path.relative_to(ROOT).as_posix() for path in (ROOT / "docs").rglob("*.md")}
    if actual_docs != DOCS:
        error(f"본문 문서 구성이 다릅니다: missing={sorted(DOCS-actual_docs)} unexpected={sorted(actual_docs-DOCS)}")
    concept_completion: dict[str, str] = {}
    for relative in sorted(CONCEPT_DOCS):
        path = ROOT / relative
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8")
        positions = [text.find(f"## {title}\n") for title in CONCEPT_SECTIONS]
        if any(position < 0 for position in positions):
            error(f"개념 문서 학습 heading 누락: {relative}")
            continue
        if positions != sorted(positions):
            error(f"개념 문서 학습 heading 순서 오류: {relative}")
        if len(bullets(section(text, "학습 목표"))) < 2:
            error(f"학습 목표가 2개 미만입니다: {relative}")
        if not section(text, "선행 개념") or not section(text, "연결 실습"):
            error(f"선행 개념 또는 연결 실습이 비어 있습니다: {relative}")
        completion = section(text, "완료 기준")
        if len(bullets(completion)) < 3:
            error(f"개념 문서 완료 기준이 3개 미만입니다: {relative}")
        normalized = " ".join(completion.split())
        if normalized in concept_completion:
            error(f"개념 문서 복사형 완료 기준: {relative}, {concept_completion[normalized]}")
        concept_completion[normalized] = relative

    completion_owner: dict[str, str] = {}
    explanation_owner: dict[str, str] = {}
    for relative in sorted(EXERCISES):
        path = ROOT / relative
        if not path.is_file():
            error(f"실습 README가 없습니다: {relative}")
            continue
        text = path.read_text(encoding="utf-8")
        positions = [text.find(f"## {title}\n") for title in EXERCISE_SECTIONS]
        if any(position < 0 for position in positions):
            error(f"실습 학습 heading 누락: {relative}")
            continue
        if positions != sorted(positions):
            error(f"실습 학습 heading 순서 오류: {relative}")
        completion = section(text, "완료 기준")
        explanation = section(text, "자기 설명")
        if len(bullets(completion)) < 3:
            error(f"실습 완료 기준이 3개 미만입니다: {relative}")
        questions = bullets(explanation)
        if len(questions) < 2 or any(not question.rstrip().endswith("?") for question in questions):
            error(f"자기 설명 질문이 2개 미만이거나 물음표로 끝나지 않습니다: {relative}")
        normalized_completion = " ".join(completion.split())
        normalized_explanation = " ".join(explanation.split())
        if normalized_completion in completion_owner:
            error(f"실습 복사형 완료 기준: {relative}, {completion_owner[normalized_completion]}")
        if normalized_explanation in explanation_owner:
            error(f"실습 복사형 자기 설명: {relative}, {explanation_owner[normalized_explanation]}")
        completion_owner[normalized_completion] = relative
        explanation_owner[normalized_explanation] = relative

    roadmap = (ROOT / "docs/00-roadmap.md").read_text(encoding="utf-8")
    roadmap_requirements = (
        "## 대상 독자",
        "## 선행지식과 지원 환경",
        "필수 경로",
        "선택 경로",
        "## 문서와 실습의 대응",
        "## 완료 뒤 할 수 있어야 하는 일",
        "## 범위 밖 항목",
        "## 완료 기준",
        "## 자동 검증의 한계",
        "skipped=0",
    )
    for requirement in roadmap_requirements:
        if requirement not in roadmap:
            error(f"roadmap 학습 계약 누락: {requirement}")
    if "네임스페이스 실험을 건너뛰" in roadmap:
        error("roadmap이 필수 privileged Linux 실험의 skip을 허용합니다")


def check_markdown() -> None:
    markdown = sorted(path for path in ROOT.rglob("*.md") if not any(part in GENERATED_NAMES or part == "workspace" for part in path.relative_to(ROOT).parts))
    link_pattern = re.compile(r"!?\[[^]]*\]\(([^)]+)\)")
    for path in markdown:
        text = path.read_text(encoding="utf-8")
        lines = text.splitlines()
        relative = path.relative_to(ROOT)
        if not lines or not lines[0].startswith("# ") or sum(line.startswith("# ") for line in lines) != 1:
            error(f"H1 제목은 첫 줄에 정확히 하나여야 합니다: {relative}")
        prose = markdown_without_fences(text)
        for raw in link_pattern.findall(prose):
            target = raw.strip()
            if target.startswith("<") and ">" in target:
                target = target[1 : target.index(">")]
            else:
                target = target.split(maxsplit=1)[0]
            if target.startswith(("https://", "http://", "mailto:")):
                continue
            decoded = unquote(target)
            path_text, separator, fragment = decoded.partition("#")
            resolved = path if not path_text else (path.parent / path_text).resolve()
            try:
                resolved.relative_to(ROOT)
            except ValueError:
                error(f"저장소 밖 링크: {relative} -> {target}")
                continue
            if not resolved.exists():
                error(f"깨진 링크: {relative} -> {target}")
            elif separator and fragment and resolved.suffix == ".md" and slug(fragment) not in headings(resolved):
                error(f"깨진 anchor: {relative} -> {target}")


def check_source() -> None:
    for path in ROOT.rglob("*"):
        relative = path.relative_to(ROOT)
        if any(part in {".git", ".guide", "workspace", "__pycache__", ".pytest_cache"} for part in relative.parts):
            continue
        if not path.is_file():
            continue
        if path.suffix in {".pyc", ".pyo"}:
            error(f"생성 bytecode가 남았습니다: {relative}")
        if path.name != "Makefile" and path.suffix not in TEXT_SUFFIXES:
            continue
        data = path.read_bytes()
        if b"\x00" in data or b"\r" in data:
            error(f"텍스트에 NUL 또는 CR이 있습니다: {relative}")
            continue
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError:
            error(f"UTF-8 텍스트가 아닙니다: {relative}")
            continue
        for number, line in enumerate(text.splitlines(), 1):
            if line.rstrip(" \t") != line:
                error(f"줄 끝 공백: {relative}:{number}")
        if path.suffix == ".py":
            try:
                ast.parse(text, filename=str(path))
            except SyntaxError as exception:
                error(f"Python 구문 오류: {relative}: {exception}")

    for reference in sorted((ROOT / "exercises").rglob("reference/**/*.py")):
        text = reference.read_text(encoding="utf-8")
        if re.search(r"\b(?:TODO|TBD|FIXME)\b|NotImplementedError", text):
            error(f"reference 미완성 표식: {reference.relative_to(ROOT)}")

    for script in sorted([ROOT / "prepare.sh", ROOT / "verify.sh", *(ROOT / "scripts").glob("*.sh"), *(ROOT / "exercises").rglob("*.sh")]):
        if script.is_file():
            outcome = subprocess.run(["sh", "-n", str(script)], capture_output=True, text=True)
            if outcome.returncode:
                error(f"Shell 구문 오류: {script.relative_to(ROOT)}: {outcome.stderr.strip()}")
            if os.name == "posix" and not os.access(script, os.X_OK):
                error(f"실행 권한 없음: {script.relative_to(ROOT)}")
    for script in sorted((ROOT / "scripts").glob("*.py")):
        if script.is_file() and script.read_bytes().startswith(b"#!") and os.name == "posix" and not os.access(script, os.X_OK):
            error(f"실행 권한 없음: {script.relative_to(ROOT)}")


def check_interfaces_and_pins() -> None:
    makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
    for target in ("prepare", "check", "static-check", "meta-check", "reference-check", "skeleton-check", "test-quality-check", "docker-e2e", "verify", "clean"):
        if re.search(rf"(?m)^{re.escape(target)}\s*:", makefile) is None:
            error(f"공개 Make target 누락: {target}")
    prepare = (ROOT / "prepare.sh").read_text(encoding="utf-8")
    verify = (ROOT / "verify.sh").read_text(encoding="utf-8")
    expected = "python:3.12-slim-bookworm@sha256:4766d8b510c428e595d74b9cc5bbb2fae8e26316fffb4adc89908d79aacd58a2"
    image_helper = (ROOT / "scripts/prepare_network_image.py").read_text(encoding="utf-8")
    if expected not in image_helper or "latest" in image_helper:
        error("고정 Python 3.12 verifier image digest 계약이 없습니다")
    package_pins = (
        "DEBIAN_SNAPSHOT = \"20260803T000000Z\"",
        '"iproute2": "6.1.0-3"',
        '"iptables": "1.8.9-2"',
        '"iputils-ping": "3:20221126-1+deb12u1"',
        '"tcpdump": "4.99.3-1"',
        '"procps": "2:4.0.2-3"',
    )
    if any(pin not in image_helper for pin in package_pins):
        error("Debian snapshot·network tool package version pin 계약이 없습니다")
    if "--check-state" not in verify or "package_versions" not in verify:
        error("verify가 verifier image package attestation을 재검사하지 않습니다")
    if "--pull=never" not in verify or "--privileged" not in verify:
        error("verify의 no-pull privileged Docker 계약이 없습니다")
    if "PREPARE RESULT: PASS" not in prepare or "VERIFY LOG:" not in verify or "RESULT: PASS" not in verify:
        error("prepare/verify 결과 출력 계약이 없습니다")
    combined = "\n".join((prepare, verify, (ROOT / "README.md").read_text(encoding="utf-8")))
    if "Python 3.11" in combined:
        error("지원 종료 기준인 Python 3.11 계약이 남았습니다")


def main() -> int:
    check_layout()
    check_learning_contracts()
    check_markdown()
    check_source()
    check_interfaces_and_pins()
    if ERRORS:
        print(f"네트워크 가이드 검사 실패: {len(ERRORS)}건", file=sys.stderr)
        for message in ERRORS:
            print(f"- {message}", file=sys.stderr)
        return 1
    print(f"[PASS] exact layout, docs={len(DOCS)}, exercises={len(EXERCISES)}, pedagogy, links, source, pins")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
