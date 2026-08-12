#!/usr/bin/env python3
"""Validate the final guide layout and its teaching contracts."""

from __future__ import annotations

import io
import json
import os
import re
import stat
import subprocess
import sys
import tokenize
import tomllib
import unicodedata
from collections import Counter
from pathlib import Path
from urllib.parse import unquote


ROOT = Path(os.environ.get("GUIDE_ROOT", Path(__file__).resolve().parents[1])).resolve()


def identify() -> str:
    if (ROOT / "exercises/command-checker").is_dir():
        return "python"
    if (ROOT / "exercises/system-investigation").is_dir():
        return "unix-systems"
    if (ROOT / "exercises/setup.sh").is_file():
        return "git"
    raise ValueError("지원하는 가이드 구조를 식별할 수 없습니다.")


GUIDE = identify()
CONFIG = {
    "git": {
        "docs": {
            "docs/00-roadmap.md", "docs/01-workspace-basics.md",
            "docs/02-commit-workflow.md", "docs/03-remote-pr-workflow.md",
            "docs/04-merge-rebase-conflicts.md", "docs/05-recovery-runbook.md",
            "docs/90-open-source-contribution.md",
        },
        "concepts": {
            "docs/01-workspace-basics.md", "docs/02-commit-workflow.md",
            "docs/03-remote-pr-workflow.md", "docs/04-merge-rebase-conflicts.md",
            "docs/05-recovery-runbook.md", "docs/90-open-source-contribution.md",
        },
        "exercise": "exercises/README.md",
        "required": {
            "README.md", "CONTRIBUTING.md", "Makefile", "prepare.sh", "verify.sh",
            "scripts/repository_state.py", "scripts/validate.py",
            "scripts/test-validator.py", "scripts/validate.sh", "scripts/layout-manifest.txt",
            "scripts/test-verify-negatives.sh",
            "exercises/setup.sh",
        },
        "forbidden": {"docs/06-open-source-contribution.md", "git/exercises/workspace"},
        "executables": {"prepare.sh", "verify.sh", "scripts/validate.py",
                        "scripts/test-validator.py", "scripts/validate.sh", "exercises/setup.sh"},
    },
    "python": {
        "docs": {
            "docs/00-roadmap.md",
            "docs/01-language-and-runtime/01-runtime-and-environment.md",
            "docs/01-language-and-runtime/02-objects-and-collections.md",
            "docs/01-language-and-runtime/03-functions-errors-and-types.md",
            "docs/01-language-and-runtime/04-iterators-generators-and-context-managers.md",
            "docs/02-automation/01-files-structured-data-and-cli.md",
            "docs/02-automation/02-subprocess-and-process-lifecycle.md",
            "docs/02-automation/03-concurrency-and-cancellation.md",
            "docs/03-quality/01-testing.md",
            "docs/03-quality/02-project-structure-packaging-and-typing.md",
            "docs/03-quality/03-cli-test-runner.md",
        },
        "concepts": set(),
        "exercise": "exercises/command-checker/README.md",
        "required": {
            "README.md", "CONTRIBUTING.md", "Makefile", "prepare.sh", "verify.sh",
            "scripts/repository_state.py", "scripts/validate.py", "scripts/test-validator.py",
            "scripts/test-prepare-safety.sh", "scripts/layout-manifest.txt",
            "scripts/test-verify-negatives.sh",
            "scripts/check_docs.py", "scripts/check_test_quality.py",
            "scripts/check_package_install.py", "scripts/check_stage_contracts.py",
            "scripts/check_type_contracts.py", "scripts/new-workspace.sh",
            "exercises/command-checker/reference/_command_checker_build.py",
            "exercises/command-checker/reference/pyproject.toml",
            "exercises/command-checker/reference/command_checker/py.typed",
            "exercises/command-checker/skeleton/_command_checker_build.py",
            "exercises/command-checker/skeleton/pyproject.toml",
            "exercises/command-checker/skeleton/command_checker/py.typed",
        },
        "forbidden": {
            "docs/01-runtime-and-environment.md", "docs/02-objects-and-collections.md",
            "docs/03-functions-errors-and-types.md", "docs/04-files-and-cli.md",
            "docs/05-subprocess-and-automation.md", "docs/06-testing.md",
            "docs/07-cli-test-runner.md", "docs/08-algorithms-and-project-quality.md",
            "exercises/command-checker/tests/test_stage_07_reports.py",
        },
        "executables": {"prepare.sh", "verify.sh", "scripts/validate.py",
                        "scripts/test-prepare-safety.sh", "scripts/test-validator.py",
                        "scripts/check_docs.py",
                        "scripts/test-verify-negatives.sh",
                        "scripts/check_package_install.py", "scripts/check_test_quality.py",
                        "scripts/check_type_contracts.py", "scripts/check_stage_contracts.py",
                        "scripts/new-workspace.sh"},
    },
    "unix-systems": {
        "docs": {
            "docs/00-roadmap.md",
            "docs/01-user-space-model/01-terminal-process-and-kernel.md",
            "docs/01-user-space-model/02-files-paths-and-metadata.md",
            "docs/01-user-space-model/03-streams-file-descriptors-and-pipes.md",
            "docs/01-user-space-model/04-users-permissions-and-environment.md",
            "docs/02-process-and-resource-observation/01-processes-signals-and-jobs.md",
            "docs/02-process-and-resource-observation/02-process-memory-observation.md",
            "docs/02-process-and-resource-observation/03-network-endpoints-and-diagnosis.md",
            "docs/03-services-and-troubleshooting/01-service-supervision-logs-and-readiness.md",
            "docs/03-services-and-troubleshooting/02-system-troubleshooting.md",
        },
        "concepts": set(),
        "exercise": "exercises/system-investigation/README.md",
        "required": {
            "README.md", "CONTRIBUTING.md", "Makefile", "prepare.sh", "verify.sh",
            "scripts/repository_state.py", "scripts/validate.py", "scripts/test-validator.py",
            "scripts/layout-manifest.txt",
            "scripts/test_answer_mutants.py", "exercises/system-investigation/check.sh",
            "exercises/system-investigation/check_answers.py",
            "exercises/system-investigation/create-workspace.sh",
            "exercises/system-investigation/lab.py",
        },
        "forbidden": {"exercises/system-probe"},
        "executables": {"prepare.sh", "verify.sh", "scripts/validate.py",
                        "scripts/test-validator.py", "scripts/test_answer_mutants.py",
                        "exercises/system-investigation/check.sh",
                        "exercises/system-investigation/check_answers.py",
                        "exercises/system-investigation/create-workspace.sh",
                        "exercises/system-investigation/lab.py"},
    },
}[GUIDE]
if not CONFIG["concepts"]:
    CONFIG["concepts"] = CONFIG["docs"] - {"docs/00-roadmap.md"}

