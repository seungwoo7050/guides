#!/usr/bin/env python3
"""Validate the guide-cpp repository structure and documentation contracts."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from urllib.parse import unquote, urlsplit

from validate_annotations import validate_repository_contracts

ROOT = Path(__file__).resolve().parents[1]

REQUIRED_ROOT = [
    ".gitignore",
    "README.md",
    "CONTRIBUTING.md",
    "LICENSE.md",
    "LICENSES",
    "LICENSES/CC-BY-4.0.txt",
    "LICENSES/MIT.txt",
    "Makefile",
    "prepare.sh",
    "verify.sh",
    "docs",
    "exercises",
    "scripts",
    "scripts/manage_artifacts.py",
    "scripts/new_workspace.py",
    "scripts/run_with_timeout.py",
    "scripts/validate_annotations.py",
    "scripts/validate_docs.py",
    "scripts/verify_modern_skeletons.py",
    "scripts/selftest_verifiers.py",
    "exercises/01-modern-cpp/README.md",
    "exercises/02-cpp98-systems/README.md",
]

REQUIRED_DOCUMENTS = [
    "docs/00-roadmap.md",
    "docs/01-modern-cpp/01-program-build-cmake.md",
    "docs/01-modern-cpp/02-values-lifetimes-and-move.md",
    "docs/01-modern-cpp/03-raii-smart-pointers-and-rule-of-zero.md",
    "docs/01-modern-cpp/04-classes-responsibilities-and-polymorphism.md",
    "docs/01-modern-cpp/05-errors-optional-variant-and-expected.md",
    "docs/01-modern-cpp/06-algorithms-ranges-templates-and-concepts.md",
    "docs/01-modern-cpp/07-concurrency-time-and-filesystem.md",
    "docs/01-modern-cpp/08-testing-debugging-and-tooling.md",
    "docs/01-modern-cpp/09-application-capstone.md",
    "docs/02-cpp98-systems/00-roadmap.md",
    "docs/02-cpp98-systems/01-program-and-type-model.md",
    "docs/02-cpp98-systems/02-lifetime-value-and-ownership.md",
    "docs/02-cpp98-systems/03-assigning-object-responsibilities.md",
    "docs/02-cpp98-systems/04-inheritance-and-polymorphism.md",
    "docs/02-cpp98-systems/05-errors-validation-and-casts.md",
    "docs/02-cpp98-systems/06-templates-iterators-and-stl.md",
    "docs/02-cpp98-systems/07-solving-problems-with-stl.md",
    "docs/02-cpp98-systems/08-posix-sockets-and-event-loop.md",
    "docs/02-cpp98-systems/09-object-oriented-http-server.md",
    "docs/90-appendix/01-modern-to-cpp98-crosswalk.md",
    "docs/90-appendix/02-compiler-platform-notes.md",
    "docs/90-appendix/03-cpp98-build-and-compatibility.md",
    "docs/90-appendix/04-stl-internals.md",
]

MODERN_EXERCISES = [
    "exercises/01-modern-cpp/01-strong-types-and-cmake",
    "exercises/01-modern-cpp/02-unique-file",
    "exercises/01-modern-cpp/03-query-pipeline",
    "exercises/01-modern-cpp/04-local-job-runner",
]

CPP98_EXERCISES = [
    "exercises/02-cpp98-systems/object-model/command-service/01-procedural",
    "exercises/02-cpp98-systems/object-model/command-service/02-value-ownership",
    "exercises/02-cpp98-systems/object-model/command-service/03-responsibilities",
    "exercises/02-cpp98-systems/object-model/command-service/04-polymorphism",
    "exercises/02-cpp98-systems/object-model/command-service/05-errors",
    "exercises/02-cpp98-systems/generic-programming/template-array",
    "exercises/02-cpp98-systems/generic-programming/mini-vector",
    "exercises/02-cpp98-systems/generic-programming/stl-problems",
    "exercises/02-cpp98-systems/networking/line-server",
    "exercises/02-cpp98-systems/networking/http-server",
    "exercises/02-cpp98-systems/networking/http-server/01-parser",
    "exercises/02-cpp98-systems/networking/http-server/02-config-router",
    "exercises/02-cpp98-systems/networking/http-server/03-nonblocking-server",
    "exercises/02-cpp98-systems/networking/http-server/04-cgi-process",
    "exercises/02-cpp98-systems/networking/http-server/05-integrated-server",
]

OBSOLETE_PATHS = [
    "before-verify.sh",
    "make-out.txt",
    "tree.txt",
    "docs/01-program-and-type-model.md",
    "docs/02-lifetime-value-and-ownership.md",
    "docs/03-assigning-object-responsibilities.md",
    "docs/04-inheritance-and-polymorphism.md",
    "docs/05-errors-validation-and-casts.md",
    "docs/06-templates-iterators-and-stl.md",
    "docs/07-solving-problems-with-stl.md",
    "docs/08-posix-sockets-and-event-loop.md",
    "docs/09-object-oriented-http-server.md",
    "exercises/object-model",
    "exercises/generic-programming",
    "exercises/networking",
    "reference",
]

STALE_LITERALS = [
    "docs/01-program-and-type-model.md",
    "docs/02-lifetime-value-and-ownership.md",
    "docs/03-assigning-object-responsibilities.md",
    "docs/04-inheritance-and-polymorphism.md",
    "docs/05-errors-validation-and-casts.md",
    "docs/06-templates-iterators-and-stl.md",
    "docs/07-solving-problems-with-stl.md",
    "docs/08-posix-sockets-and-event-loop.md",
    "docs/09-object-oriented-http-server.md",
    "exercises/object-model",
    "exercises/generic-programming",
    "exercises/networking",
    "reference/cpp98-compatibility.md",
    "reference/stl-internals.md",
]

MODERN_REQUIRED_SECTIONS = {
    "## 목표",
    "## 시작하기 전에",
    "## 연결 실습",
    "## 완료 기준",
}

TEXT_SUFFIXES = {".md", ".py", ".sh", ".txt", ".json", ".cmake", ".yml", ".yaml"}
LINK_PATTERN = re.compile(r"!?\[[^\]]*\]\(([^)]+)\)")
FENCE_PATTERN = re.compile(r"^\s{0,3}(`{3,}|~{3,})(.*)$")
SCHEME_PATTERN = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*:")
PRUNED_DIRECTORY_NAMES = {".git", ".guide-probes", ".pytest_cache", ".workspace", "__pycache__", "build"}


def rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def text_file(path: Path) -> bool:
    return path.name in {"Makefile", "CMakeLists.txt"} or path.suffix.lower() in TEXT_SUFFIXES


def repository_files(root: Path, *, suffix: str | None = None):
    """Yield files without entering generated data or learner workspaces."""

    for current_text, directory_names, file_names in os.walk(
        root, topdown=True, followlinks=False
    ):
        current = Path(current_text)
        directory_names[:] = [
            name
            for name in directory_names
            if name not in PRUNED_DIRECTORY_NAMES
            and not name.startswith("build-")
            and not name.endswith(".dSYM")
            and not (current / name).is_symlink()
        ]
        for name in file_names:
            path = current / name
            if path.is_symlink() or (suffix is not None and path.suffix.lower() != suffix):
                continue
            yield path


def skeleton_tests_outside_learner_guard(content: str) -> bool:
    """Return true when add_test registers a skeleton outside its opt-in guard."""

    guarded_depth = 0
    lines = content.splitlines()
    index = 0
    while index < len(lines):
        stripped = lines[index].strip()
        if re.match(r"if\s*\(\s*GUIDE_TEST_SKELETONS\s*\)", stripped, re.IGNORECASE):
            guarded_depth += 1
        elif guarded_depth and re.match(r"endif\s*\(", stripped, re.IGNORECASE):
            guarded_depth -= 1

        if re.match(r"add_test\s*\(", stripped, re.IGNORECASE):
            block = [stripped]
            balance = stripped.count("(") - stripped.count(")")
            while balance > 0 and index + 1 < len(lines):
                index += 1
                block.append(lines[index])
                balance += lines[index].count("(") - lines[index].count(")")
            if "skeleton" in "\n".join(block).lower() and guarded_depth == 0:
                return True
        index += 1
    return False


def visible_lines(text: str, path: Path, errors: list[str]) -> list[str]:
    visible: list[str] = []
    marker: str | None = None
    marker_length = 0

    for number, line in enumerate(text.splitlines(), start=1):
        match = FENCE_PATTERN.match(line)
        if match:
            token = match.group(1)
            if marker is None:
                marker = token[0]
                marker_length = len(token)
            elif token[0] == marker and len(token) >= marker_length:
                marker = None
                marker_length = 0
            continue
        if marker is None:
            visible.append(line)

    if marker is not None:
        errors.append(f"닫히지 않은 Markdown code fence: {rel(path)}")
    return visible


def parse_link_target(raw: str) -> str:
    raw = raw.strip()
    if not raw:
        return ""
    if raw.startswith("<"):
        closing = raw.find(">")
        if closing != -1:
            return raw[1:closing]
    # Markdown titles follow the destination after whitespace. Paths that
    # contain spaces should use <...> or URL escaping.
    return raw.split(None, 1)[0]


def validate_link(source: Path, raw: str, errors: list[str]) -> None:
    target = unquote(parse_link_target(raw))
    if not target or target.startswith("#") or SCHEME_PATTERN.match(target):
        return

    parts = urlsplit(target)
    path_text = parts.path
    if not path_text:
        return

    if path_text.startswith("/"):
        resolved = ROOT / path_text.lstrip("/")
    else:
        resolved = source.parent / path_text

    try:
        resolved = resolved.resolve()
        resolved.relative_to(ROOT.resolve())
    except ValueError:
        errors.append(f"저장소 밖을 가리키는 상대 링크: {rel(source)} -> {target}")
        return

    if not resolved.exists():
        errors.append(f"상대 링크 대상이 없음: {rel(source)} -> {target}")


def validate_markdown(path: Path, errors: list[str]) -> None:
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        errors.append(f"UTF-8로 읽을 수 없는 Markdown: {rel(path)}")
        return

    if not text.strip():
        errors.append(f"비어 있는 Markdown: {rel(path)}")
        return

    visible = visible_lines(text, path, errors)
    h1_count = sum(1 for line in visible if re.match(r"^#\s+\S", line))
    if h1_count != 1:
        errors.append(f"H1 제목은 정확히 하나여야 함: {rel(path)} ({h1_count}개)")

    visible_text = "\n".join(visible)
    for match in LINK_PATTERN.finditer(visible_text):
        validate_link(path, match.group(1), errors)


def validate_structure(errors: list[str]) -> None:
    for item in REQUIRED_ROOT:
        if not (ROOT / item).exists():
            errors.append(f"필수 루트 경로 누락: {item}")

    for item in REQUIRED_DOCUMENTS:
        if not (ROOT / item).is_file():
            errors.append(f"필수 문서 누락: {item}")

    for item in OBSOLETE_PATHS:
        if (ROOT / item).exists():
            errors.append(f"이전 구조 경로가 남아 있음: {item}")

    workspace = ROOT / ".workspace"
    if workspace.is_symlink():
        errors.append("learner workspace root가 symlink임: .workspace")
    elif workspace.exists() and not workspace.is_dir():
        errors.append("learner workspace root가 directory가 아님: .workspace")

    executable_scripts = [
        ROOT / "prepare.sh",
        ROOT / "verify.sh",
        ROOT / "scripts/new_workspace.py",
        ROOT / "scripts/validate_annotations.py",
    ]
    executable_scripts.extend(repository_files(ROOT, suffix=".sh"))
    for script in sorted(set(executable_scripts), key=lambda value: value.as_posix()):
        if script.is_file() and not script.stat().st_mode & 0o111:
            errors.append(f"실행 스크립트에 실행 권한이 없음: {rel(script)}")

    for exercise_text in MODERN_EXERCISES:
        exercise = ROOT / exercise_text
        required = [
            exercise / "README.md",
            exercise / "CMakeLists.txt",
            exercise / "skeleton",
            exercise / "reference",
            exercise / "tests",
        ]
        for item in required:
            if not item.exists():
                errors.append(f"Modern C++ 실습 구성 누락: {rel(item)}")

        for subtree in ("include", "src"):
            skeleton_root = exercise / "skeleton" / subtree
            reference_root = exercise / "reference" / subtree
            skeleton_files = {
                path.relative_to(skeleton_root).as_posix()
                for path in skeleton_root.rglob("*")
                if path.is_file()
            } if skeleton_root.is_dir() else set()
            reference_files = {
                path.relative_to(reference_root).as_posix()
                for path in reference_root.rglob("*")
                if path.is_file()
            } if reference_root.is_dir() else set()
            if skeleton_files != reference_files:
                errors.append(
                    f"skeleton/reference 파일 경계 불일치: {exercise_text}/{subtree} "
                    f"(skeleton-only={sorted(skeleton_files-reference_files)}, "
                    f"reference-only={sorted(reference_files-skeleton_files)})"
                )

        cmake = exercise / "CMakeLists.txt"
        if cmake.is_file():
            content = cmake.read_text(encoding="utf-8")
            if "skeleton" not in content or "reference" not in content:
                errors.append(f"skeleton/reference target이 모두 연결되지 않음: {rel(cmake)}")
            if skeleton_tests_outside_learner_guard(content):
                errors.append(f"미완성 skeleton이 CTest 정상 suite에 등록됨: {rel(cmake)}")

    for exercise_text in CPP98_EXERCISES:
        exercise = ROOT / exercise_text
        if not exercise.is_dir():
            errors.append(f"C++98 실습 경로 누락: {exercise_text}")
        elif not (exercise / "Makefile").is_file():
            errors.append(f"C++98 실습 Makefile 누락: {exercise_text}/Makefile")

    network_test_contracts = {
        "exercises/02-cpp98-systems/networking/line-server/tests.py": [
            "read_startup_line",
            "select.select",
            "/proc/{pid}/fd",
            'shutil.which("lsof")',
            "time.monotonic",
        ],
        "exercises/02-cpp98-systems/networking/http-server/03-nonblocking-server/tests.py": [
            "read_startup_line",
            "select.select",
            "Content-Length",
        ],
        "exercises/02-cpp98-systems/networking/http-server/05-integrated-server/tests.py": [
            "read_startup_line",
            "select.select",
            "Content-Length",
        ],
    }
    for path_text, required_literals in network_test_contracts.items():
        path = ROOT / path_text
        if not path.is_file():
            errors.append(f"네트워크 검증 파일 누락: {path_text}")
            continue
        content = path.read_text(encoding="utf-8")
        for literal in required_literals:
            if literal not in content:
                errors.append(f"네트워크 검증 계약 누락: {path_text} -> {literal}")

    preset = ROOT / "exercises/01-modern-cpp/CMakePresets.json"
    if not preset.is_file():
        errors.append("Modern C++ CMakePresets.json 누락")
    else:
        try:
            data = json.loads(preset.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError) as error:
            errors.append(f"CMakePresets.json 파싱 실패: {error}")
        else:
            configure_names = {item.get("name") for item in data.get("configurePresets", [])}
            required_presets = {"debug", "release", "sanitize", "thread-sanitize"}
            missing = required_presets - configure_names
            if missing:
                errors.append(f"Modern C++ configure preset 누락: {sorted(missing)}")

    top_cmake = ROOT / "exercises/01-modern-cpp/CMakeLists.txt"
    if top_cmake.is_file():
        content = top_cmake.read_text(encoding="utf-8")
        required_literals = [
            "cxx_std_20",
            "modern_skeletons",
            "modern_references",
            "GUIDE_TEST_SKELETONS",
            "GUIDE_ENABLE_SANITIZERS",
            "GUIDE_ENABLE_THREAD_SANITIZER",
        ]
        for literal in required_literals:
            if literal not in content:
                errors.append(f"Modern C++ 최상위 CMake 계약 누락: {literal}")

    root_makefile = ROOT / "Makefile"
    if root_makefile.is_file():
        content = root_makefile.read_text(encoding="utf-8")
        required_targets = [
            "docs-check:",
            "workspace:",
            "modern-start-state:",
            "modern-test:",
            "modern-release:",
            "modern-sanitize:",
            "modern-thread-sanitize:",
            "modern-exercise-test:",
            "cpp98-exercise-test:",
            "skeleton-build:",
            "test:",
            "failure-check:",
            "sanitize:",
            "clean:",
        ]
        for target in required_targets:
            if target not in content:
                errors.append(f"루트 Makefile target 누락: {target[:-1]}")
        negative_contracts = [
            "fail-copy",
            "fail-nonvirtual",
            "fail-commit",
            "compile-fail",
            "leak-check",
            "failure-test",
        ]
        for literal in negative_contracts:
            if literal not in content:
                errors.append(f"C++98 실패 계약 검증 누락: {literal}")


def validate_content(errors: list[str]) -> None:
    markdown_files = list(repository_files(ROOT, suffix=".md"))
    for path in markdown_files:
        validate_markdown(path, errors)

    for path in (ROOT / "docs/01-modern-cpp").glob("*.md"):
        text = path.read_text(encoding="utf-8")
        headings = {
            line.strip()
            for line in visible_lines(text, path, errors)
            if line.startswith("## ")
        }
        missing = sorted(MODERN_REQUIRED_SECTIONS - headings)
        if missing:
            errors.append(f"Modern C++ 공통 절 누락: {rel(path)} -> {', '.join(missing)}")

    for exercise_text in MODERN_EXERCISES:
        exercise = ROOT / exercise_text
        skeleton_sources = [
            path
            for path in (exercise / "skeleton").rglob("*")
            if path.is_file() and path.suffix in {".hpp", ".cpp"}
        ]
        reference_sources = [
            path
            for path in (exercise / "reference").rglob("*")
            if path.is_file() and path.suffix in {".hpp", ".cpp"}
        ]
        tests = [
            path
            for path in (exercise / "tests").rglob("*")
            if path.is_file() and path.suffix in {".hpp", ".cpp"}
        ]
        if not skeleton_sources or not reference_sources or not tests:
            errors.append(f"Modern C++ 구현 또는 테스트 소스 누락: {exercise_text}")
            continue
        if not any("TODO:" in path.read_text(encoding="utf-8") for path in skeleton_sources):
            errors.append(f"학습 계약 TODO가 없는 skeleton: {exercise_text}")
        for path in reference_sources + tests:
            if "TODO:" in path.read_text(encoding="utf-8"):
                errors.append(f"reference/test에 TODO가 남아 있음: {rel(path)}")

    # Migration literals are intentionally present in prepare.sh only.
    scan_roots = [
        ROOT / "README.md",
        ROOT / "CONTRIBUTING.md",
        ROOT / "Makefile",
        ROOT / "docs",
        ROOT / "exercises",
    ]
    for scan_root in scan_roots:
        paths = [scan_root] if scan_root.is_file() else list(scan_root.rglob("*"))
        for path in paths:
            if not path.is_file() or not text_file(path):
                continue
            try:
                text = path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                continue
            for literal in STALE_LITERALS:
                if literal in text:
                    errors.append(f"이동 전 경로 문자열이 남아 있음: {rel(path)} -> {literal}")

    for path_text in ("README.md", "docs/00-roadmap.md", "CONTRIBUTING.md"):
        path = ROOT / path_text
        if path.is_file():
            text = path.read_text(encoding="utf-8")
            for command in ("./prepare.sh", "./verify.sh"):
                if command not in text:
                    errors.append(f"정본 루트 명령이 문서에 없음: {path_text} -> {command}")

    errors.extend(validate_repository_contracts(ROOT))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("structure", "full"), default="full")
    args = parser.parse_args()

    errors: list[str] = []
    validate_structure(errors)
    if args.mode == "full":
        validate_content(errors)

    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1

    if args.mode == "structure":
        print("저장소 구조 검사: PASS")
    else:
        markdown_count = sum(1 for _ in repository_files(ROOT, suffix=".md"))
        print(
            f"문서·구조 검사: 필수 문서 {len(REQUIRED_DOCUMENTS)}개, "
            f"Modern 실습 {len(MODERN_EXERCISES)}개, "
            f"C++98 실습 경로 {len(CPP98_EXERCISES)}개, Markdown {markdown_count}개"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
