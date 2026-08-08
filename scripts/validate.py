#!/usr/bin/env python3
"""Validate the final Java guide tree, documentation, tests and pinned toolchain."""

from __future__ import annotations

import os
import re
import stat
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]
ERRORS: list[str] = []
EXCLUDED_DIRECTORIES = {".git", ".guide", "target", ".workspace", "__pycache__"}
EXCLUDED_SUFFIXES = {".jfr", ".pyc"}

EXPECTED_DOCS = {
    "docs/00-roadmap.md",
    "docs/01-language-and-domain/01-jdk-jvm-and-first-program.md",
    "docs/01-language-and-domain/02-java-language-foundations.md",
    "docs/01-language-and-domain/03-domain-types-records-and-sealed-types.md",
    "docs/01-language-and-domain/04-collections-streams-and-numeric-invariants.md",
    "docs/01-language-and-domain/05-errors-validation-time-and-identifiers.md",
    "docs/02-runtime-and-concurrency/01-concurrency-locking-and-executors.md",
    "docs/03-build-test-and-evidence/01-maven-wrapper-and-lifecycle.md",
    "docs/03-build-test-and-evidence/02-junit-assertj-and-test-doubles.md",
    "docs/03-build-test-and-evidence/03-quality-profiling-and-evidence.md",
    "docs/04-capstone.md",
}

EXPECTED_EXERCISES = {
    "exercises/01-language-and-domain/01-first-program",
    "exercises/01-language-and-domain/02-value-object-contract",
    "exercises/02-runtime-and-concurrency/01-concurrent-state-update",
    "exercises/02-runtime-and-concurrency/02-executor-lifecycle",
    "exercises/03-build-test-and-evidence/01-multi-repository-maven",
    "exercises/03-build-test-and-evidence/02-state-and-effect-testing",
    "exercises/04-capstone/01-concurrent-job-ledger",
}

EXPECTED_MODULES = {
    "examples/runtime-model",
    "exercises/01-language-and-domain/01-first-program/reference",
    "exercises/01-language-and-domain/02-value-object-contract/reference",
    "exercises/02-runtime-and-concurrency/01-concurrent-state-update/reference",
    "exercises/02-runtime-and-concurrency/02-executor-lifecycle/reference",
    "exercises/03-build-test-and-evidence/02-state-and-effect-testing/reference",
    "exercises/04-capstone/01-concurrent-job-ledger/reference",
}

FORBIDDEN_PATHS = {
    "docs/00-java-language-foundations.md",
    "docs/01-jdk-jvm-and-toolchain.md",
    "docs/02-domain-types-records-and-sealed-types.md",
    "docs/03-collections-streams-and-numeric-invariants.md",
    "docs/04-errors-validation-time-and-identifiers.md",
    "docs/05-concurrency-locking-and-executors.md",
    "docs/06-maven-wrapper-lifecycle-and-local-repository.md",
    "docs/07-junit-assertj-and-test-doubles.md",
    "docs/08-quality-profiling-and-evidence.md",
    "reference",
    "exercises/value-object-contract",
    "exercises/concurrent-state-update",
    "exercises/executor-lifecycle",
    "exercises/multi-repository-maven",
    "exercises/state-and-effect-testing",
    ".guide-cache",
}

EXECUTABLE_FILES = {
    "mvnw",
    "prepare.sh",
    "verify.sh",
    "scripts/mvn-guide.sh",
    "scripts/preflight.sh",
    "scripts/record-executor-jfr.sh",
    "scripts/smoke-javac.sh",
    "exercises/03-build-test-and-evidence/01-multi-repository-maven/verify.sh",
}


def report(message: str) -> None:
    ERRORS.append(message)


def source_files() -> list[Path]:
    files: list[Path] = []
    for directory, names, filenames in os.walk(ROOT, followlinks=False):
        names[:] = sorted(name for name in names if name not in EXCLUDED_DIRECTORIES)
        base = Path(directory)
        for name in sorted(filenames):
            path = base / name
            if path.suffix not in EXCLUDED_SUFFIXES:
                files.append(path)
        for name in names.copy():
            path = base / name
            if path.is_symlink():
                files.append(path)
                names.remove(name)
    return sorted(files, key=lambda path: path.relative_to(ROOT).as_posix())