errors: list[str] = []


def error(message: str) -> None:
    errors.append(message)


def section(text: str, heading: str) -> str:
    match = re.search(rf"^## {re.escape(heading)}\n(.*?)(?=^## |\Z)", text, re.M | re.S)
    return match.group(1).strip() if match else ""


IMPLEMENTATION_CANDIDATE = re.compile(r"\[Implementation[^\]\n]*\]")
IMPLEMENTATION_EXACT = re.compile(r"\[Implementation (0|[1-9]\d*(?:-[1-9]\d*)?)\]")


def implementation_sort_key(identifier: str) -> tuple[int, int]:
    parts = identifier.split("-", 1)
    return int(parts[0]), int(parts[1]) if len(parts) == 2 else 0


def validate_implementation_annotations() -> None:
    reference = ROOT / "exercises/command-checker/reference"
    exercise_readme = ROOT / "exercises/command-checker/README.md"
    ignored = {".git", ".guide", ".venv", ".pytest_cache", "__pycache__", "workspace"}
    occurrences: list[tuple[str, Path, int, str]] = []

    def inspect_line(path: Path, number: int, line: str, *, comment: bool) -> None:
        if "[Implementation" not in line:
            return
        candidates = list(IMPLEMENTATION_CANDIDATE.finditer(line))
        if not candidates:
            error(f"Implementation annotation 형식 오류: {path.relative_to(ROOT)}:{number}")
            return
        for candidate in candidates:
            exact = IMPLEMENTATION_EXACT.fullmatch(candidate.group(0))
            if exact is None:
                error(f"Implementation annotation 형식 오류: {path.relative_to(ROOT)}:{number}")
                continue
            identifier = exact.group(1)
            if identifier == "0":
                error("command-checker에는 Implementation 0 대상이 없습니다.")
            allowed_source = path.is_relative_to(reference) and (
                path.suffix == ".py" or path == reference / "pyproject.toml"
            )
            allowed_sidecar = path == exercise_readme
            if not allowed_source and not allowed_sidecar:
                error(f"Implementation annotation 금지 경로: {path.relative_to(ROOT)}:{number}")
            if allowed_source and not comment:
                error(f"Implementation annotation은 comment여야 합니다: {path.relative_to(ROOT)}:{number}")
            if allowed_sidecar and identifier != "10-6":
                error(f"README sidecar는 10-6만 소유합니다: {path.relative_to(ROOT)}:{number}")
            if not re.search(r"[가-힣]", line):
                error(f"Implementation annotation 설명 누락: {path.relative_to(ROOT)}:{number}")
            occurrences.append((identifier, path, number, line))

    for path in sorted(ROOT.rglob("*")):
        relative = path.relative_to(ROOT)
        if not path.is_file() or any(part in ignored for part in relative.parts):
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        if path.suffix == ".py":
            try:
                tokens = tokenize.generate_tokens(io.StringIO(text).readline)
                for token in tokens:
                    if token.type == tokenize.COMMENT:
                        inspect_line(path, token.start[0], token.string, comment=True)
            except (IndentationError, tokenize.TokenError) as exc:
                error(f"Python token 검사 실패: {relative}: {exc}")
        else:
            for number, line in enumerate(text.splitlines(), 1):
                inspect_line(path, number, line, comment=line.lstrip().startswith("#"))

    counts = Counter(identifier for identifier, _, _, _ in occurrences)
    for identifier, count in sorted(counts.items(), key=lambda item: implementation_sort_key(item[0])):
        if count != 1:
            error(f"Implementation annotation 중복: {identifier}: {count}개")
    if not counts:
        error("Implementation annotation이 없습니다.")
        return

    top_level = {int(identifier) for identifier in counts if "-" not in identifier and identifier != "0"}
    if top_level != set(range(1, max(top_level, default=0) + 1)):
        error(f"Implementation top-level 번호는 1부터 연속이어야 합니다: {sorted(top_level)}")
    children: dict[int, set[int]] = {}
    for identifier in counts:
        if "-" not in identifier:
            continue
        parent_text, child_text = identifier.split("-", 1)
        parent, child = int(parent_text), int(child_text)
        children.setdefault(parent, set()).add(child)
        if parent not in top_level:
            error(f"Implementation substep parent 누락: {identifier}")
    for parent, values in sorted(children.items()):
        if values != set(range(1, max(values) + 1)):
            error(f"Implementation {parent} substep은 1부터 연속이어야 합니다: {sorted(values)}")

    readme_text = exercise_readme.read_text(encoding="utf-8")
    implementation_section = section(readme_text, "Reference 구현 순서")
    row_ids = re.findall(r"^\|\s*`(\d+(?:-\d+)?)`\s*\|", implementation_section, re.M)
    expected_ids = sorted(counts, key=implementation_sort_key)
    if row_ids != expected_ids:
        error(f"Reference 구현 순서 표와 annotation 불일치: {row_ids} != {expected_ids}")

    sidecars = [item for item in occurrences if item[1] == exercise_readme]
    if len(sidecars) != 1 or sidecars[0][0] != "10-6" or "reference/command_checker/py.typed" not in sidecars[0][3]:
        error("py.typed sidecar annotation은 README의 10-6 행에 정확히 한 번 있어야 합니다.")
    typed_marker = reference / "command_checker/py.typed"
    if typed_marker.read_text(encoding="utf-8").strip():
        error("reference py.typed는 공백 외 내용이 없는 marker여야 합니다.")


