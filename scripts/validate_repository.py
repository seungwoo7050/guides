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
    "fd-redirection",
    "process-group-forwarding",
    "readline-repl",
    "text-checks",
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
    "scripts/new-workspace.sh",
    "scripts/test-validator.py",
    "scripts/test_workspace.py",
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
    "exercise-sanitize",
    "reference-test",
    "reference-sanitize",
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
    "fd_redirection",
    "libtextkit.a",
    "process_group_forwarding",
    "repl",
    "textstat",
}

FORBIDDEN_ANSWER_NAMES = {"answer", "answers", "ref", "solution", "solutions"}

ORDERED_MAPPING_HEADER = (
    "| 순서 | 문서 | 관찰 예제 | 직접 수행 | 수정 위치 | 검증 | 완료 뒤 비교·다음 |"
)

IMPLEMENTATION_SCOPES = {
    **{
        f"exercise:{name}": {
            "root": Path("exercises") / name / "reference",
            "readme": Path("exercises") / name / "reference" / "README.md",
            "allowed": None,
        }
        for name in EXPECTED_EXERCISES
    },
    "example:fd-redirection": {
        "root": Path("examples/fd-redirection"),
        "readme": Path("examples/fd-redirection/README.md"),
        "allowed": {Path("examples/fd-redirection/src/fd_redirection.c")},
    },
    "example:process-group-forwarding": {
        "root": Path("examples/process-group-forwarding"),
        "readme": Path("examples/process-group-forwarding/README.md"),
        "allowed": {
            Path("examples/process-group-forwarding/src/process_group_forwarding.c")
        },
    },
    "example:readline-repl": {
        "root": Path("examples/readline-repl"),
        "readme": Path("examples/readline-repl/README.md"),
        "allowed": {Path("examples/readline-repl/src/repl.c")},
    },
    "example:text-checks": {
        "root": Path("examples/text-checks"),
        "readme": Path("examples/text-checks/README.md"),
        "allowed": {Path("examples/text-checks/tests/check.sh")},
    },
}

MARKER_PREFIX = "[" + "Implementation"
IMPLEMENTATION_MARKER = re.compile(
    re.escape(MARKER_PREFIX) +
    r" (?P<parent>0|[1-9]\d*)(?:-(?P<child>[1-9]\d*))?\]"
)


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


def ignored_learner_path(path: Path) -> bool:
    try:
        parts = path.relative_to(ROOT).parts
    except ValueError:
        return False
    for name in EXPECTED_EXERCISES:
        exercise_parts = (Path("exercises") / name).parts
        if parts[:len(exercise_parts)] != exercise_parts or len(parts) <= len(exercise_parts):
            continue
        learner_root = parts[len(exercise_parts)]
        return (
            learner_root == "workspace" or learner_root == ".workspace.lock" or
            learner_root.startswith(".workspace.tmp.")
        )
    return False


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

    if ORDERED_MAPPING_HEADER not in readme:
        fail("README.md에 canonical ordered mapping 열이 없습니다")
    for path_text in sorted(EXPECTED_DOCS):
        if path_text not in readme:
            fail(f"README.md 학습 순서에서 문서를 찾을 수 없습니다: {path_text}")
    for name in sorted(EXPECTED_EXERCISES):
        path_text = f"exercises/{name}/README.md"
        if path_text not in readme:
            fail(f"README.md 학습 순서에서 연습문제를 찾을 수 없습니다: {path_text}")
    for name in sorted(EXPECTED_EXAMPLES):
        path_text = f"examples/{name}/README.md"
        if path_text not in readme:
            fail(f"README.md 학습 순서에서 예제를 찾을 수 없습니다: {path_text}")
    for required_text in (
        "scripts/new-workspace.sh",
        "workspace/",
        "reference/README.md",
        "완료한 뒤",
    ):
        if required_text not in readme:
            fail(f"README.md에 학습 흐름 계약이 없습니다: {required_text}")


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
        require_path(f"examples/{name}/README.md")
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
        if makefile.parent == exercises or ignored_learner_path(makefile):
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
        for required in (
            "README.md", "Makefile", "skeleton", "reference", "reference/README.md", "tests"
        ):
            if not (root / required).exists():
                fail(f"연습문제 구성요소가 없습니다: exercises/{name}/{required}")
        if not any(path.is_file() for path in (root / "skeleton").rglob("*")):
            fail(f"skeleton이 비어 있습니다: exercises/{name}")
        if not any(path.is_file() for path in (root / "reference").rglob("*")):
            fail(f"reference가 비어 있습니다: exercises/{name}")
        if not any(path.is_file() for path in (root / "tests").rglob("*")):
            fail(f"tests가 비어 있습니다: exercises/{name}")

        for directory in root.rglob("*"):
            if ignored_learner_path(directory):
                continue
            if directory.is_dir() and directory.name in FORBIDDEN_ANSWER_NAMES:
                fail(
                    "reference/ 외의 기준 답안 별칭을 허용하지 않습니다: "
                    f"{relative(directory)}"
                )

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


