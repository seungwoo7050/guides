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
GENERATED_DIRECTORIES = {
    ".git",
    ".guide",
    ".workspace",
    "target",
    "examples/runtime-model/target",
    "exercises/01-language-and-domain/01-first-program/reference/target",
    "exercises/01-language-and-domain/01-first-program/skeleton/target",
    "exercises/01-language-and-domain/02-value-object-contract/reference/target",
    "exercises/01-language-and-domain/02-value-object-contract/skeleton/target",
    "exercises/02-runtime-and-concurrency/01-concurrent-state-update/reference/target",
    "exercises/02-runtime-and-concurrency/01-concurrent-state-update/skeleton/target",
    "exercises/02-runtime-and-concurrency/02-executor-lifecycle/reference/target",
    "exercises/02-runtime-and-concurrency/02-executor-lifecycle/skeleton/target",
    "exercises/03-build-test-and-evidence/01-multi-repository-maven/.workspace",
    "exercises/03-build-test-and-evidence/01-multi-repository-maven/consumer-service/target",
    "exercises/03-build-test-and-evidence/01-multi-repository-maven/contract-library/target",
    "exercises/03-build-test-and-evidence/02-state-and-effect-testing/reference/target",
    "exercises/03-build-test-and-evidence/02-state-and-effect-testing/skeleton/target",
    "exercises/04-capstone/01-concurrent-job-ledger/reference/target",
    "exercises/04-capstone/01-concurrent-job-ledger/skeleton/target",
    "scripts/__pycache__",
}

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

WORKSPACE_EXERCISES = {
    "exercises/01-language-and-domain/01-first-program": "first-program",
    "exercises/01-language-and-domain/02-value-object-contract": "value-object-contract",
    "exercises/02-runtime-and-concurrency/01-concurrent-state-update": "concurrent-state-update",
    "exercises/02-runtime-and-concurrency/02-executor-lifecycle": "executor-lifecycle",
    "exercises/03-build-test-and-evidence/02-state-and-effect-testing": "state-and-effect-testing",
    "exercises/04-capstone/01-concurrent-job-ledger": "concurrent-job-ledger",
}