def github_slug(value: str) -> str:
    value = re.sub(r"<[^>]+>", "", value).replace("`", "").strip().lower()
    kept = [char for char in value if char in {" ", "-", "_"} or unicodedata.category(char)[0] in {"L", "N"}]
    return re.sub(r"\s+", "-", "".join(kept))


def anchors(path: Path) -> set[str]:
    counts: dict[str, int] = {}
    result: set[str] = set()
    for heading in re.findall(r"^#{1,6}\s+(.+?)\s*#*\s*$", path.read_text(encoding="utf-8"), re.M):
        base = github_slug(heading)
        count = counts.get(base, 0)
        counts[base] = count + 1
        result.add(base if count == 0 else f"{base}-{count}")
    return result


actual_docs = {path.relative_to(ROOT).as_posix() for path in (ROOT / "docs").rglob("*.md")}
if actual_docs != CONFIG["docs"]:
    missing = sorted(CONFIG["docs"] - actual_docs)
    extra = sorted(actual_docs - CONFIG["docs"])
    if missing:
        error("문서 누락: " + ", ".join(missing))
    if extra:
        error("예상하지 않은 문서: " + ", ".join(extra))

for relative in sorted(CONFIG["required"]):
    if not (ROOT / relative).is_file():
        error(f"필수 파일 누락: {relative}")