def github_slug(text: str) -> str:
    text = re.sub(r"`([^`]*)`", r"\1", text).strip().lower()
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"[^\w\s가-힣-]", "", text)
    return re.sub(r"[\s-]+", "-", text).strip("-")


def markdown_headings(path: Path) -> set[str]:
    headings: set[str] = set()
    counts: dict[str, int] = {}
    in_fence = False
    fence = ""
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.lstrip()
        if stripped.startswith(("```", "~~~")):
            marker = stripped[:3]
            if not in_fence:
                in_fence = True
                fence = marker
            elif marker == fence:
                in_fence = False
            continue
        if in_fence:
            continue
        match = re.match(r"^#{1,6}\s+(.+?)\s*#*\s*$", line)
        if match:
            base = github_slug(match.group(1))
            count = counts.get(base, 0)
            counts[base] = count + 1
            headings.add(base if count == 0 else f"{base}-{count}")
    return headings


def check_exact_tree() -> None:
    manifest = ROOT / "config/expected-tree.txt"
    if not manifest.is_file():
        report("정확한 tree manifest가 없습니다: config/expected-tree.txt")
        return
    expected = {
        line
        for line in manifest.read_text(encoding="utf-8").splitlines()
        if line and not line.startswith("#")
    }
    actual = {path.relative_to(ROOT).as_posix() for path in source_files()}
    for missing in sorted(expected - actual):
        report(f"tree에 필요한 파일이 없습니다: {missing}")
    for unexpected in sorted(actual - expected):
        report(f"tree에 예상하지 않은 파일이 있습니다: {unexpected}")

    docs = {
        path.relative_to(ROOT).as_posix()
        for path in (ROOT / "docs").rglob("*.md")
        if path.is_file()
    }
    if docs != EXPECTED_DOCS:
        for missing in sorted(EXPECTED_DOCS - docs):
            report(f"학습 문서가 없습니다: {missing}")
        for unexpected in sorted(docs - EXPECTED_DOCS):
            report(f"예상하지 않은 학습 문서입니다: {unexpected}")

    exercises = {
        path.parent.relative_to(ROOT).as_posix()
        for path in (ROOT / "exercises").rglob("README.md")
        if path.is_file()
    }
    if exercises != EXPECTED_EXERCISES:
        for missing in sorted(EXPECTED_EXERCISES - exercises):
            report(f"실습이 없습니다: {missing}")
        for unexpected in sorted(exercises - EXPECTED_EXERCISES):
            report(f"예상하지 않은 실습입니다: {unexpected}")

    for relative in sorted(FORBIDDEN_PATHS):
        path = ROOT / relative
        if path.exists() or path.is_symlink():
            report(f"이전 경로가 남았습니다: {relative}")


def check_text_hygiene() -> None:
    for path in source_files():
        relative = path.relative_to(ROOT).as_posix()
        if path.is_symlink():
            continue
        data = path.read_bytes()
        if not data:
            report(f"빈 파일이 남았습니다: {relative}")
            continue
        if b"\0" in data:
            report(f"NUL byte가 있는 source 파일입니다: {relative}")
            continue
        if b"\r\n" in data:
            report(f"CRLF 줄바꿈이 있습니다: {relative}")
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError:
            report(f"UTF-8 text가 아닌 source 파일입니다: {relative}")
            continue
        for number, line in enumerate(text.splitlines(), start=1):
            if line.rstrip(" \t") != line:
                report(f"줄 끝 공백이 있습니다: {relative}:{number}")