ORDERED_LEARNING_ROWS: tuple[tuple[str, ...], ...] = (
    (
        "docs/00-roadmap.md",
        "make check",
        "docs/01-language-and-domain/01-jdk-jvm-and-first-program.md",
    ),
    (
        "docs/01-language-and-domain/01-jdk-jvm-and-first-program.md",
        "examples/runtime-model/README.md",
        "exercises/01-language-and-domain/01-first-program/README.md",
        ".workspace/first-program",
        "./scripts/check-workspace.sh exercises/01-language-and-domain/01-first-program",
        "아직 `reference/`를 보지 않고",
    ),
    (
        "docs/01-language-and-domain/02-java-language-foundations.md",
        ".workspace/first-program",
        "exercises/01-language-and-domain/01-first-program/reference/",
        "통과·자기 설명 뒤",
    ),
    (
        "docs/01-language-and-domain/03-domain-types-records-and-sealed-types.md",
        "exercises/01-language-and-domain/02-value-object-contract/README.md",
        ".workspace/value-object-contract",
        "./scripts/check-workspace.sh exercises/01-language-and-domain/02-value-object-contract",
        "아직 `reference/`를 보지 않고",
    ),
    (
        "docs/01-language-and-domain/04-collections-streams-and-numeric-invariants.md",
        ".workspace/value-object-contract",
        "./scripts/check-workspace.sh exercises/01-language-and-domain/02-value-object-contract",
        "아직 `reference/`를 보지 않고",
    ),
    (
        "docs/01-language-and-domain/05-errors-validation-time-and-identifiers.md",
        ".workspace/value-object-contract",
        "./scripts/check-workspace.sh exercises/01-language-and-domain/02-value-object-contract",
        "exercises/01-language-and-domain/02-value-object-contract/reference/",
        "통과·자기 설명 뒤",
    ),
    (
        "docs/02-runtime-and-concurrency/01-concurrency-locking-and-executors.md",
        "exercises/02-runtime-and-concurrency/01-concurrent-state-update/README.md",
        ".workspace/concurrent-state-update",
        "./scripts/check-workspace.sh exercises/02-runtime-and-concurrency/01-concurrent-state-update",
        "통과·자기 설명 뒤 해당 `reference/`",
    ),
    (
        "docs/02-runtime-and-concurrency/01-concurrency-locking-and-executors.md",
        "exercises/02-runtime-and-concurrency/02-executor-lifecycle/README.md",
        ".workspace/executor-lifecycle",
        "./scripts/check-workspace.sh exercises/02-runtime-and-concurrency/02-executor-lifecycle",
        "통과·자기 설명 뒤 해당 `reference/`",
    ),
    (
        "docs/03-build-test-and-evidence/01-maven-wrapper-and-lifecycle.md",
        "exercises/03-build-test-and-evidence/01-multi-repository-maven/README.md",
        "./exercises/03-build-test-and-evidence/01-multi-repository-maven/verify.sh",
        "별도 `reference/`는 없습니다",
    ),
    (
        "docs/03-build-test-and-evidence/02-junit-assertj-and-test-doubles.md",
        "exercises/03-build-test-and-evidence/02-state-and-effect-testing/README.md",
        ".workspace/state-and-effect-testing",
        "./scripts/check-workspace.sh exercises/03-build-test-and-evidence/02-state-and-effect-testing",
        "통과·자기 설명 뒤 해당 `reference/`",
    ),
    (
        "docs/03-build-test-and-evidence/03-quality-profiling-and-evidence.md",
        "make check",
        "make verify",
        "docs/04-capstone.md",
    ),
    (
        "docs/04-capstone.md",
        "exercises/04-capstone/01-concurrent-job-ledger/README.md",
        ".workspace/concurrent-job-ledger",
        "./scripts/check-workspace.sh exercises/04-capstone/01-concurrent-job-ledger",
        "통과·자기 설명 뒤 해당 `reference/`",
        "make verify",
    ),
)

OBSERVATION_EXERCISE = (
    "exercises/03-build-test-and-evidence/01-multi-repository-maven"
)

EXPECTED_MODULES = {
    "examples/runtime-model",
    "exercises/01-language-and-domain/01-first-program/reference",
    "exercises/01-language-and-domain/02-value-object-contract/reference",
    "exercises/02-runtime-and-concurrency/01-concurrent-state-update/reference",
    "exercises/02-runtime-and-concurrency/02-executor-lifecycle/reference",
    "exercises/03-build-test-and-evidence/02-state-and-effect-testing/reference",
    "exercises/04-capstone/01-concurrent-job-ledger/reference",
}