for relative in sorted(CONFIG["forbidden"]):
    path = ROOT / relative
    if path.exists() or path.is_symlink():
        error(f"이전 레이아웃이 남아 있음: {relative}")
for relative in sorted(CONFIG["executables"]):
    path = ROOT / relative
    if path.is_file() and not (path.stat().st_mode & stat.S_IXUSR):
        error(f"실행 모드 누락: {relative}")

manifest_path = ROOT / "scripts/layout-manifest.txt"
if manifest_path.is_file():
    manifest_lines = manifest_path.read_text(encoding="utf-8").splitlines()
    if manifest_lines != sorted(set(manifest_lines)) or any(not line or line.startswith("/") for line in manifest_lines):
        error("layout manifest는 중복 없는 정렬된 상대 경로여야 합니다.")
    layout_excluded = {".git", ".guide", ".venv", ".pytest_cache", "__pycache__", "workspace"}
    actual_layout = sorted(path.relative_to(ROOT).as_posix() for path in ROOT.rglob("*")
        if not any(part in layout_excluded for part in path.relative_to(ROOT).parts)
        and (path.is_file() or path.is_symlink()) and not path.name.endswith((".pyc", ".pyo")))
    if manifest_lines != actual_layout:
        missing = sorted(set(manifest_lines) - set(actual_layout)); extra = sorted(set(actual_layout) - set(manifest_lines))
        if missing: error("layout manifest 경로 누락: " + ", ".join(missing))
        if extra: error("layout manifest 밖 source 경로: " + ", ".join(extra))

excluded = {".git", ".guide", ".venv", ".pytest_cache", "__pycache__", "workspace"}
for path in ROOT.rglob("*"):
    relative = path.relative_to(ROOT)
    if ("__pycache__" in relative.parts or path.name.endswith((".pyc", ".pyo"))) and not any(
        part in {".git", ".guide", ".venv", "workspace"} for part in relative.parts
    ):
        error(f"Python cache가 source tree에 있음: {relative}")
    if any(part in excluded for part in relative.parts):
        continue
    if path.is_symlink():
        error(f"source tree에 심볼릭 링크가 있음: {relative}")

