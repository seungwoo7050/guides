#!/usr/bin/env python3
"""Validate the final guide layout and its teaching contracts."""

from __future__ import annotations

import json
import os
import re
import stat
import subprocess
import sys
import unicodedata
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
        "connections": {
            "docs/01-workspace-basics.md": "1단계-작업-공간과-브랜치",
            "docs/02-commit-workflow.md": "2단계-변경-검토와-커밋",
            "docs/03-remote-pr-workflow.md": "3단계-원격-협업",
            "docs/04-merge-rebase-conflicts.md": "4단계-충돌-해결",
            "docs/05-recovery-runbook.md": "5단계-복구-증거",
            "docs/90-open-source-contribution.md": "선택-90-오픈소스-기여",
        },
        "required": {
            "README.md", "CONTRIBUTING.md", "Makefile", "prepare.sh", "verify.sh",
            "scripts/repository_state.py", "scripts/validate.py",
            "scripts/test-prepare-safety.sh", "scripts/test-validator.py",
            "scripts/validate.sh", "scripts/layout-manifest.txt",
            "scripts/test-verify-negatives.sh",
            "exercises/setup.sh",
        },
        "forbidden": {"docs/06-open-source-contribution.md", "git/exercises/workspace"},
        "executables": {"prepare.sh", "verify.sh", "scripts/validate.py",
                        "scripts/test-prepare-safety.sh", "scripts/test-validator.py",
                        "scripts/test-verify-negatives.sh",
                        "scripts/validate.sh", "exercises/setup.sh"},
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
            "scripts/layout-manifest.txt",
            "scripts/check_docs.py", "scripts/check_test_quality.py",
            "scripts/check_stage_contracts.py", "scripts/new-workspace.sh",
        },
        "forbidden": {
            "docs/01-runtime-and-environment.md", "docs/02-objects-and-collections.md",
            "docs/03-functions-errors-and-types.md", "docs/04-files-and-cli.md",
            "docs/05-subprocess-and-automation.md", "docs/06-testing.md",
            "docs/07-cli-test-runner.md", "docs/08-algorithms-and-project-quality.md",
            "exercises/command-checker/tests/test_stage_07_reports.py",
        },
        "executables": {"prepare.sh", "verify.sh", "scripts/validate.py",
                        "scripts/test-validator.py", "scripts/check_docs.py",
                        "scripts/check_test_quality.py", "scripts/check_stage_contracts.py",
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


def github_slug(value: str) -> str:
    value = re.sub(r"<[^>]+>", "", value).replace("`", "").strip().lower()
    kept = [char for char in value if char in {" ", "-", "_"} or unicodedata.category(char)[0] in {"L", "N"}]
    return re.sub(r"\s+", "-", "".join(kept))


def anchors(path: Path) -> set[str]:
    counts: dict[str, int] = {}
    result: set[str] = set()
    opened: tuple[str, int] | None = None
    headings: list[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        fence = re.match(r"^\s*(`{3,}|~{3,})", line)
        if fence:
            marker = fence.group(1)
            if opened is None:
                opened = (marker[0], len(marker))
            elif marker[0] == opened[0] and len(marker) >= opened[1]:
                opened = None
            continue
        if opened is not None:
            continue
        heading = re.match(r"^#{1,6}\s+(.+?)\s*#*\s*$", line)
        if heading:
            headings.append(heading.group(1))
    for heading in headings:
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
    actual_layout = sorted(
        path.relative_to(ROOT).as_posix()
        for path in ROOT.rglob("*")
        if not any(part in layout_excluded for part in path.relative_to(ROOT).parts)
        and (path.is_file() or path.is_symlink())
        and not path.name.endswith((".pyc", ".pyo"))
    )
    if manifest_lines != actual_layout:
        missing = sorted(set(manifest_lines) - set(actual_layout))
        extra = sorted(set(actual_layout) - set(manifest_lines))
        if missing:
            error("layout manifest 경로 누락: " + ", ".join(missing))
        if extra:
            error("layout manifest 밖 source 경로: " + ", ".join(extra))

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
        headings = re.findall(r"^## (.+)$", text, re.M)
        positions = []
        for name in contract:
            if headings.count(name) != 1:
                error(f"교육 계약 heading 누락/중복: {relative}: {name}")
                positions.append(-1)
            else:
                positions.append(headings.index(name))
            if not section(text, name):
                error(f"교육 계약 내용 누락: {relative}: {name}")
        if -1 not in positions and positions != sorted(positions):
            error(f"교육 계약 순서 오류: {relative}")
        completion = section(text, "완료 기준")
        if len(re.findall(r"^(?:- |\d+\. )", completion, re.M)) < 3:
            error(f"완료 기준이 3개 미만: {relative}")
        connection = section(text, "연결 실습")
        expected_exercise = (ROOT / CONFIG["exercise"]).resolve()
        expected_fragment = CONFIG.get("connections", {}).get(relative)
        resolved_connections: list[tuple[Path, str]] = []
        for link in link_re.finditer(connection):
            raw = link.group(1).strip().strip("<>").split(maxsplit=1)[0]
            if not raw or raw.startswith(("http://", "https://", "mailto:", "tel:")):
                continue
            target_part, _, fragment = raw.partition("#")
            target = unquote(target_part)
            candidate = path if not target else (path.parent / target).resolve()
            if candidate.is_dir():
                candidate = candidate / "README.md"
            resolved_connections.append((candidate, unquote(fragment)))
        if not any(candidate == expected_exercise for candidate, _ in resolved_connections):
            error(f"연결 실습이 실제 exercise README를 가리키지 않음: {relative}")
        if expected_fragment and (expected_exercise, expected_fragment) not in resolved_connections:
            error(f"연결 실습이 해당 단계 증거를 가리키지 않음: {relative}#{expected_fragment}")
        rubric = "\n".join(re.sub(r"\s+", " ", section(text, name)).strip() for name in contract)
        if rubric in rubrics:
            error(f"복사된 교육 rubric: {relative} == {rubrics[rubric]}")
        else:
            rubrics[rubric] = relative
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
        target_part, separator, fragment = raw.partition("#")
        target = unquote(target_part)
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
            expected_anchor = unquote(fragment)
            available = anchor_cache.setdefault(candidate, anchors(candidate))
            if expected_anchor not in available:
                error(f"깨진 Markdown anchor: {relative}: {raw}")

if GUIDE == "git":
    root_readme = (ROOT / "README.md").read_text(encoding="utf-8")
    learning_map = section(root_readme, "학습 순서와 실습 지도")
    table_lines = [line for line in learning_map.splitlines() if line.strip().startswith("|")]
    table = [[cell.strip() for cell in line.strip().strip("|").split("|")] for line in table_lines]
    expected_header = ["순서", "문서", "관찰 예제", "직접 수행", "수정 위치", "검증", "완료 뒤 비교·다음"]
    if len(table) < 2 or table[0] != expected_header:
        error("root README 학습 지도 header 불일치")
        learning_rows: list[list[str]] = []
    elif len(table[1]) != 7 or not all(re.fullmatch(r":?-{3,}:?", cell) for cell in table[1]):
        error("root README 학습 지도 separator 불일치")
        learning_rows = table[2:]
    else:
        learning_rows = table[2:]
    if any(len(row) != 7 for row in learning_rows):
        error("root README 학습 지도는 행마다 정확히 일곱 열이어야 함")

    git_learning_rows = [
        ("0", "docs/00-roadmap.md", None, "—", "docs/01-workspace-basics.md"),
        ("1", "docs/01-workspace-basics.md", "1단계-작업-공간과-브랜치",
         "exercises/workspace/sample-app", "docs/02-commit-workflow.md"),
        ("2", "docs/02-commit-workflow.md", "2단계-변경-검토와-커밋",
         "exercises/workspace/sample-app", "docs/03-remote-pr-workflow.md"),
        ("3", "docs/03-remote-pr-workflow.md", "3단계-원격-협업",
         "exercises/workspace/team-app-dev-a", "docs/04-merge-rebase-conflicts.md"),
        ("4", "docs/04-merge-rebase-conflicts.md", "4단계-충돌-해결",
         "exercises/workspace/team-app-*", "docs/05-recovery-runbook.md"),
        ("5", "docs/05-recovery-runbook.md", "5단계-복구-증거",
         "exercises/workspace/recovery-lab.*", "필수 과정 종료"),
        ("선택 90", "docs/90-open-source-contribution.md", "선택-90-오픈소스-기여",
         "exercises/workspace/team-app-*", "가이드 종료"),
    ]
    expected_order = [document for _, document, _, _, _ in git_learning_rows]
    actual_order: list[str] = []
    for row in learning_rows:
        if len(row) != 7:
            continue
        targets = re.findall(r"\]\(([^)#]+)(?:#[^)]+)?\)", row[1])
        actual_order.append(targets[0] if len(targets) == 1 else "")
    if actual_order != expected_order:
        error("root README 학습 지도 문서 행 누락·중복·순서 오류")

    rows_by_order = {row[0]: row for row in learning_rows if len(row) == 7}
    for order, document, fragment, workspace, next_step in git_learning_rows:
        row = rows_by_order.get(order)
        if row is None:
            error(f"root README 학습 지도 단계 누락: {order}")
            continue
        document_targets = re.findall(r"\]\(([^)#]+)(?:#[^)]+)?\)", row[1])
        if document_targets != [document]:
            error(f"root README 학습 지도 문서 열 불일치: {order}")
        if row[2] != "—":
            error(f"root README 학습 지도 관찰 예제 없음 표시 누락: {order}")
        if not row[3] or row[3] == "—":
            error(f"root README 학습 지도 직접 수행 열 누락: {order}")
        if fragment and f"exercises/README.md#{fragment}" not in row[3]:
            error(f"root README 학습 지도 단계별 실습 링크 누락: {order}")
        if workspace not in row[4]:
            error(f"root README 학습 지도 수정 위치 누락: {order}")
        if not row[5] or row[5] == "—":
            error(f"root README 학습 지도 검증 열 누락: {order}")
        if not row[6] or next_step not in row[6] or (fragment and "기대 증거" not in row[6]):
            error(f"root README 학습 지도 완료 증거·다음 단계 누락: {order}")

    quick_reference_links = {
        "reference/quick-reference.md", "reference/repository-policy.md",
    }
    mapped_reference_links = set(re.findall(r"\]\((reference/[^)#]+)(?:#[^)]+)?\)", learning_map))
    if not quick_reference_links <= mapped_reference_links or not re.search(
        r"root-level `reference/`[^\n]*(?:답안|완성 구현)[^\n]*(?:아닙|아니)", learning_map
    ):
        error("root README가 root reference 문서와 exercise 답안을 구분하지 않음")

    roadmap_required = section((ROOT / "docs/00-roadmap.md").read_text(encoding="utf-8"), "필수 학습 지도")
    roadmap_order: list[str] = []
    for line in roadmap_required.splitlines():
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) == 5 and re.fullmatch(r"[1-5]", cells[0]):
            targets = re.findall(r"\]\(([^)#]+)(?:#[^)]+)?\)", cells[1])
            roadmap_order.extend(f"docs/{target}" for target in targets)
    if roadmap_order != expected_order[1:6]:
        error("README와 roadmap의 필수 문서 순서가 일치하지 않음")
    roadmap_optional = section((ROOT / "docs/00-roadmap.md").read_text(encoding="utf-8"), "선택 학습 지도")
    if "](90-open-source-contribution.md)" not in roadmap_optional:
        error("roadmap 선택 학습 지도에 90편이 없음")

    exercise_contract = (ROOT / CONFIG["exercise"]).read_text(encoding="utf-8")
    evidence_headings = {
        "1단계 작업 공간과 브랜치": ("작업 트리", "HEAD", "origin/main"),
        "2단계 변경 검토와 커밋": ("커밋", "개인 메모", "diff"),
        "3단계 원격 협업": ("upstream", "remote-tracking ref", "graph"),
        "4단계 충돌 해결": ("priority", "assignee", "push", "--force-with-lease"),
        "5단계 복구 증거": ("recovery/*", "detached", "revert", "stash"),
        "선택 90 오픈소스 기여": ("origin", "upstream", "PR", "diff"),
    }
    expected_fields = ["직접 수행", "수정 위치", "검증", "기대 증거", "다음"]
    stage_bodies: dict[str, str] = {}
    for heading, required_terms in evidence_headings.items():
        match = re.search(
            rf"^### {re.escape(heading)}\n(.*?)(?=^### |^## |\Z)",
            exercise_contract,
            re.M | re.S,
        )
        if not match:
            error(f"exercise 단계별 기대 증거 누락: {heading}")
            continue
        body = match.group(1)
        stage_bodies[heading] = body
        matches = re.findall(r"^- \*\*(직접 수행|수정 위치|검증|기대 증거|다음):\*\*\s*(\S.*)$", body, re.M)
        labels = [label for label, _ in matches]
        if labels != expected_fields:
            error(f"exercise 단계 필드 누락·중복·순서 오류: {heading}")
        fields = dict(matches)
        evidence = fields.get("기대 증거", "")
        for term in required_terms:
            if term not in evidence:
                error(f"exercise 단계 증거 계약 누락: {heading}: {term}")
    recovery_walkthrough = stage_bodies.get("5단계 복구 증거", "")
    for command in (
        "mktemp -d exercises/workspace/recovery-lab.XXXXXX",
        "git -C \"$RECOVERY_LAB\" reset --hard HEAD^",
        "git -C \"$RECOVERY_LAB\" switch --detach main",
        "git -C \"$RECOVERY_LAB\" branch recovery/reset",
        "git -C \"$RECOVERY_LAB\" branch recovery/detached",
        "git -C \"$RECOVERY_LAB\" revert --no-edit HEAD",
        "git -C \"$RECOVERY_LAB\" stash push -u",
    ):
        if command not in recovery_walkthrough:
            error(f"exercise 복구 sandbox walkthrough 누락: {command}")
    verification = section(exercise_contract, "검증")
    if "### 학습자 단계 검증" not in verification or "### 저장소 자체 검증" not in verification:
        error("exercise가 학습자 증거와 저장소 자체 검증을 구분하지 않음")
    if "`exercises/workspace/`" not in verification or "검사하지 않" not in verification:
        error("저장소 자체 검증의 learner workspace 비판정 한계 누락")
    if "Python 3.12" not in exercise_contract:
        error("exercise 지원 환경에 Python 3.12가 없습니다.")

    implementation_token = re.compile(r"\[" + r"Implementation\b[^\]\n]*\]", re.I)
    annotation_excluded = excluded | {"node_modules", "vendor", "dist", "build", ".next", "target", "generated"}
    lockfiles = {"package-lock.json", "pnpm-lock.yaml", "yarn.lock", "poetry.lock"}
    for candidate in ROOT.rglob("*"):
        if (not candidate.is_file()
                or candidate.name in lockfiles
                or any(part in annotation_excluded for part in candidate.relative_to(ROOT).parts)):
            continue
        try:
            content = candidate.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        if implementation_token.search(content):
            error(f"Git 상태·증거 실습의 annotation 면제 위반: {candidate.relative_to(ROOT)}")

roadmap_path = ROOT / "docs/00-roadmap.md"
if roadmap_path.is_file():
    roadmap = roadmap_path.read_text(encoding="utf-8")
    roadmap_contract = ("학습 목표", "대상 독자", "선행 개념", "지원 환경", "필수 학습 지도",
                        "선택 학습 지도", "종료 능력", "범위 밖", "자동화의 한계")
    for name in roadmap_contract:
        if roadmap.count(f"## {name}\n") != 1 or not section(roadmap, name):
            error(f"roadmap 계약 누락/중복: {name}")
    if "Python 3.12" not in section(roadmap, "지원 환경"):
        error("roadmap 지원 환경에 Python 3.12가 없습니다.")
    required_map = section(roadmap, "필수 학습 지도")
    mapped_learning = required_map + "\n" + section(roadmap, "선택 학습 지도")
    for concept in sorted(CONFIG["concepts"]):
        relative_to_docs = Path(concept).relative_to("docs").as_posix()
        if relative_to_docs not in mapped_learning:
            error(f"roadmap 필수/선택 학습 지도에서 문서 누락: {relative_to_docs}")
    if len(re.findall(r"^- ", section(roadmap, "자동화의 한계"), re.M)) < 2:
        error("roadmap 자동화의 한계가 두 항목 미만입니다.")

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
    expected_modules = {"__init__.py", "__main__.py", "cli.py", "comparison.py", "model.py",
                        "process.py", "reports.py", "runner.py", "specification.py"}
    for implementation in ("reference", "skeleton"):
        directory = ROOT / "exercises/command-checker" / implementation / "command_checker"
        actual = {path.name for path in directory.glob("*.py")}
        if actual != expected_modules:
            error(f"{implementation} 모듈 집합 불일치: {sorted(actual)}")
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
for base in (ROOT / "exercises", ROOT / "projects"):
    if not base.is_dir():
        continue
    reference_roots.extend(
        path for path in base.rglob("reference")
        if path.is_dir() and not any(part in excluded for part in path.relative_to(ROOT).parts)
    )
for reference_root in sorted(set(reference_roots)):
    for path in reference_root.rglob("*"):
        if (path.is_file()
                and not any(part in excluded for part in path.relative_to(ROOT).parts)
                and path.suffix.lower() in {".py", ".md", ".json", ".sh"}):
            text = path.read_text(encoding="utf-8")
            if "TODO" in text or "NotImplementedError" in text:
                error(f"reference 미완성 표식: {path.relative_to(ROOT)}")

if errors:
    print("VALIDATOR RESULT: FAIL", file=sys.stderr)
    for message in errors:
        print(f"- {message}", file=sys.stderr)
    raise SystemExit(1)
print(f"VALIDATOR RESULT: PASS ({GUIDE}, {len(markdown)} markdown files)")