IMPLEMENTATION_SCOPES: dict[str, tuple[str, tuple[str, ...]]] = {
    "runtime-model": (
        "examples/runtime-model/README.md",
        (
            "examples/runtime-model/README.md",
            "examples/runtime-model/pom.xml",
            "examples/runtime-model/src/main/java/",
        ),
    ),
    "first-program": (
        "exercises/01-language-and-domain/01-first-program/README.md",
        (
            "exercises/01-language-and-domain/01-first-program/README.md",
            "exercises/01-language-and-domain/01-first-program/reference/pom.xml",
            "exercises/01-language-and-domain/01-first-program/reference/src/main/java/",
        ),
    ),
    "value-object-contract": (
        "exercises/01-language-and-domain/02-value-object-contract/README.md",
        (
            "exercises/01-language-and-domain/02-value-object-contract/README.md",
            "exercises/01-language-and-domain/02-value-object-contract/reference/pom.xml",
            "exercises/01-language-and-domain/02-value-object-contract/reference/src/main/java/",
        ),
    ),
    "concurrent-state-update": (
        "exercises/02-runtime-and-concurrency/01-concurrent-state-update/README.md",
        (
            "exercises/02-runtime-and-concurrency/01-concurrent-state-update/README.md",
            "exercises/02-runtime-and-concurrency/01-concurrent-state-update/reference/pom.xml",
            "exercises/02-runtime-and-concurrency/01-concurrent-state-update/reference/src/main/java/",
        ),
    ),
    "executor-lifecycle": (
        "exercises/02-runtime-and-concurrency/02-executor-lifecycle/README.md",
        (
            "exercises/02-runtime-and-concurrency/02-executor-lifecycle/README.md",
            "exercises/02-runtime-and-concurrency/02-executor-lifecycle/reference/pom.xml",
            "exercises/02-runtime-and-concurrency/02-executor-lifecycle/reference/src/main/java/",
        ),
    ),
    "multi-repository-maven": (
        "exercises/03-build-test-and-evidence/01-multi-repository-maven/README.md",
        (
            "exercises/03-build-test-and-evidence/01-multi-repository-maven/README.md",
            "exercises/03-build-test-and-evidence/01-multi-repository-maven/contract-library/pom.xml",
            "exercises/03-build-test-and-evidence/01-multi-repository-maven/contract-library/src/main/java/",
            "exercises/03-build-test-and-evidence/01-multi-repository-maven/consumer-service/pom.xml",
            "exercises/03-build-test-and-evidence/01-multi-repository-maven/consumer-service/src/main/java/",
        ),
    ),
    "state-and-effect-testing": (
        "exercises/03-build-test-and-evidence/02-state-and-effect-testing/README.md",
        (
            "exercises/03-build-test-and-evidence/02-state-and-effect-testing/README.md",
            "exercises/03-build-test-and-evidence/02-state-and-effect-testing/reference/pom.xml",
            "exercises/03-build-test-and-evidence/02-state-and-effect-testing/reference/src/main/java/",
        ),
    ),
    "concurrent-job-ledger": (
        "exercises/04-capstone/01-concurrent-job-ledger/README.md",
        (
            "exercises/04-capstone/01-concurrent-job-ledger/README.md",
            "exercises/04-capstone/01-concurrent-job-ledger/reference/pom.xml",
            "exercises/04-capstone/01-concurrent-job-ledger/reference/src/main/java/",
        ),
    ),
}