link_re = re.compile(r"(?<!!)\[[^]]*\]\(([^)]+)\)")
fence_re = re.compile(r"^\s*(`{3,}|~{3,})(.*)$")
markdown = sorted(
    path for path in ROOT.rglob("*.md")
    if not any(part in excluded for part in path.relative_to(ROOT).parts)
)
rubrics: dict[str, str] = {}
anchor_cache: dict[Path, set[str]] = {}
for path in markdown:
    relative = path.relative_to(ROOT).as_posix()
    data = path.read_bytes()
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        error(f"UTF-8이 아닌 문서: {relative}")
        continue
    if b"\r" in data:
        error(f"CR 줄 끝: {relative}")
    for number, line in enumerate(text.splitlines(), 1):
        if line.rstrip() != line:
            error(f"후행 공백: {relative}:{number}")
    if relative in CONFIG["concepts"]:
        contract = ("학습 목표", "선행 개념", "연결 실습", "완료 기준")
        headings = re.findall(r"^## (.+)$", text, re.M); positions = []
        for name in contract:
            if headings.count(name) != 1: error(f"교육 계약 heading 누락/중복: {relative}: {name}"); positions.append(-1)
            else: positions.append(headings.index(name))
            if not section(text, name): error(f"교육 계약 내용 누락: {relative}: {name}")
        if -1 not in positions and positions != sorted(positions): error(f"교육 계약 순서 오류: {relative}")
        if len(re.findall(r"^(?:- |\d+\. )", section(text, "완료 기준"), re.M)) < 3: error(f"완료 기준이 3개 미만: {relative}")
        connection = section(text, "연결 실습")
        if "](" not in connection or "README.md" not in connection: error(f"연결 실습이 실제 exercise README를 가리키지 않음: {relative}")
        rubric = "\n".join(re.sub(r"\s+", " ", section(text, name)).strip() for name in contract)
        if rubric in rubrics: error(f"복사된 교육 rubric: {relative} == {rubrics[rubric]}")
        else: rubrics[rubric] = relative
    opened: tuple[str, int, str, int] | None = None
    body: list[str] = []
    for number, line in enumerate(text.splitlines(), 1):
        match = fence_re.match(line)
        if opened is None:
            if match:
                marker, language = match.groups()
                opened = (marker[0], len(marker), language.strip().lower(), number)
                body = []
            continue
        if match and match.group(1)[0] == opened[0] and len(match.group(1)) >= opened[1]:
            if opened[2] in {"sh", "bash"}:
                shell = "sh" if opened[2] == "sh" else "bash"
                result = subprocess.run([shell, "-n"], input="\n".join(body) + "\n",
                                        text=True, capture_output=True, check=False)
                if result.returncode:
                    error(f"{opened[2]} 코드 블록 문법 오류: {relative}:{opened[3]}")
            opened = None
            body = []
        else:
            body.append(line)
    if opened is not None:
        error(f"닫히지 않은 코드 블록: {relative}:{opened[3]}")
    for match in link_re.finditer(text):
        raw = match.group(1).strip().strip("<>").split(maxsplit=1)[0]
        if not raw or raw.startswith(("http://", "https://", "mailto:", "tel:")):
            continue
        target_part, separator, fragment = raw.partition("#"); target = unquote(target_part)
        candidate = path if not target else (path.parent / target).resolve()
        try:
            candidate.relative_to(ROOT)
        except ValueError:
            error(f"저장소 밖 내부 링크: {relative}: {target}")
            continue
        if candidate.is_dir():
            candidate = candidate / "README.md"
        if not candidate.exists():
            error(f"깨진 내부 링크: {relative}: {target}")
            continue
        if separator and fragment and candidate.suffix.lower() == ".md":
            expected_anchor = unquote(fragment); available = anchor_cache.setdefault(candidate, anchors(candidate))
            if expected_anchor not in available: error(f"깨진 Markdown anchor: {relative}: {raw}")