def check_markdown() -> None:
    link_pattern = re.compile(r"(?<!!)\[[^\]]+\]\(([^)]+)\)")
    for path in sorted(ROOT.rglob("*.md")):
        if any(part in EXCLUDED_DIRECTORIES for part in path.relative_to(ROOT).parts):
            continue
        relative = path.relative_to(ROOT)
        text = path.read_text(encoding="utf-8")
        lines = text.splitlines()
        if not lines or not lines[0].startswith("# "):
            report(f"첫 줄에 H1 제목이 없습니다: {relative}")

        in_fence = False
        fence = ""
        prose_lines: list[str] = []
        for line in lines:
            stripped = line.lstrip()
            if stripped.startswith(("```", "~~~")):
                marker = stripped[:3]
                if not in_fence:
                    in_fence = True
                    fence = marker
                elif marker == fence:
                    in_fence = False
                continue
            if not in_fence:
                prose_lines.append(re.sub(r"`[^`]*`", "", line))
        if in_fence:
            report(f"닫히지 않은 코드 블록이 있습니다: {relative}")

        prose = "\n".join(prose_lines)
        for raw_target in link_pattern.findall(prose):
            target = raw_target.strip().split()[0].strip("<>")
            if target.startswith(("http://", "https://", "mailto:")):
                continue
            decoded = unquote(target)
            file_part, _, fragment = decoded.partition("#")
            resolved = path if not file_part else (path.parent / file_part).resolve()
            try:
                resolved.relative_to(ROOT)
            except ValueError:
                report(f"저장소 밖을 가리키는 링크입니다: {relative} -> {target}")
                continue
            if not resolved.exists():
                report(f"대상이 없는 링크입니다: {relative} -> {target}")
            elif fragment and resolved.suffix.lower() == ".md":
                if fragment.lower() not in markdown_headings(resolved):
                    report(f"대상이 없는 문서 앵커입니다: {relative} -> {target}")


def section(text: str, heading: str) -> tuple[int, str] | None:
    pattern = re.compile(
        rf"^## {re.escape(heading)}\s*$\n(.*?)(?=^## |\Z)",
        re.MULTILINE | re.DOTALL,
    )
    match = pattern.search(text)
    return None if match is None else (match.start(), match.group(1).strip())


def check_exercise_rubrics() -> None:
    rubric_signatures: dict[str, str] = {}
    for exercise in sorted(EXPECTED_EXERCISES):
        readme = ROOT / exercise / "README.md"
        if not readme.is_file():
            continue
        text = readme.read_text(encoding="utf-8")
        required = ["목표", "완료 기준", "자기 설명", "검증"]
        sections = {heading: section(text, heading) for heading in required}
        for heading, found in sections.items():
            if found is None:
                report(f"실습 루브릭에 '## {heading}'이 없습니다: {exercise}")
        if any(found is None for found in sections.values()):
            continue
        positions = [sections[heading][0] for heading in required]  # type: ignore[index]
        if positions != sorted(positions):
            report(f"실습 루브릭 순서는 목표 → 완료 기준 → 자기 설명 → 검증이어야 합니다: {exercise}")

        completion = sections["완료 기준"][1]  # type: ignore[index]
        explanation = sections["자기 설명"][1]  # type: ignore[index]
        verification = sections["검증"][1]  # type: ignore[index]
        if len(re.findall(r"^- \[ \] .+", completion, re.MULTILINE)) < 3:
            report(f"관찰 가능한 완료 기준이 3개 미만입니다: {exercise}")
        if len(re.findall(r"^- .+\?\s*$", explanation, re.MULTILINE)) < 2:
            report(f"실습별 자기 설명 질문이 2개 미만입니다: {exercise}")
        if not any(token in verification for token in ("mvn-guide.sh", "verify.sh")):
            report(f"실행 가능한 검증 명령이 없습니다: {exercise}")

        signature = re.sub(r"\s+", " ", completion + "\n" + explanation).strip().lower()
        previous = rubric_signatures.get(signature)
        if previous is not None:
            report(f"복사형 완료 기준·자기 설명을 사용했습니다: {previous}, {exercise}")
        rubric_signatures[signature] = exercise


def check_poms_and_sources() -> None:
    namespace = {"m": "http://maven.apache.org/POM/4.0.0"}
    for path in sorted(ROOT.rglob("pom.xml")):
        if any(part in EXCLUDED_DIRECTORIES for part in path.relative_to(ROOT).parts):
            continue
        relative = path.relative_to(ROOT)
        try:
            tree = ET.parse(path)
        except ET.ParseError as error:
            report(f"잘못된 POM XML입니다: {relative}: {error}")
            continue
        if path == ROOT / "pom.xml":
            modules = {
                element.text.strip()
                for element in tree.findall("./m:modules/m:module", namespace)
                if element.text
            }
            if modules != EXPECTED_MODULES:
                for missing in sorted(EXPECTED_MODULES - modules):
                    report(f"루트 POM에 빠진 모듈: {missing}")
                for unexpected in sorted(modules - EXPECTED_MODULES):
                    report(f"루트 POM의 예상하지 않은 모듈: {unexpected}")

    for path in sorted(ROOT.rglob("*.java")):
        if any(part in EXCLUDED_DIRECTORIES for part in path.relative_to(ROOT).parts):
            continue
        relative = path.relative_to(ROOT)
        text = path.read_text(encoding="utf-8")
        package = re.search(r"^package\s+([\w.]+);", text, re.MULTILINE)
        if not package:
            report(f"package 선언이 없습니다: {relative}")
            continue
        expected = Path(*package.group(1).split(".")) / path.name
        if not path.as_posix().endswith(expected.as_posix()):
            report(f"package와 파일 경로가 다릅니다: {relative}")
        if "/reference/" in path.as_posix() and re.search(r"\b(?:TODO|FIXME)\b", text):
            report(f"reference 소스에 TODO/FIXME가 남았습니다: {relative}")