IMPLEMENTATION_REQUIRED_FILES: dict[str, tuple[str, ...]] = {
    "runtime-model": (
        "examples/runtime-model/pom.xml",
        "examples/runtime-model/src/main/java/dev/guides/java/runtime/RuntimeProbe.java",
    ),
    "first-program": (
        "exercises/01-language-and-domain/01-first-program/reference/src/main/java/dev/guides/java/firstprogram/NumberReportApplication.java",
    ),
    "value-object-contract": (
        "exercises/01-language-and-domain/02-value-object-contract/reference/src/main/java/dev/guides/java/valueobject/Currency.java",
        "exercises/01-language-and-domain/02-value-object-contract/reference/src/main/java/dev/guides/java/valueobject/Money.java",
    ),
    "concurrent-state-update": (
        "exercises/02-runtime-and-concurrency/01-concurrent-state-update/reference/src/main/java/dev/guides/java/concurrentstate/DeterministicRaceDemo.java",
        "exercises/02-runtime-and-concurrency/01-concurrent-state-update/reference/src/main/java/dev/guides/java/concurrentstate/LockedCounter.java",
        "exercises/02-runtime-and-concurrency/01-concurrent-state-update/reference/src/main/java/dev/guides/java/concurrentstate/RacyCounter.java",
    ),
    "executor-lifecycle": (
        "exercises/02-runtime-and-concurrency/02-executor-lifecycle/reference/src/main/java/dev/guides/java/executor/BoundedTaskRunner.java",
        "exercises/02-runtime-and-concurrency/02-executor-lifecycle/reference/src/main/java/dev/guides/java/executor/ExecutorProbe.java",
    ),
    "multi-repository-maven": (
        "exercises/03-build-test-and-evidence/01-multi-repository-maven/contract-library/pom.xml",
        "exercises/03-build-test-and-evidence/01-multi-repository-maven/contract-library/src/main/java/dev/guides/contract/ContractVersion.java",
        "exercises/03-build-test-and-evidence/01-multi-repository-maven/consumer-service/pom.xml",
        "exercises/03-build-test-and-evidence/01-multi-repository-maven/consumer-service/src/main/java/dev/guides/consumer/ConsumerApplication.java",
    ),
    "state-and-effect-testing": (
        "exercises/03-build-test-and-evidence/02-state-and-effect-testing/reference/src/main/java/dev/guides/java/stateeffect/ExternalEffect.java",
        "exercises/03-build-test-and-evidence/02-state-and-effect-testing/reference/src/main/java/dev/guides/java/stateeffect/IdempotentOperationService.java",
        "exercises/03-build-test-and-evidence/02-state-and-effect-testing/reference/src/main/java/dev/guides/java/stateeffect/OperationResult.java",
        "exercises/03-build-test-and-evidence/02-state-and-effect-testing/reference/src/main/java/dev/guides/java/stateeffect/StateStore.java",
    ),
    "concurrent-job-ledger": (
        "exercises/04-capstone/01-concurrent-job-ledger/reference/src/main/java/dev/guides/java/jobledger/ConcurrentJobLedger.java",
        "exercises/04-capstone/01-concurrent-job-ledger/reference/src/main/java/dev/guides/java/jobledger/CreditJob.java",
        "exercises/04-capstone/01-concurrent-job-ledger/reference/src/main/java/dev/guides/java/jobledger/DebitJob.java",
        "exercises/04-capstone/01-concurrent-job-ledger/reference/src/main/java/dev/guides/java/jobledger/JobCommand.java",
        "exercises/04-capstone/01-concurrent-job-ledger/reference/src/main/java/dev/guides/java/jobledger/JobId.java",
        "exercises/04-capstone/01-concurrent-job-ledger/reference/src/main/java/dev/guides/java/jobledger/JobKind.java",
        "exercises/04-capstone/01-concurrent-job-ledger/reference/src/main/java/dev/guides/java/jobledger/JobReceipt.java",
    ),
}

IMPLEMENTATION_TOKEN_PREFIX = "[" + "Implementation "
IMPLEMENTATION_PATTERN = re.compile(
    re.escape(IMPLEMENTATION_TOKEN_PREFIX) + r"([^\]\r\n]+)\]"
)
IMPLEMENTATION_LABEL = re.compile(r"(?:0|[1-9]\d*(?:-[1-9]\d*)?)")

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
    "scripts/new-workspace.sh",
    "scripts/check-workspace.sh",
    "scripts/preflight.sh",
    "scripts/record-executor-jfr.sh",
    "scripts/smoke-javac.sh",
    "scripts/verify-skeletons.sh",
    "exercises/03-build-test-and-evidence/01-multi-repository-maven/verify.sh",
}


def report(message: str) -> None:
    ERRORS.append(message)


def generated(relative: str) -> bool:
    return any(
        relative == directory or relative.startswith(f"{directory}/")
        for directory in GENERATED_DIRECTORIES
    )


