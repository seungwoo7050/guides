#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

EXPECTED_DOCS = {
    "docs/00-roadmap.md",
    "docs/01-foundations/01-edit-compile-run.md",
    "docs/01-foundations/02-values-branches-loops.md",
    "docs/01-foundations/03-functions-arrays-text.md",
    "docs/01-foundations/04-input-errors-debugging.md",
    "docs/02-c-language/01-c-program-model.md",
    "docs/02-c-language/02-memory-pointers-strings.md",
    "docs/02-c-language/03-data-structures-api-design.md",
    "docs/02-c-language/04-build-link-test.md",
    "docs/02-c-language/05-variadic-format-api.md",
    "docs/03-unix-programming/01-posix-io-streams.md",
    "docs/03-unix-programming/02-process-fd-pipe.md",
    "docs/03-unix-programming/03-signals-events.md",
    "docs/03-unix-programming/04-shell-parser-executor.md",
    "docs/04-concurrency/01-threads-time.md",
    "docs/90-appendix/01-debugger-reference.md",
    "docs/90-appendix/02-readline-integration.md",
    "docs/90-appendix/03-unix-text-testing.md",
}

EXPECTED_EXAMPLES = {
    "account-simulator",
    "command-pipeline",
    "command-runner",
    "diagnostic-formatter",
    "owned-string",
    "readline-repl",
    "record-stream",
    "signal-loop",
    "text-checks",
    "textkit",
}

EXPECTED_EXERCISES = {
    "01-foundations/01-number-report",
    "02-c-language/01-textkit",
    "02-c-language/02-owned-string",
    "02-c-language/03-int-vector",
    "02-c-language/04-diagnostic-formatter",
    "03-unix-programming/01-record-stream",
    "03-unix-programming/02-command-pipeline",
    "03-unix-programming/03-signal-loop",
    "03-unix-programming/04-command-runner",
    "04-concurrency/01-account-simulator",
}

ROOT_REQUIRED = {
    ".gitignore",
    "CONTRIBUTING.md",
    "LICENSE.md",
    "Makefile",
    "README.md",
    "prepare.sh",
    "verify.sh",
    "scripts/validate_docs.py",
    "scripts/validate_repository.py",
    "exercises/Makefile",
}

FORBIDDEN_PATHS = {
    "make-out.txt",
    "tree.txt",
    "reference",
    "docs/01-c-program-model.md",
    "docs/02-memory-pointers-strings.md",
    "docs/03-data-structures-api-design.md",
    "docs/04-build-link-test.md",
    "docs/05-variadic-format-api.md",
    "docs/06-posix-io-streams.md",
    "docs/07-process-fd-pipe.md",
    "docs/08-signals-events.md",
    "docs/09-shell-parser-executor.md",
    "docs/10-threads-time.md",
}

EXERCISE_TARGETS = {
    "exercise-build",
    "exercise-test",
    "reference-test",
    "sanitize",
    "clean",
}

EXERCISE_PEDAGOGY_SECTIONS = (
    "완료 기준",
    "자기 설명",
    "검증",
)

TEXT_SUFFIXES = {".c", ".h", ".md", ".py", ".sh", ".txt"}
SOURCE_SUFFIXES = {".c", ".h", ".py", ".sh"}
ARTIFACT_SUFFIXES = {
    ".o", ".a", ".d", ".pyc", ".gcda", ".gcno", ".gcov",
    ".profraw", ".profdata", ".out",
}
KNOWN_BINARIES = {
    "account_simulator",
    "command_pipeline",
    "command_runner",
    "libtextkit.a",
    "repl",
    "signal_loop",
    "textstat",
}