roadmap_path = ROOT / "docs/00-roadmap.md"
if roadmap_path.is_file():
    roadmap = roadmap_path.read_text(encoding="utf-8")
    roadmap_contract = ("학습 목표", "대상 독자", "선행 개념", "지원 환경", "필수 학습 지도", "선택 학습 지도", "종료 능력", "범위 밖", "자동화의 한계")
    for name in roadmap_contract:
        if roadmap.count(f"## {name}\n") != 1 or not section(roadmap, name): error(f"roadmap 계약 누락/중복: {name}")
    if "Python 3.12" not in section(roadmap, "지원 환경"): error("roadmap 지원 환경에 Python 3.12가 없습니다.")
    required_map = section(roadmap, "필수 학습 지도"); mapped_learning = required_map + "\n" + section(roadmap, "선택 학습 지도")
    for concept in sorted(CONFIG["concepts"]):
        relative_to_docs = Path(concept).relative_to("docs").as_posix()
        if relative_to_docs not in mapped_learning: error(f"roadmap 필수/선택 학습 지도에서 문서 누락: {relative_to_docs}")
    if len(re.findall(r"^- ", section(roadmap, "자동화의 한계"), re.M)) < 2: error("roadmap 자동화의 한계가 두 항목 미만입니다.")

exercise_path = ROOT / CONFIG["exercise"]
if exercise_path.is_file():
    exercise = exercise_path.read_text(encoding="utf-8")
    headings = [exercise.find(f"\n## {name}\n") for name in
                ("목표", "완료 기준", "자기 설명", "검증")]
    if any(position < 0 for position in headings) or headings != sorted(headings):
        error(f"실습 교육 절의 순서/누락: {CONFIG['exercise']}")
    completion = re.search(r"\n## 완료 기준\n(.*?)(?=\n## |\Z)", exercise, re.S)
    reflection = re.search(r"\n## 자기 설명\n(.*?)(?=\n## |\Z)", exercise, re.S)
    if completion and len(re.findall(r"^- ", completion.group(1), re.M)) < 3:
        error(f"완료 기준 항목이 3개 미만: {CONFIG['exercise']}")
    if reflection and len(re.findall(r"^- .*\?\s*$", reflection.group(1), re.M)) < 2:
        error(f"자기 설명 질문이 2개 미만: {CONFIG['exercise']}")