def source_files() -> list[Path]:
    files: list[Path] = []
    for directory, names, filenames in os.walk(ROOT, followlinks=False):
        base = Path(directory)
        names[:] = sorted(
            name
            for name in names
            if not generated((base / name).relative_to(ROOT).as_posix())
        )
        for name in sorted(filenames):
            path = base / name
            relative = path.relative_to(ROOT).as_posix()
            if not generated(relative):
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
        if generated(path.relative_to(ROOT).as_posix()):
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
    completion_signatures: dict[str, str] = {}
    explanation_signatures: dict[str, str] = {}
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
        if exercise in WORKSPACE_EXERCISES:
            expected_command = f"./scripts/check-workspace.sh {exercise}"
        else:
            expected_command = f"./{OBSERVATION_EXERCISE}/verify.sh"
        if expected_command not in verification:
            report(f"정본 learner 검증 명령이 없습니다: {exercise}: {expected_command}")

        completion_signature = re.sub(r"\s+", " ", completion).strip().lower()
        previous = completion_signatures.get(completion_signature)
        if previous is not None:
            report(f"복사형 완료 기준을 사용했습니다: {previous}, {exercise}")
        completion_signatures[completion_signature] = exercise

        explanation_signature = re.sub(r"\s+", " ", explanation).strip().lower()
        previous = explanation_signatures.get(explanation_signature)
        if previous is not None:
            report(f"복사형 자기 설명 질문을 사용했습니다: {previous}, {exercise}")
        explanation_signatures[explanation_signature] = exercise


def check_workspace_contract() -> None:
    manifest = ROOT / "scripts/workspaces.txt"
    expected = {
        f"{exercise}\t{name}" for exercise, name in WORKSPACE_EXERCISES.items()
    }
    if not manifest.is_file() or set(manifest.read_text(encoding="utf-8").splitlines()) != expected:
        report("learner workspace manifest가 정확하지 않습니다: scripts/workspaces.txt")

    script_contracts = {
        "scripts/new-workspace.sh": (
            "manifest에 없는 exercise 경로",
            "skeleton의 symlink는 허용하지 않습니다",
            "workspace가 이미 있습니다",
            "<relativePath>../../pom.xml</relativePath>",
        ),
        "scripts/check-workspace.sh": (
            "workspace가 저장소 경계를 벗어났습니다",
            "공개 테스트를 변경했습니다",
            "workspace POM 계약을 변경했습니다",
            '"$ROOT/scripts/mvn-guide.sh" -f "$workspace/pom.xml" test',
        ),
    }
    for relative, tokens in script_contracts.items():
        path = ROOT / relative
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8")
        for token in tokens:
            if token not in text:
                report(f"workspace 도구 계약이 빠졌습니다: {relative}: {token}")


def check_public_commands() -> None:
    required = ("make prepare", "make check", "make verify", "make clean")
    for relative in ("README.md", "CONTRIBUTING.md"):
        text = (ROOT / relative).read_text(encoding="utf-8")
        for command in required:
            if command not in text:
                report(f"공개 명령 안내가 빠졌습니다: {relative}: {command}")


def check_observation_exercise_contract() -> None:
    relative = f"{OBSERVATION_EXERCISE}/verify.sh"
    path = ROOT / relative
    if not path.is_file():
        return
    text = path.read_text(encoding="utf-8")
    for token in (
        ".guide/java/prepared.json",
        "preparation-capture",
        "marker-field",
        "maven_repository",
        "maven_user_home",
        "GUIDE_MAVEN_REPOSITORY",
        "MAVEN_USER_HOME",
    ):
        if token not in text:
            report(f"Maven 관찰 실습의 standalone cache 계약이 빠졌습니다: {relative}: {token}")