def implementation_scope_for_path(path: Path) -> str | None:
    relative_path = path.relative_to(ROOT)
    for name, contract in IMPLEMENTATION_SCOPES.items():
        allowed = contract["allowed"]
        if allowed is not None:
            if relative_path in allowed:
                return name
            continue
        scope_root = contract["root"]
        if relative_path.is_relative_to(scope_root) and (
            path.suffix in SOURCE_SUFFIXES or path.name == "Makefile"
        ):
            return name
    return None


def marker_sort_key(label: str) -> tuple[int, int]:
    parent, separator, child = label.partition("-")
    return int(parent), int(child) if separator else 0


def check_implementation_annotations() -> None:
    markers_by_scope: dict[str, list[tuple[str, Path]]] = {
        name: [] for name in IMPLEMENTATION_SCOPES
    }

    for path in ROOT.rglob("*"):
        if not path.is_file() or ".git" in path.parts or ignored_learner_path(path):
            continue
        if "build" in path.parts or "__pycache__" in path.parts:
            continue
        data = path.read_bytes()
        if MARKER_PREFIX.encode() not in data:
            continue
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError:
            fail(f"binary·generated 파일에 Implementation 표식이 있습니다: {relative(path)}")
        scope = implementation_scope_for_path(path)
        if scope is None:
            fail(f"Implementation 표식이 허용되지 않는 위치입니다: {relative(path)}")

        starts = [
            match.start() for match in re.finditer(re.escape(MARKER_PREFIX), text)
        ]
        for start in starts:
            match = IMPLEMENTATION_MARKER.match(text, start)
            if match is None:
                fail(f"형식이 잘못된 Implementation 표식입니다: {relative(path)}")
            parent = match.group("parent")
            child = match.group("child")
            if parent == "0" and child is not None:
                fail(f"Implementation 0에는 하위 번호를 붙일 수 없습니다: {relative(path)}")
            label = parent if child is None else f"{parent}-{child}"
            markers_by_scope[scope].append((label, path))

    for scope, markers in markers_by_scope.items():
        if not markers:
            fail(f"완성 구현 scope에 Implementation 표식이 없습니다: {scope}")
        labels = [label for label, _ in markers]
        if len(labels) != len(set(labels)):
            duplicate = next(label for label in labels if labels.count(label) > 1)
            fail(f"한 scope에서 Implementation 표식이 중복됩니다: {scope}: {duplicate}")

        top_numbers = sorted(
            int(label) for label in labels if "-" not in label and label != "0"
        )
        if not top_numbers or top_numbers != list(range(1, max(top_numbers) + 1)):
            fail(f"Implementation 상위 번호는 1부터 연속이어야 합니다: {scope}")

        top_set = {str(number) for number in top_numbers}
        children: dict[str, list[int]] = {}
        for label in labels:
            if "-" not in label:
                continue
            parent, child = label.split("-", 1)
            if parent not in top_set:
                fail(f"부모 없는 Implementation 하위 번호입니다: {scope}: {label}")
            children.setdefault(parent, []).append(int(child))
        for parent, values in children.items():
            ordered = sorted(values)
            if ordered != list(range(1, max(ordered) + 1)):
                fail(f"Implementation 하위 번호는 1부터 연속이어야 합니다: {scope}: {parent}")

        readme_path = ROOT / IMPLEMENTATION_SCOPES[scope]["readme"]
        text = readme_path.read_text(encoding="utf-8")
        headings, sections = markdown_h2_sections(text)
        if headings.count("구현 순서") != 1:
            fail(f"scope README에 '## 구현 순서'가 정확히 하나여야 합니다: {relative(readme_path)}")
        indexed_labels = re.findall(
            r"(?m)^\|\s*`((?:0|[1-9]\d*)(?:-[1-9]\d*)?)`\s*\|",
            sections["구현 순서"],
        )
        expected_labels = sorted(labels, key=marker_sort_key)
        if indexed_labels != expected_labels:
            fail(
                "scope README index와 source 표식이 일치하지 않습니다: "
                f"{relative(readme_path)}: index={indexed_labels}, source={expected_labels}"
            )


def check_executable_contract() -> None:
    if os.name != "posix":
        return
    required_executable = [
        ROOT / "prepare.sh",
        ROOT / "verify.sh",
        ROOT / "scripts/new-workspace.sh",
    ]
    required_executable.extend(
        path for base in (ROOT / "examples", ROOT / "exercises")
        for path in base.rglob("*.sh")
        if not ignored_learner_path(path)
    )
    for path in required_executable:
        if path.exists() and not os.access(path, os.X_OK):
            fail(f"실행 권한이 없습니다: {relative(path)}")


def check_symlinks() -> None:
    for path in ROOT.rglob("*"):
        if ignored_learner_path(path):
            continue
        if not path.is_symlink():
            continue
        try:
            path.resolve().relative_to(ROOT.resolve())
        except ValueError:
            fail(f"저장소 밖을 가리키는 심볼릭 링크입니다: {relative(path)}")


def check_text_hygiene() -> None:
    for path in ROOT.rglob("*"):
        if not path.is_file() or ".git" in path.parts or ignored_learner_path(path):
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
        if ".git" in path.parts or ignored_learner_path(path):
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
    check_implementation_annotations()
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