if GUIDE == "python":
    validate_implementation_annotations()
    root_readme = (ROOT / "README.md").read_text(encoding="utf-8")
    learning_order = section(root_readme, "누적 학습 순서")
    for column in ("순서", "문서", "관찰 예제", "직접 수행", "수정 위치", "검증", "완료 뒤 비교·다음"):
        if column not in learning_order:
            error(f"README 학습 순서 column 누락: {column}")
    for concept in sorted(CONFIG["concepts"]):
        if concept not in learning_order:
            error(f"README 학습 순서에서 문서 누락: {concept}")
    for stage in range(1, 9):
        command = f"make stage-{stage:02d} EXERCISE_IMPL=workspace"
        if command not in learning_order:
            error(f"README 학습 순서에서 stage 명령 누락: {command}")
    for phrase in ("examples/", "fixtures/", "workspace/", "reference/", "make exercise-check EXERCISE_IMPL=workspace"):
        if phrase not in learning_order:
            error(f"README 학습 순서 역할 누락: {phrase}")

    makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
    if not re.search(r"^EXERCISE_IMPL \?= workspace$", makefile, re.M):
        error("Makefile의 EXERCISE_IMPL 기본값은 workspace여야 합니다.")
    if not re.search(r"^reference-check:\n\t@\$\(MAKE\).*EXERCISE_IMPL=reference$", makefile, re.M):
        error("reference-check는 reference를 명시적으로 선택해야 합니다.")

    expected_modules = {"__init__.py", "__main__.py", "cli.py", "comparison.py", "model.py",
                        "process.py", "reports.py", "runner.py", "specification.py"}
    for implementation in ("reference", "skeleton"):
        project = ROOT / "exercises/command-checker" / implementation
        directory = project / "command_checker"
        actual = {path.name for path in directory.glob("*.py")}
        if actual != expected_modules:
            error(f"{implementation} 모듈 집합 불일치: {sorted(actual)}")
        if not (directory / "py.typed").is_file():
            error(f"{implementation} typed package marker 누락")
        try:
            pyproject = tomllib.loads((project / "pyproject.toml").read_text(encoding="utf-8"))
        except (OSError, tomllib.TOMLDecodeError) as exc:
            error(f"{implementation} pyproject를 읽을 수 없음: {exc}")
        else:
            metadata = pyproject.get("project", {})
            if metadata.get("name") != "command-checker" or metadata.get("requires-python") != ">=3.12":
                error(f"{implementation} project metadata 불일치")
            if metadata.get("dependencies") != []:
                error(f"{implementation} project runtime dependencies는 비어 있어야 함")
            if metadata.get("scripts") != {"command-checker": "command_checker.cli:main"}:
                error(f"{implementation} console script 계약 불일치")
            if pyproject.get("build-system") != {
                "requires": [], "build-backend": "_command_checker_build", "backend-path": ["."]
            }:
                error(f"{implementation} dependency-free build backend 계약 불일치")
    expected_tests = {"test_command_checker.py", "test_stage_01_entrypoint.py",
                      "test_stage_02_model.py", "test_stage_03_comparison.py",
                      "test_stage_04_specification.py", "test_stage_05_execution.py",
                      "test_stage_06_aggregation.py", "test_stage_07_process_lifecycle.py",
                      "test_stage_08_concurrency_and_reports.py"}
    actual_tests = {path.name for path in (ROOT / "exercises/command-checker/tests").glob("test_*.py")}
    if actual_tests != expected_tests:
        error(f"테스트 모듈 집합 불일치: {sorted(actual_tests)}")
    for path in (ROOT / "exercises/command-checker/reference").rglob("*.py"):
        if "TODO" in path.read_text(encoding="utf-8") or "NotImplementedError" in path.read_text(encoding="utf-8"):
            error(f"reference 미완성 표식: {path.relative_to(ROOT)}")

if GUIDE == "unix-systems":
    answer = json.loads((ROOT / "exercises/system-investigation/reference/diagnoses.json").read_text(encoding="utf-8"))
    cases = answer.get("cases", {})
    expected_cases = {f"{number:02d}-{name}" for number, name in enumerate((
        "command-resolution", "dangling-symlink", "waiting-for-input", "deleted-open-file",
        "working-directory", "address-family-mismatch", "running-not-ready",
        "signal-not-forwarded", "reserved-not-resident"), 1)}
    if set(cases) != expected_cases:
        error("Unix 기준 답안은 정확히 아홉 사례여야 합니다.")

reference_roots: list[Path] = []
for base in (ROOT / "reference", ROOT / "exercises"):
    if not base.is_dir(): continue
    if base.name == "reference": reference_roots.append(base)
    reference_roots.extend(path for path in base.rglob("reference") if path.is_dir())
for reference_root in sorted(set(reference_roots)):
    for path in reference_root.rglob("*"):
        if path.is_file() and path.suffix.lower() in {".py", ".md", ".json", ".sh"}:
            text = path.read_text(encoding="utf-8")
            if "TODO" in text or "NotImplementedError" in text: error(f"reference 미완성 표식: {path.relative_to(ROOT)}")

if errors:
    print("VALIDATOR RESULT: FAIL", file=sys.stderr)
    for message in errors:
        print(f"- {message}", file=sys.stderr)
    raise SystemExit(1)
print(f"VALIDATOR RESULT: PASS ({GUIDE}, {len(markdown)} markdown files)")