def check_ordered_learning_map() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    found = section(readme, "정본 학습 순서")
    if found is None:
        report("README에 정본 학습 순서가 없습니다.")
        return
    mapping = found[1]
    header = "| 순서 | 문서 | 관찰 예제 | 직접 수행 | 수정 위치 | 검증 | 완료 뒤 비교·다음 |"
    if header not in mapping:
        report("README 정본 학습 표의 canonical semantic field가 빠졌습니다.")

    parsed: list[tuple[int, list[str]]] = []
    for line in mapping.splitlines():
        if re.match(r"^\|\s*\d+\s*\|", line) is None:
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) != 7:
            report(f"README 정본 학습 표의 field 수가 7이 아닙니다: {line}")
            continue
        parsed.append((int(cells[0]), cells))

    actual_order = [number for number, _ in parsed]
    expected_order = list(range(len(ORDERED_LEARNING_ROWS)))
    if actual_order != expected_order:
        report(
            "README 정본 학습 표의 순서가 0부터 연속적이지 않습니다: "
            + ", ".join(str(number) for number in actual_order)
        )

    rows = {number: cells for number, cells in parsed}
    if len(rows) != len(parsed):
        report("README 정본 학습 표에 중복 순서가 있습니다.")
    for number, required_tokens in enumerate(ORDERED_LEARNING_ROWS):
        cells = rows.get(number)
        if cells is None:
            continue
        row = " | ".join(cells[1:])
        for token in required_tokens:
            if token not in row:
                report(f"README 정본 학습 표 {number}행의 대응이 잘못되었습니다: {token}")

    required_paths = {
        *EXPECTED_DOCS,
        "examples/runtime-model/README.md",
        *(f"{exercise}/README.md" for exercise in EXPECTED_EXERCISES),
    }
    for relative in sorted(required_paths):
        if relative not in mapping:
            report(f"README 정본 학습 표에 경로가 빠졌습니다: {relative}")

    for exercise, workspace in sorted(WORKSPACE_EXERCISES.items()):
        command = f"./scripts/check-workspace.sh {exercise}"
        if command not in mapping:
            report(f"README 정본 학습 표에 learner 검증 명령이 빠졌습니다: {exercise}")
        if f".workspace/{workspace}" not in mapping:
            report(f"README 정본 학습 표에 수정 위치가 빠졌습니다: .workspace/{workspace}")

    if "완료 뒤" not in mapping or "reference/" not in mapping:
        report("README 정본 학습 표에 완료 뒤 reference 비교 시점이 없습니다.")


def annotation_scope(relative: str) -> str | None:
    matched: list[str] = []
    for name, (_, allowed) in IMPLEMENTATION_SCOPES.items():
        if any(relative == entry or (entry.endswith("/") and relative.startswith(entry)) for entry in allowed):
            matched.append(name)
    if len(matched) > 1:
        report(f"Implementation annotation scope가 겹칩니다: {relative}: {', '.join(matched)}")
    return matched[0] if len(matched) == 1 else None


def marker_is_comment(path: Path, line: str, in_fence: bool) -> bool:
    stripped = line.strip()
    if path.suffix == ".java":
        return stripped.startswith(("//", "/*", "*"))
    if path.suffix == ".xml":
        return stripped.startswith("<!--") and stripped.endswith("-->")
    if path.suffix == ".md":
        return not in_fence and stripped.startswith("|")
    return False


def implementation_index(readme: Path) -> list[str]:
    found = section(readme.read_text(encoding="utf-8"), "권장 구현 순서")
    if found is None:
        report(f"annotation scope README에 권장 구현 순서가 없습니다: {readme.relative_to(ROOT)}")
        return []
    labels: list[str] = []
    row = re.compile(
        r"^\|\s*(?:"
        + re.escape(IMPLEMENTATION_TOKEN_PREFIX)
        + r")?(0|[1-9]\d*(?:-[1-9]\d*)?)(?:\])?\s*\|"
    )
    for line in found[1].splitlines():
        match = row.match(line)
        if match:
            labels.append(match.group(1))
    if len(labels) != len(set(labels)):
        report(f"권장 구현 순서 index에 중복 번호가 있습니다: {readme.relative_to(ROOT)}")
    return labels


def check_numbering(scope: str, labels: list[str]) -> None:
    top_level = sorted(int(label) for label in labels if "-" not in label and label != "0")
    if not top_level:
        report(f"Implementation top-level 번호가 없습니다: {scope}")
        return
    expected_top = list(range(1, max(top_level) + 1))
    if top_level != expected_top:
        report(f"Implementation top-level 번호가 연속적이지 않습니다: {scope}: {top_level}")

    parents = set(top_level)
    children: dict[int, list[int]] = {}
    for label in labels:
        if "-" not in label:
            continue
        parent_text, child_text = label.split("-", 1)
        parent = int(parent_text)
        child = int(child_text)
        if parent not in parents:
            report(f"parent가 없는 Implementation substep입니다: {scope}: {label}")
        children.setdefault(parent, []).append(child)
    for parent, values in sorted(children.items()):
        ordered = sorted(values)
        if ordered != list(range(1, max(ordered) + 1)):
            report(f"Implementation substep 번호가 연속적이지 않습니다: {scope}: {ordered}")