def check_test_pairs() -> None:
    for exercise in sorted(EXPECTED_EXERCISES):
        if exercise.endswith("01-multi-repository-maven"):
            continue
        skeleton = ROOT / exercise / "skeleton/src/test"
        reference = ROOT / exercise / "reference/src/test"
        skeleton_files = {
            path.relative_to(skeleton).as_posix(): path
            for path in skeleton.rglob("*")
            if path.is_file()
        }
        reference_files = {
            path.relative_to(reference).as_posix(): path
            for path in reference.rglob("*")
            if path.is_file()
        }
        if skeleton_files.keys() != reference_files.keys():
            report(f"skeleton/reference 테스트 파일 집합이 다릅니다: {exercise}")
            continue
        for relative in sorted(skeleton_files):
            if skeleton_files[relative].read_bytes() != reference_files[relative].read_bytes():
                report(f"skeleton/reference 테스트가 byte-identical하지 않습니다: {exercise}/{relative}")


def check_toolchain_and_modes() -> None:
    wrapper = (ROOT / ".mvn/wrapper/maven-wrapper.properties").read_text(encoding="utf-8")
    expected_wrapper = {
        "wrapperVersion=3.3.4",
        "distributionType=only-script",
        "distributionUrl=https://repo.maven.apache.org/maven2/org/apache/maven/apache-maven/3.9.16/apache-maven-3.9.16-bin.zip",
        "distributionSha256Sum=5af3b743dd8b876b5c45da33b676251e5f1687712644abb4ee519ca56e1d89ce",
    }
    if set(wrapper.splitlines()) != expected_wrapper:
        report("Maven Wrapper 3.3.4/3.9.16/SHA-256 고정값이 정확하지 않습니다.")

    root_pom = (ROOT / "pom.xml").read_text(encoding="utf-8")
    for required in (
        "<maven.compiler.release>17</maven.compiler.release>",
        "<junit.version>6.1.0</junit.version>",
        "<assertj.version>3.27.7</assertj.version>",
        "<artifactId>junit-platform-launcher</artifactId>",
        "<version>[21,22)</version>",
        "<version>[3.9.16,3.9.17)</version>",
        "spotless-maven-plugin",
        "maven-checkstyle-plugin",
    ):
        if required not in root_pom:
            report(f"루트 POM의 고정 계약이 빠졌습니다: {required}")
    consumer = (
        ROOT
        / "exercises/03-build-test-and-evidence/01-multi-repository-maven/consumer-service/pom.xml"
    ).read_text(encoding="utf-8")
    if "<junit.version>6.1.0</junit.version>" not in consumer:
        report("독립 consumer POM의 JUnit 버전이 6.1.0이 아닙니다.")

    for relative in sorted(EXECUTABLE_FILES):
        path = ROOT / relative
        if not path.is_file() or not path.stat().st_mode & stat.S_IXUSR:
            report(f"실행 권한이 없습니다: {relative}")


def main() -> int:
    check_exact_tree()
    check_text_hygiene()
    check_markdown()
    check_exercise_rubrics()
    check_poms_and_sources()
    check_test_pairs()
    check_toolchain_and_modes()
    if ERRORS:
        print(f"검사 실패: {len(ERRORS)}건", file=sys.stderr)
        for error in ERRORS:
            print(f"- {error}", file=sys.stderr)
        return 1
    print("Java 가이드 문서·정확한 tree·실습·도구 계약 검사를 통과했습니다.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