def relative(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def fail(message: str) -> None:
    print(f"저장소 구조 검사 실패: {message}", file=sys.stderr)
    raise SystemExit(1)


def require_path(path_text: str) -> None:
    path = ROOT / path_text
    if not path.exists():
        fail(f"필수 경로가 없습니다: {path_text}")


def check_root_contract() -> None:
    for path_text in sorted(ROOT_REQUIRED):
        require_path(path_text)
    for path_text in sorted(FORBIDDEN_PATHS):
        if (ROOT / path_text).exists():
            fail(f"삭제되어야 할 구형·생성 경로가 남았습니다: {path_text}")

    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    contributing = (ROOT / "CONTRIBUTING.md").read_text(encoding="utf-8")
    for command in ("./prepare.sh", "./verify.sh"):
        if command not in readme:
            fail(f"README.md에 정본 명령이 없습니다: {command}")
        if command not in contributing:
            fail(f"CONTRIBUTING.md에 정본 명령이 없습니다: {command}")


def check_docs() -> None:
    actual = {
        relative(path)
        for path in (ROOT / "docs").rglob("*.md")
        if path.is_file()
    }
    missing = EXPECTED_DOCS - actual
    unexpected = actual - EXPECTED_DOCS
    if missing:
        fail("계획한 문서가 없습니다: " + ", ".join(sorted(missing)))
    if unexpected:
        fail("계획 밖의 중복 문서가 있습니다: " + ", ".join(sorted(unexpected)))


def check_examples() -> None:
    examples = ROOT / "examples"
    actual = {path.name for path in examples.iterdir() if path.is_dir()}
    if actual != EXPECTED_EXAMPLES:
        missing = EXPECTED_EXAMPLES - actual
        unexpected = actual - EXPECTED_EXAMPLES
        details = []
        if missing:
            details.append("누락=" + ", ".join(sorted(missing)))
        if unexpected:
            details.append("예상 밖=" + ", ".join(sorted(unexpected)))
        fail("examples/ 구성이 계획과 다릅니다: " + "; ".join(details))
    root_makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
    for name in sorted(EXPECTED_EXAMPLES):
        require_path(f"examples/{name}/Makefile")
        if f"examples/{name}" not in root_makefile:
            fail(f"루트 Makefile이 예제를 열거하지 않습니다: {name}")


def makefile_has_target(text: str, target: str) -> bool:
    return re.search(rf"(?m)^{re.escape(target)}\s*:", text) is not None


def markdown_h2_sections(text: str) -> tuple[list[str], dict[str, str]]:
    matches = list(re.finditer(r"(?m)^## ([^\n]+?)\s*$", text))
    headings = [match.group(1) for match in matches]
    sections: dict[str, str] = {}
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        sections[match.group(1)] = text[match.end():end].strip()
    return headings, sections


def check_exercises() -> None:
    exercises = ROOT / "exercises"
    actual: set[str] = set()
    for makefile in exercises.rglob("Makefile"):
        if makefile.parent == exercises:
            continue
        actual.add(makefile.parent.relative_to(exercises).as_posix())
    if actual != EXPECTED_EXERCISES:
        missing = EXPECTED_EXERCISES - actual
        unexpected = actual - EXPECTED_EXERCISES
        details = []
        if missing:
            details.append("누락=" + ", ".join(sorted(missing)))
        if unexpected:
            details.append("예상 밖=" + ", ".join(sorted(unexpected)))
        fail("exercises/ 구성이 계획과 다릅니다: " + "; ".join(details))

    aggregate = (exercises / "Makefile").read_text(encoding="utf-8")
    completion_owners: dict[str, str] = {}
    explanation_owners: dict[str, str] = {}
    for name in sorted(EXPECTED_EXERCISES):
        root = exercises / name
        for required in ("README.md", "Makefile", "skeleton", "reference", "tests"):
            if not (root / required).exists():
                fail(f"연습문제 구성요소가 없습니다: exercises/{name}/{required}")
        if not any(path.is_file() for path in (root / "skeleton").rglob("*")):
            fail(f"skeleton이 비어 있습니다: exercises/{name}")
        if not any(path.is_file() for path in (root / "reference").rglob("*")):
            fail(f"reference가 비어 있습니다: exercises/{name}")
        if not any(path.is_file() for path in (root / "tests").rglob("*")):
            fail(f"tests가 비어 있습니다: exercises/{name}")

        makefile_text = (root / "Makefile").read_text(encoding="utf-8")
        missing_targets = sorted(
            target for target in EXERCISE_TARGETS
            if not makefile_has_target(makefile_text, target)
        )
        if missing_targets:
            fail(
                f"연습문제 Makefile target 누락: exercises/{name}: "
                + ", ".join(missing_targets)
            )
        if name not in aggregate:
            fail(f"exercises/Makefile이 연습문제를 열거하지 않습니다: {name}")

        readme_text = (root / "README.md").read_text(encoding="utf-8")
        headings, sections = markdown_h2_sections(readme_text)
        for heading in EXERCISE_PEDAGOGY_SECTIONS:
            if headings.count(heading) != 1:
                fail(
                    f"연습문제 README에 '## {heading}' 제목이 정확히 하나여야 합니다: "
                    f"exercises/{name}/README.md"
                )
        positions = [headings.index(heading) for heading in EXERCISE_PEDAGOGY_SECTIONS]
        if positions != sorted(positions):
            fail(
                "연습문제 README의 학습 마무리 순서는 "
                "'완료 기준 -> 자기 설명 -> 검증'이어야 합니다: "
                f"exercises/{name}/README.md"
            )

        completion_bullets = [
            line for line in sections["완료 기준"].splitlines()
            if line.startswith("- ")
        ]
        explanation_bullets = [
            line for line in sections["자기 설명"].splitlines()
            if line.startswith("- ")
        ]
        if len(completion_bullets) < 3:
            fail(
                "연습문제 완료 기준에는 관찰 가능한 확인 항목이 3개 이상 필요합니다: "
                f"exercises/{name}/README.md"
            )
        if len(explanation_bullets) < 2 or any(
            not line.rstrip().endswith("?") for line in explanation_bullets
        ):
            fail(
                "연습문제 자기 설명에는 물음표로 끝나는 질문이 2개 이상 필요합니다: "
                f"exercises/{name}/README.md"
            )

        normalized_completion = " ".join(sections["완료 기준"].split())
        normalized_explanation = " ".join(sections["자기 설명"].split())
        if normalized_completion in completion_owners:
            fail(
                "연습문제별 완료 기준이 서로 달라야 합니다: "
                f"exercises/{name}/README.md, "
                f"exercises/{completion_owners[normalized_completion]}/README.md"
            )
        if normalized_explanation in explanation_owners:
            fail(
                "연습문제별 자기 설명 질문이 서로 달라야 합니다: "
                f"exercises/{name}/README.md, "
                f"exercises/{explanation_owners[normalized_explanation]}/README.md"
            )
        completion_owners[normalized_completion] = name
        explanation_owners[normalized_explanation] = name

        for source in (root / "reference").rglob("*"):
            if not source.is_file() or source.suffix not in SOURCE_SUFFIXES:
                continue
            text = source.read_text(encoding="utf-8")
            if re.search(r"\bTODO\b|구현하세요", text):
                fail(f"기준 구현에 미완성 표식이 있습니다: {relative(source)}")


def check_executable_contract() -> None:
    if os.name != "posix":
        return
    required_executable = [ROOT / "prepare.sh", ROOT / "verify.sh"]
    required_executable.extend(
        path for base in (ROOT / "examples", ROOT / "exercises")
        for path in base.rglob("*.sh")
    )
    for path in required_executable:
        if path.exists() and not os.access(path, os.X_OK):
            fail(f"실행 권한이 없습니다: {relative(path)}")


def check_symlinks() -> None:
    for path in ROOT.rglob("*"):
        if not path.is_symlink():
            continue
        try:
            path.resolve().relative_to(ROOT.resolve())
        except ValueError:
            fail(f"저장소 밖을 가리키는 심볼릭 링크입니다: {relative(path)}")


def check_text_hygiene() -> None:
    for path in ROOT.rglob("*"):
        if not path.is_file() or ".git" in path.parts:
            continue
        if path.name != "Makefile" and path.suffix not in TEXT_SUFFIXES:
            continue
        data = path.read_bytes()
        if b"\x00" in data:
            fail(f"텍스트 파일에 NUL 바이트가 있습니다: {relative(path)}")
        if b"\r" in data:
            fail(f"CR 문자가 포함된 줄바꿈이 있습니다: {relative(path)}")
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError as error:
            fail(f"UTF-8이 아닌 텍스트 파일입니다: {relative(path)}: {error}")
        for line_number, line in enumerate(text.splitlines(), start=1):
            if line.rstrip(" \t") != line:
                fail(f"줄 끝 공백이 있습니다: {relative(path)}:{line_number}")


def check_clean_tree() -> None:
    for path in ROOT.rglob("*"):
        if ".git" in path.parts:
            continue
        if path.is_dir() and (path.name == "build" or path.name.endswith(".dSYM") or path.name == "__pycache__"):
            fail(f"빌드·캐시 디렉터리가 남았습니다: {relative(path)}")
        if not path.is_file():
            continue
        if path.suffix in ARTIFACT_SUFFIXES:
            fail(f"빌드 산출물이 남았습니다: {relative(path)}")
        if path.name in KNOWN_BINARIES or path.name == "a.out":
            fail(f"실행 산출물이 남았습니다: {relative(path)}")
        prefix = path.read_bytes()[:8]
        if prefix.startswith(b"\x7fELF") or prefix[:4] in {
            b"\xfe\xed\xfa\xce", b"\xce\xfa\xed\xfe",
            b"\xfe\xed\xfa\xcf", b"\xcf\xfa\xed\xfe",
            b"\xca\xfe\xba\xbe", b"\xbe\xba\xfe\xca",
        }:
            fail(f"컴파일된 실행 파일이 남았습니다: {relative(path)}")
        if path.name in {"core", "verify.log"} or path.name.startswith("core."):
            fail(f"검증 부산물이 남았습니다: {relative(path)}")


def main() -> None:
    parser = argparse.ArgumentParser(description="guide-c 저장소 구조 검사")
    parser.add_argument(
        "--clean",
        action="store_true",
        help="빌드·검증 산출물이 남지 않았는지도 검사합니다",
    )
    arguments = parser.parse_args()

    check_root_contract()
    check_docs()
    check_examples()
    check_exercises()
    check_executable_contract()
    check_symlinks()
    check_text_hygiene()
    if arguments.clean:
        check_clean_tree()

    print(
        "저장소 구조 검사 통과: "
        f"문서 {len(EXPECTED_DOCS)}개, 예제 {len(EXPECTED_EXAMPLES)}개, "
        f"연습문제 {len(EXPECTED_EXERCISES)}개"
    )


if __name__ == "__main__":
    main()