def check_implementation_annotations() -> None:
    anchors: dict[str, list[tuple[str, int, str]]] = {
        name: [] for name in IMPLEMENTATION_SCOPES
    }
    for path in source_files():
        if path.is_symlink():
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        relative = path.relative_to(ROOT).as_posix()
        in_fence = False
        fence = ""
        for number, line in enumerate(text.splitlines(), start=1):
            stripped = line.lstrip()
            line_in_fence = in_fence
            if path.suffix == ".md" and stripped.startswith(("```", "~~~")):
                marker = stripped[:3]
                if not in_fence:
                    in_fence = True
                    fence = marker
                elif marker == fence:
                    in_fence = False
                continue
            for match in IMPLEMENTATION_PATTERN.finditer(line):
                label = match.group(1)
                scope = annotation_scope(relative)
                if scope is None:
                    report(f"허용 범위 밖 Implementation annotation입니다: {relative}:{number}")
                    continue
                if not IMPLEMENTATION_LABEL.fullmatch(label) or label.startswith("0-"):
                    report(f"잘못된 Implementation 번호입니다: {relative}:{number}: {label}")
                    continue
                if not marker_is_comment(path, line, line_in_fence):
                    report(f"주석 또는 README sidecar가 아닌 annotation입니다: {relative}:{number}")
                    continue
                anchors[scope].append((label, number, relative))

    for scope, occurrences in anchors.items():
        labels = [label for label, _, _ in occurrences]
        if not labels:
            report(f"Implementation annotation이 없는 scope입니다: {scope}")
            continue
        if labels.count("0") > 1:
            report(f"Implementation 0이 scope에 둘 이상 있습니다: {scope}")
        duplicates = sorted({label for label in labels if labels.count(label) > 1})
        for label in duplicates:
            locations = [f"{relative}:{number}" for value, number, relative in occurrences if value == label]
            report(f"중복 Implementation anchor입니다: {scope}: {label}: {', '.join(locations)}")
        unique = sorted(set(labels), key=lambda value: tuple(int(part) for part in value.split("-")))
        check_numbering(scope, unique)

        anchored_files = {relative for _, _, relative in occurrences}
        for required in IMPLEMENTATION_REQUIRED_FILES[scope]:
            if required not in anchored_files:
                report(f"Implementation annotation이 빠진 완성 파일입니다: {scope}: {required}")

        readme_relative = IMPLEMENTATION_SCOPES[scope][0]
        indexed = implementation_index(ROOT / readme_relative)
        if indexed != unique:
            missing = sorted(set(unique) - set(indexed))
            orphan = sorted(set(indexed) - set(unique))
            if missing:
                report(f"README index에 없는 Implementation anchor입니다: {scope}: {', '.join(missing)}")
            if orphan:
                report(f"source anchor가 없는 README implementation row입니다: {scope}: {', '.join(orphan)}")
            if not missing and not orphan:
                report(f"README implementation index 순서가 권장 구현 순서와 다릅니다: {scope}")


def check_poms_and_sources() -> None:
    namespace = {"m": "http://maven.apache.org/POM/4.0.0"}
    for path in sorted(ROOT.rglob("pom.xml")):
        if generated(path.relative_to(ROOT).as_posix()):
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
        if generated(path.relative_to(ROOT).as_posix()):
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
    check_workspace_contract()
    check_public_commands()
    check_observation_exercise_contract()
    check_ordered_learning_map()
    check_implementation_annotations()
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
