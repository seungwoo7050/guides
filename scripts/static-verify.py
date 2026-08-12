#!/usr/bin/env python3
"""웹 인프라 가이드의 구조, 문서, 설정과 검증 계약을 정적으로 검사합니다."""
from __future__ import annotations

import ast
import csv
import fnmatch
import json
import os
import re
import stat
import subprocess
import sys
from pathlib import Path
from typing import Iterable
from urllib.parse import unquote

try:
    import yaml
except ImportError as error:  # pragma: no cover - environment-dependent message
    print(
        "오류: PyYAML 6.0.3이 필요합니다. 저장소 루트에서 ./prepare.sh를 실행하세요.",
        file=sys.stderr,
    )
    raise SystemExit(2) from error

ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = ROOT.resolve()
ERRORS: list[str] = []
CHECKS = 0
ALLOW_GENERATED_EXERCISE_STATE = False
IGNORED_PARTS = {".git", ".verify", "__pycache__", "workspace", ".workspace.lock"}
IGNORED_TOP_LEVEL = {"make-out.txt"}

DOCS = [
    (0, "roadmap"),
    (1, "web-request-and-server"),
    (2, "docker-image-and-container"),
    (3, "compose-network-and-storage"),
    (4, "nginx-tls-and-php-fpm"),
    (5, "database-lifecycle"),
    (6, "idempotent-app-bootstrap"),
    (7, "operations-debugging-and-recovery"),
    (8, "production-contract-and-threat-model"),
    (9, "linux-host-provisioning-and-hardening"),
    (10, "dns-acme-and-public-tls"),
    (11, "image-registry-and-release-artifacts"),
    (12, "ci-cd-deployment-and-rollback"),
    (13, "production-secrets-and-configuration"),
    (14, "observability-and-alerting"),
    (15, "backup-restore-and-disaster-recovery"),
    (16, "capacity-resource-limits-and-updates"),
    (17, "incident-response-and-runbooks"),
    (18, "production-rebuild-capstone"),
]

EXERCISES = [
    (1, "request-and-process"),
    (2, "container"),
    (3, "compose"),
    (4, "gateway-runtime"),
    (5, "database"),
    (6, "app-bootstrap"),
    (7, "troubleshooting"),
    (8, "production-contract"),
    (9, "host-hardening"),
    (10, "public-tls"),
    (11, "release-artifact"),
    (12, "deployment-rollback"),
    (13, "secret-rotation"),
    (14, "observability"),
    (15, "disaster-recovery"),
    (16, "capacity-and-updates"),
    (17, "incident-response"),
    (18, "production-rebuild"),
]

EXERCISE_DIRECT_EXTRAS = {
    2: {"breakages"},
    7: {"check-evidence.py", "run-scenario.sh", "scenarios", "template"},
    8: {"verify.py"},
    9: {"fixtures", "verify.py"},
    11: {"verify.py"},
    12: {"fixtures", "verify.py"},
    13: {"verify.py"},
    14: {"verify.py"},
    15: {"fixtures", "verify.py"},
    16: {"fixtures", "verify.py"},
    17: {"fixtures", "verify.py"},
    18: {"verify.py"},
}

TROUBLESHOOTING_SCENARIOS = (
    "wrong-db-host",
    "wrong-db-password",
    "missing-secret",
    "wrong-fcgi-port",
    "broken-healthcheck",
    "data-loss",
)

RUNBOOKS = [
    "00-index",
    "01-502-504-upstream-failure",
    "02-database-authentication-failure",
    "03-disk-exhaustion",
    "04-certificate-renewal-failure",
    "05-container-restart-loop",
    "06-bad-deployment-rollback",
    "07-backup-job-failure",
    "08-data-restore",
    "09-host-rebuild",
    "10-secret-compromise",
]

REFERENCE_FILES = {
    "command-reference.md",
    "glossary.md",
    "php-pdo-bootstrap.md",
    "troubleshooting-matrix.md",
}

SCRIPT_FILES = {
    "cleanup-runtime.sh",
    "meta-verify.py",
    "new-workspace.py",
    "requirements.txt",
    "static-verify.py",
    "test-workspace.py",
    "verify-all.sh",
}

PRODUCTION_FILES = [
    "exercises/07-troubleshooting/check-evidence.py",
    "exercises/07-troubleshooting/template/evidence.md",
    "exercises/08-production-contract/skeleton/contract.yaml",
    "exercises/08-production-contract/reference/contract.yaml",
    "exercises/08-production-contract/verify.py",
    "exercises/09-host-hardening/fixtures/secure.json",
    "exercises/09-host-hardening/fixtures/insecure.json",
    "exercises/09-host-hardening/skeleton/audit.py",
    "exercises/09-host-hardening/reference/audit.py",
    "exercises/09-host-hardening/verify.py",
    "exercises/10-public-tls/skeleton/tls-lifecycle.sh",
    "exercises/10-public-tls/reference/tls-lifecycle.sh",
    "exercises/11-release-artifact/skeleton/Dockerfile",
    "exercises/11-release-artifact/reference/Dockerfile",
    "exercises/11-release-artifact/reference/app.py",
    "exercises/11-release-artifact/skeleton/release.yaml",
    "exercises/11-release-artifact/reference/release.yaml",
    "exercises/11-release-artifact/verify.py",
    "exercises/12-deployment-rollback/skeleton/deploy.py",
    "exercises/12-deployment-rollback/reference/deploy.py",
    "exercises/12-deployment-rollback/fixtures/v1.yaml",
    "exercises/12-deployment-rollback/fixtures/v2.yaml",
    "exercises/12-deployment-rollback/fixtures/bad.yaml",
    "exercises/12-deployment-rollback/fixtures/incompatible.yaml",
    "exercises/12-deployment-rollback/verify.py",
    "exercises/13-secret-rotation/skeleton/rotate.py",
    "exercises/13-secret-rotation/reference/rotate.py",
    "exercises/13-secret-rotation/verify.py",
    "exercises/14-observability/skeleton/app.py",
    "exercises/14-observability/reference/app.py",
    "exercises/14-observability/verify.py",
    "exercises/15-disaster-recovery/fixtures/source/database.json",
    "exercises/15-disaster-recovery/skeleton/backup.py",
    "exercises/15-disaster-recovery/reference/backup.py",
    "exercises/15-disaster-recovery/verify.py",
    "exercises/16-capacity-and-updates/fixtures/metrics.csv",
    "exercises/16-capacity-and-updates/fixtures/components.json",
    "exercises/16-capacity-and-updates/fixtures/policy.json",
    "exercises/16-capacity-and-updates/skeleton/plan.py",
    "exercises/16-capacity-and-updates/reference/plan.py",
    "exercises/16-capacity-and-updates/verify.py",
    "exercises/17-incident-response/fixtures/incident.json",
    "exercises/17-incident-response/skeleton/response.yaml",
    "exercises/17-incident-response/reference/response.yaml",
    "exercises/17-incident-response/verify.py",
    "exercises/18-production-rebuild/skeleton/rebuild-plan.yaml",
    "exercises/18-production-rebuild/reference/rebuild-plan.yaml",
    "exercises/18-production-rebuild/verify.py",
]


def parse_args() -> None:
    global ALLOW_GENERATED_EXERCISE_STATE
    allowed = {"--allow-generated-exercise-state"}
    unknown = set(sys.argv[1:]) - allowed
    if unknown:
        print(f"오류: 알 수 없는 인자입니다: {', '.join(sorted(unknown))}", file=sys.stderr)
        raise SystemExit(2)
    ALLOW_GENERATED_EXERCISE_STATE = "--allow-generated-exercise-state" in sys.argv[1:]


def error(message: str) -> None:
    ERRORS.append(message)


def count() -> None:
    global CHECKS
    CHECKS += 1


def is_ignored(path: Path) -> bool:
    try:
        relative = path.relative_to(ROOT)
    except ValueError:
        return True
    return any(
        part in IGNORED_PARTS or part.startswith(".workspace.tmp.")
        for part in relative.parts
    ) or (
        len(relative.parts) == 1 and relative.name in IGNORED_TOP_LEVEL
    )


def repository_paths(pattern: str) -> Iterable[Path]:
    for current, directories, files in os.walk(ROOT, topdown=True, followlinks=False):
        current_path = Path(current)
        kept: list[str] = []
        for name in directories:
            child = current_path / name
            if is_ignored(child):
                continue
            if fnmatch.fnmatch(name, pattern):
                yield child
            kept.append(name)
        directories[:] = kept
        for name in files:
            child = current_path / name
            if not is_ignored(child) and fnmatch.fnmatch(name, pattern):
                yield child


def run_check(label: str, command: list[str]) -> None:
    count()
    completed = subprocess.run(
        command,
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    if completed.returncode != 0:
        error(f"{label} 검사에 실패했습니다:\n{completed.stdout.rstrip()}")


def require_files() -> None:
    required = [
        ".gitignore",
        "CONTRIBUTING.md",
        "LICENSE.md",
        "Makefile",
        "README.md",
        "prepare.sh",
        "verify.sh",
        *[f"docs/{number:02d}-{name}.md" for number, name in DOCS],
        *[f"docs/runbooks/{name}.md" for name in RUNBOOKS],
        *[f"reference/{name}" for name in sorted(REFERENCE_FILES)],
        *[f"scripts/{name}" for name in sorted(SCRIPT_FILES)],
        *PRODUCTION_FILES,
    ]
    for number, name in EXERCISES:
        directory = f"exercises/{number:02d}-{name}"
        required.extend([f"{directory}/README.md", f"{directory}/verify.sh"])
    for relative in required:
        count()
        if not (ROOT / relative).is_file():
            error(f"필수 파일이 없습니다: {relative}")



def directory_names(path: Path, label: str) -> set[str]:
    count()
    if not path.is_dir():
        error(f"필수 디렉터리가 없습니다: {label}")
        return set()
    try:
        return {child.name for child in path.iterdir()}
    except OSError as exc:
        error(f"디렉터리를 읽을 수 없습니다: {label}: {exc}")
        return set()


def is_exercise_runtime_child(name: str) -> bool:
    return (
        name in {"workspace", ".workspace.lock"}
        or name.startswith(".workspace.tmp.")
    )


def check_top_level_layout() -> None:
    allowed = {
        ".git",
        ".gitignore",
        ".verify",
        "CONTRIBUTING.md",
        "LICENSE.md",
        "LICENSES",
        "Makefile",
        "README.md",
        "docs",
        "exercises",
        "make-out.txt",
        "prepare.sh",
        "reference",
        "scripts",
        "verify.sh",
    }
    for path in ROOT.iterdir():
        count()
        if path.name not in allowed:
            error(f"예상하지 않은 저장소 최상위 경로입니다: {path.name}")

    expected_docs = {
        *{f"{number:02d}-{name}.md" for number, name in DOCS},
        "runbooks",
    }
    actual_docs = directory_names(ROOT / "docs", "docs")
    for missing in sorted(expected_docs - actual_docs):
        error(f"docs 경로가 없습니다: docs/{missing}")
    for extra in sorted(actual_docs - expected_docs):
        error(f"구형 또는 계획 밖 docs 경로입니다: docs/{extra}")

    expected_exercises = {f"{number:02d}-{name}" for number, name in EXERCISES}
    actual_exercises = directory_names(ROOT / "exercises", "exercises")
    for missing in sorted(expected_exercises - actual_exercises):
        error(f"exercise 경로가 없습니다: exercises/{missing}")
    for extra in sorted(actual_exercises - expected_exercises):
        error(f"구형 또는 계획 밖 exercise 경로입니다: exercises/{extra}")

    for number, name in EXERCISES:
        exercise_name = f"{number:02d}-{name}"
        exercise = ROOT / "exercises" / exercise_name
        expected_children = {"README.md", "verify.sh"}
        if number != 7:
            expected_children.update({"skeleton", "reference"})
        expected_children.update(EXERCISE_DIRECT_EXTRAS.get(number, set()))
        actual_children = {
            child
            for child in directory_names(exercise, f"exercises/{exercise_name}")
            if not is_exercise_runtime_child(child)
        }
        for missing in sorted(expected_children - actual_children):
            error(
                "exercise direct path가 없습니다: "
                f"exercises/{exercise_name}/{missing}"
            )
        for extra in sorted(actual_children - expected_children):
            error(
                "예상하지 않은 exercise direct path입니다: "
                f"exercises/{exercise_name}/{extra}"
            )

    actual_reference = directory_names(ROOT / "reference", "reference")
    for missing in sorted(REFERENCE_FILES - actual_reference):
        error(f"reference 파일이 없습니다: reference/{missing}")
    for extra in sorted(actual_reference - REFERENCE_FILES):
        error(f"계획 밖 reference 경로입니다: reference/{extra}")

    actual_scripts = directory_names(ROOT / "scripts", "scripts") - {"__pycache__"}
    for missing in sorted(SCRIPT_FILES - actual_scripts):
        error(f"scripts 파일이 없습니다: scripts/{missing}")
    for extra in sorted(actual_scripts - SCRIPT_FILES):
        error(f"구형 또는 계획 밖 scripts 경로입니다: scripts/{extra}")


def check_markdown() -> None:
    link_pattern = re.compile(r"(?<!!)\[[^\]]+\]\(([^)]+)\)")
    for path in sorted(repository_paths("*.md")):
        count()
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as exc:
            error(f"Markdown 파일을 읽을 수 없습니다: {path.relative_to(ROOT)}: {exc}")
            continue
        lines = text.splitlines()
        if not text.startswith("# "):
            error(f"Markdown 첫 줄에 H1 제목이 없습니다: {path.relative_to(ROOT)}")
        if not text.endswith("\n"):
            error(f"Markdown 파일은 LF로 끝나야 합니다: {path.relative_to(ROOT)}")
        if "\r\n" in text:
            error(f"Markdown 줄바꿈은 LF를 사용해야 합니다: {path.relative_to(ROOT)}")

        in_fence = False
        h1_count = 0
        link_targets: list[str] = []
        for line in lines:
            stripped = line.lstrip()
            if stripped.startswith("```") or stripped.startswith("~~~"):
                in_fence = not in_fence
                continue
            if in_fence:
                continue
            if line.startswith("# "):
                h1_count += 1
            link_targets.extend(link_pattern.findall(line))

        if in_fence:
            error(f"Markdown code fence가 닫히지 않았습니다: {path.relative_to(ROOT)}")
        if h1_count != 1:
            error(f"Markdown에는 문서 H1이 정확히 하나여야 합니다: {path.relative_to(ROOT)}")

        for raw_target in link_targets:
            target = raw_target.strip().split()[0].strip("<>")
            if target.startswith(("http://", "https://", "mailto:")):
                continue
            file_target = unquote(target.split("#", 1)[0])
            if not file_target:
                continue
            resolved = (path.parent / file_target).resolve()
            try:
                resolved.relative_to(REPOSITORY_ROOT)
            except ValueError:
                error(f"Markdown 링크가 저장소 밖을 가리킵니다: {path.relative_to(ROOT)} -> {target}")
                continue
            if not resolved.exists():
                error(f"Markdown 링크 대상이 없습니다: {path.relative_to(ROOT)} -> {target}")


def check_yaml() -> None:
    for path in sorted([*repository_paths("*.yaml"), *repository_paths("*.yml")]):
        count()
        try:
            documents = list(yaml.safe_load_all(path.read_text(encoding="utf-8")))
        except (OSError, UnicodeError, yaml.YAMLError) as exc:
            error(f"YAML 형식이 올바르지 않습니다: {path.relative_to(ROOT)}: {exc}")
            continue
        if not documents or all(document is None for document in documents):
            error(f"YAML 문서가 비어 있습니다: {path.relative_to(ROOT)}")
        for document in documents:
            if document is not None and not isinstance(document, dict):
                error(f"YAML 최상위 값은 매핑이어야 합니다: {path.relative_to(ROOT)}")


def check_json() -> None:
    for path in sorted(repository_paths("*.json")):
        count()
        try:
            document = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, UnicodeError) as exc:
            error(f"JSON 형식이 올바르지 않습니다: {path.relative_to(ROOT)}: {exc}")
            continue
        if not isinstance(document, (dict, list)) or not document:
            error(f"JSON 최상위 값은 비어 있지 않은 매핑 또는 목록이어야 합니다: {path.relative_to(ROOT)}")


def check_csv() -> None:
    for path in sorted(repository_paths("*.csv")):
        count()
        try:
            with path.open(newline="", encoding="utf-8") as handle:
                rows = list(csv.reader(handle))
        except (OSError, UnicodeError, csv.Error) as exc:
            error(f"CSV를 읽을 수 없습니다: {path.relative_to(ROOT)}: {exc}")
            continue
        if len(rows) < 2 or not rows[0] or any(not cell.strip() for cell in rows[0]):
            error(f"CSV에는 header와 한 개 이상의 data row가 필요합니다: {path.relative_to(ROOT)}")
            continue
        width = len(rows[0])
        for line_no, row in enumerate(rows[1:], 2):
            if len(row) != width:
                error(f"CSV 열 수가 다릅니다: {path.relative_to(ROOT)}:{line_no}")


def check_shell() -> None:
    for path in sorted(repository_paths("*.sh")):
        run_check(f"shell syntax {path.relative_to(ROOT)}", ["sh", "-n", str(path)])
        mode = path.stat().st_mode
        if not mode & stat.S_IXUSR:
            error(f"셸 스크립트에 실행 권한이 없습니다: {path.relative_to(ROOT)}")
        text = path.read_text(encoding="utf-8")
        if "\r\n" in text or not text.endswith("\n"):
            error(f"셸 스크립트 줄바꿈이 올바르지 않습니다: {path.relative_to(ROOT)}")
        if re.search(r"\$\(\s*seq\b", text):
            error(f"POSIX 셸 검증기에서 seq 명령에 의존합니다: {path.relative_to(ROOT)}")


def check_python() -> None:
    for path in sorted(repository_paths("*.py")):
        count()
        try:
            source = path.read_text(encoding="utf-8")
            compile(source, str(path), "exec")
        except (SyntaxError, UnicodeError) as exc:
            error(f"Python 문법 검사에 실패했습니다: {path.relative_to(ROOT)}: {exc}")


def check_php() -> None:
    php = subprocess.run(["sh", "-c", "command -v php"], capture_output=True, text=True)
    paths = sorted(repository_paths("*.php"))
    if paths and php.returncode != 0:
        print("건너뜀: 호스트에 PHP CLI가 없어 Docker 실행 검사에서 PHP 예제를 확인합니다.")
        return
    for path in paths:
        run_check(f"PHP syntax {path.relative_to(ROOT)}", ["php", "-l", str(path)])


def check_secrets_and_generated_files() -> None:
    forbidden_names = {
        ".DS_Store",
        ".coverage",
        "before-verify.sh",
        "prepare-verify.sh",
        "tree.txt",
    }
    forbidden_suffixes = {".pyc", ".log", ".pid", ".crt", ".key"}
    for path in repository_paths("*"):
        count()
        relative = path.relative_to(ROOT)
        if path.name in forbidden_names:
            error(f"구형 또는 생성 파일 경로가 남아 있습니다: {relative}")
        if path.suffix in forbidden_suffixes:
            error(f"생성 파일을 배포 자료에 포함할 수 없습니다: {relative}")
        if path.is_file() and "secrets" in path.parts:
            if (
                path.suffix == ".txt"
                and not path.name.endswith(".txt.example")
                and not ALLOW_GENERATED_EXERCISE_STATE
            ):
                error(f"실제 비밀값처럼 보이는 파일을 배포 자료에 포함할 수 없습니다: {relative}")
        if path.is_file() and path.stat().st_size == 0:
            error(f"빈 파일입니다: {relative}")


def check_compose_conventions() -> None:
    for path in repository_paths("compose.yaml"):
        count()
        try:
            data = yaml.safe_load(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, yaml.YAMLError) as exc:
            error(f"Compose 파일을 읽거나 해석할 수 없습니다: {path.relative_to(ROOT)}: {exc}")
            continue
        if not isinstance(data, dict) or "services" not in data:
            error(f"Compose 파일에 services 매핑이 없습니다: {path.relative_to(ROOT)}")
            continue
        if "version" in data:
            error(f"Compose 파일에 더 이상 필요하지 않은 version 키가 있습니다: {path.relative_to(ROOT)}")
        services = data.get("services")
        if not isinstance(services, dict) or not services:
            error(f"Compose services 매핑은 비어 있을 수 없습니다: {path.relative_to(ROOT)}")
            continue
        if "/reference/" in f"/{path.relative_to(ROOT).as_posix()}/":
            for name, service in services.items():
                if not isinstance(service, dict):
                    continue
                if service.get("privileged") is True:
                    error(f"reference Compose 서비스는 privileged를 사용할 수 없습니다: {path.relative_to(ROOT)}:{name}")
                if service.get("network_mode") == "host":
                    error(f"reference Compose 서비스는 host network를 사용할 수 없습니다: {path.relative_to(ROOT)}:{name}")
                for volume in service.get("volumes", []) or []:
                    if isinstance(volume, str) and "/var/run/docker.sock" in volume:
                        error(f"reference Compose에서 Docker socket을 mount할 수 없습니다: {path.relative_to(ROOT)}:{name}")


def check_dockerfiles() -> None:
    for path in repository_paths("Dockerfile*"):
        if not path.is_file():
            continue
        count()
        text = path.read_text(encoding="utf-8")
        if not re.search(r"(?mi)^FROM(?:\s+--platform=\S+)?\s+\S+", text):
            error(f"Dockerfile에 FROM 명령이 없습니다: {path.relative_to(ROOT)}")
        if re.search(r"(?mi)^FROM(?:\s+--platform=\S+)?\s+\S+:latest(?:\s|$)", text):
            error(f"Dockerfile에서 latest 태그를 사용했습니다: {path.relative_to(ROOT)}")
        for instruction in ("CMD", "ENTRYPOINT"):
            for line_no, line in enumerate(text.splitlines(), 1):
                if re.match(rf"^{instruction}\s+", line) and not re.match(rf"^{instruction}\s+\[", line):
                    error(
                        f"{instruction}은 exec 형식으로 작성해야 합니다: "
                        f"{path.relative_to(ROOT)}:{line_no}"
                    )


def check_troubleshooting_scenario_inventory(directory: Path) -> None:
    expected = TROUBLESHOOTING_SCENARIOS
    checker = directory / "check-evidence.py"
    if checker.is_file():
        count()
        try:
            module = ast.parse(checker.read_text(encoding="utf-8"))
            checker_scenarios: object | None = None
            for node in module.body:
                if not isinstance(node, (ast.Assign, ast.AnnAssign)):
                    continue
                targets = node.targets if isinstance(node, ast.Assign) else [node.target]
                if any(
                    isinstance(target, ast.Name) and target.id == "SCENARIOS"
                    for target in targets
                ):
                    checker_scenarios = ast.literal_eval(node.value)
                    break
        except (OSError, UnicodeError, SyntaxError, ValueError) as exc:
            error(f"07 evidence scenario inventory를 읽을 수 없습니다: {exc}")
        else:
            if checker_scenarios != expected:
                error("07 evidence checker의 scenario inventory가 canonical 6개와 다릅니다.")

    def shell_loop_inventory(path: Path, label: str) -> None:
        count()
        if not path.is_file():
            error(f"07 scenario inventory 소유 파일이 없습니다: {path.relative_to(ROOT)}")
            return
        text = path.read_text(encoding="utf-8")
        match = re.search(
            r"(?ms)^[ \t]*for scenario in[ \t]*\\[ \t]*\n"
            r"(.*?)^[ \t]*do[ \t]*$",
            text,
        )
        values = (
            tuple(
                re.findall(
                    r"(?m)^[ \t]*([a-z0-9][a-z0-9-]*)"
                    r"[ \t]*(?:\\)?[ \t]*$",
                    match.group(1),
                )
            )
            if match
            else ()
        )
        if values != expected:
            error(f"{label}의 scenario inventory가 canonical 6개와 다릅니다.")

    shell_loop_inventory(directory / "verify.sh", "07 wrapper")
    shell_loop_inventory(ROOT / "scripts" / "cleanup-runtime.sh", "runtime cleanup")

    runner = directory / "run-scenario.sh"
    count()
    if not runner.is_file():
        error("07 scenario runner가 없습니다: exercises/07-troubleshooting/run-scenario.sh")
    else:
        runner_text = runner.read_text(encoding="utf-8")
        match = re.search(
            r'(?ms)^[ \t]*case "\$scenario" in[ \t]*\n'
            r"[ \t]*([^\n)]+)\)[ \t]*;;",
            runner_text,
        )
        values = tuple(match.group(1).split("|")) if match else ()
        if values != expected:
            error("07 scenario runner의 allowlist가 canonical 6개와 다릅니다.")


def check_exercise_contracts() -> None:
    for number, name in EXERCISES:
        directory = ROOT / "exercises" / f"{number:02d}-{name}"
        readme = directory / "README.md"
        if readme.is_file():
            markdown = readme.read_text(encoding="utf-8")
            sections: dict[str, str] = {}
            for heading in ("완료 기준", "자기 설명"):
                count()
                match = re.search(
                    rf"(?ms)^## {re.escape(heading)}\s*\n(.*?)(?=^## |\Z)",
                    markdown,
                )
                if match is None:
                    error(
                        f"exercise 학습 {heading}이 없습니다: "
                        f"{readme.relative_to(ROOT)}"
                    )
                    continue
                sections[heading] = match.group(1)

            completion = sections.get("완료 기준", "")
            count()
            if completion and len(re.findall(r"(?m)^- \[ \] ", completion)) < 3:
                error(
                    f"exercise 완료 기준은 확인 가능한 체크리스트 3개 이상이어야 합니다: "
                    f"{readme.relative_to(ROOT)}"
                )

            explanation = sections.get("자기 설명", "")
            count()
            if explanation and len(re.findall(r"(?m)^\d+\. ", explanation)) < 2:
                error(
                    f"exercise 자기 설명에는 설명 질문이 2개 이상이어야 합니다: "
                    f"{readme.relative_to(ROOT)}"
                )

        if number != 7:
            for implementation in ("skeleton", "reference"):
                count()
                target = directory / implementation
                if not target.is_dir() or not any(target.iterdir()):
                    error(f"exercise {number:02d}의 {implementation}이 없거나 비어 있습니다.")
        wrapper = directory / "verify.sh"
        if wrapper.is_file() and number != 7:
            text = wrapper.read_text(encoding="utf-8")
            for mode in ("skeleton", "workspace", "reference"):
                count()
                if mode not in text:
                    error(
                        f"exercise wrapper가 {mode} mode를 제공하지 않습니다: "
                        f"{wrapper.relative_to(ROOT)}"
                    )
            count()
            if not re.search(r"\$\{1:-workspace\}", text):
                error(
                    f"exercise wrapper 기본 mode는 workspace여야 합니다: "
                    f"{wrapper.relative_to(ROOT)}"
                )
            count()
            if "skeleton|workspace|reference" not in text:
                error(
                    f"exercise wrapper의 mode allowlist가 canonical 순서와 다릅니다: "
                    f"{wrapper.relative_to(ROOT)}"
                )
            count()
            if "내부 symlink를 허용하지 않습니다" not in text:
                error(
                    f"exercise wrapper가 workspace 내부 symlink를 거부하지 않습니다: "
                    f"{wrapper.relative_to(ROOT)}"
                )

        if number == 7:
            count()
            if not (directory / "template" / "evidence.md").is_file():
                error("07 분석 실습의 evidence template이 없습니다.")
            count()
            if not (directory / "check-evidence.py").is_file():
                error("07 분석 실습의 evidence checker가 없습니다.")
            text = wrapper.read_text(encoding="utf-8") if wrapper.is_file() else ""
            count()
            if not re.search(r"\$\{1:-workspace\}", text):
                error("07 분석 실습 wrapper 기본 mode는 workspace여야 합니다.")
            mode_case = re.search(
                r'(?ms)^[ \t]*case "\$mode" in[ \t]*\n(.*?)^[ \t]*esac[ \t]*$',
                text,
            )
            branch_labels = (
                re.findall(
                    r"(?m)^[ \t]+([^\s)\n][^)\n]*)\)[ \t]*$",
                    mode_case.group(1),
                )
                if mode_case
                else []
            )
            modes = [
                mode
                for label in branch_labels
                for mode in label.split("|")
                if mode != "*"
            ]
            count()
            if len(modes) != 3 or set(modes) != {"workspace", "template", "scenarios"}:
                error("07 분석 실습 wrapper mode allowlist가 canonical 3개와 다릅니다.")
            count()
            if "workspace symlink를 허용하지 않습니다" not in text:
                error("07 분석 실습 wrapper가 workspace symlink를 거부하지 않습니다.")
            count()
            if "workspace 내부 symlink를 허용하지 않습니다" not in text:
                error("07 분석 실습 wrapper가 workspace 내부 symlink를 거부하지 않습니다.")
            checker = directory / "check-evidence.py"
            template = directory / "template" / "evidence.md"
            if checker.is_file() and template.is_file():
                run_check(
                    "07 evidence template",
                    [sys.executable, "-B", str(checker), "--template", str(template)],
                )
                run_check(
                    "07 evidence checker self-test",
                    [sys.executable, "-B", str(checker), "--self-test"],
                )
            check_troubleshooting_scenario_inventory(directory)

    for path in repository_paths("*"):
        if not path.is_file() or "reference" not in path.parts:
            continue
        if path.suffix.lower() not in {".py", ".sh", ".yaml", ".yml", ".json", ".php", ".conf", ""}:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        if re.search(r"\bTODO\b|NotImplementedError", text):
            error(f"reference 구현에 미완성 표식이 남아 있습니다: {path.relative_to(ROOT)}")


def check_workspace_contract() -> None:
    generator = ROOT / "scripts" / "new-workspace.py"
    count()
    if not generator.is_file():
        return
    try:
        module = ast.parse(generator.read_text(encoding="utf-8"))
        mapping: object | None = None
        for node in module.body:
            if not isinstance(node, (ast.Assign, ast.AnnAssign)):
                continue
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            if any(isinstance(target, ast.Name) and target.id == "EXERCISE_SOURCES" for target in targets):
                mapping = ast.literal_eval(node.value)
                break
    except (OSError, UnicodeError, SyntaxError, ValueError) as exc:
        error(f"workspace generator mapping을 읽을 수 없습니다: {exc}")
        return

    expected = {
        f"exercises/{number:02d}-{name}": "template" if number == 7 else "skeleton"
        for number, name in EXERCISES
    }
    count()
    if mapping != expected:
        error("workspace generator의 exercise/source mapping이 canonical 18개 실습과 다릅니다.")

    gitignore = (ROOT / ".gitignore").read_text(encoding="utf-8")
    for item in (
        "exercises/*/workspace/",
        "exercises/*/.workspace.lock",
        "exercises/*/.workspace.tmp.*/",
    ):
        count()
        if item not in gitignore:
            error(f"learner runtime state가 .gitignore에 없습니다: {item}")


def check_learning_mapping() -> None:
    readme_path = ROOT / "README.md"
    if not readme_path.is_file():
        return
    text = readme_path.read_text(encoding="utf-8")
    match = re.search(
        r"(?ms)^### 문서에서 다음 단계까지\s*\n(.*?)(?=^## |\Z)", text
    )
    count()
    if match is None:
        error("README에 canonical ordered learning mapping이 없습니다.")
        return

    rows: dict[int, tuple[str, list[str]]] = {}
    for line in match.group(1).splitlines():
        row = re.match(r"^\|\s*(\d{2})\s*\|", line)
        if row is None:
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        number = int(row.group(1))
        if number in rows:
            error(f"README learning mapping에 순서가 중복됩니다: {number:02d}")
        rows[number] = (line, cells)

    count()
    if sorted(rows) != list(range(1, 19)):
        error("README learning mapping은 01–18 행을 정확히 한 번씩 가져야 합니다.")

    docs_by_number = {
        number: f"docs/{number:02d}-{name}.md"
        for number, name in DOCS
        if number
    }
    exercises_by_number = {
        number: f"exercises/{number:02d}-{name}"
        for number, name in EXERCISES
    }
    for number in range(1, 19):
        if number not in rows:
            continue
        line, cells = rows[number]
        count()
        if len(cells) != 7:
            error(f"README learning mapping {number:02d}행은 7개 의미 열이어야 합니다.")
        workspace_fragment = (
            f"{exercises_by_number[number]}/workspace/evidence.md"
            if number == 7
            else f"{exercises_by_number[number]}/workspace/"
        )
        required = (
            docs_by_number[number],
            f"{exercises_by_number[number]}/README.md",
            workspace_fragment,
            f"{exercises_by_number[number]}/verify.sh workspace",
        )
        for fragment in required:
            count()
            if fragment not in line:
                error(f"README learning mapping {number:02d}행에 경로가 없습니다: {fragment}")
        count()
        if number != 7 and f"{exercises_by_number[number]}/reference/" not in line:
            error(f"README learning mapping {number:02d}행에 완료 뒤 reference가 없습니다.")
        count()
        if "→" not in line or (number == 18 and "종료" not in line):
            error(f"README learning mapping {number:02d}행에 다음 단계 또는 종료가 없습니다.")


def check_implementation_annotations() -> None:
    prefix = "[" + "Implementation "
    marker = re.compile(re.escape(prefix) + r"(\d+)(?:-(\d+))?\]")
    any_marker = re.compile(re.escape(prefix) + r"([^\]]+)\]")
    marker_by_scope: dict[int, list[tuple[tuple[int, int | None], Path]]] = {
        number: [] for number, _name in EXERCISES if number != 7
    }
    sidecar_scopes = {8, 17, 18}
    bootstrap_scopes = {4, 5, 6}
    exercise_names = {number: name for number, name in EXERCISES}

    def coordinate(found: re.Match[str]) -> tuple[int, int | None]:
        child = found.group(2)
        return int(found.group(1)), int(child) if child is not None else None

    def coordinate_key(value: tuple[int, int | None]) -> tuple[int, int]:
        major, child = value
        return major, -1 if child is None else child

    def coordinates(text: str) -> list[tuple[int, int | None]]:
        return [coordinate(found) for found in marker.finditer(text)]

    for path in repository_paths("*"):
        if not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeError):
            continue
        matches = list(marker.finditer(text))
        all_matches = list(any_marker.finditer(text))
        if not all_matches:
            continue
        relative = path.relative_to(ROOT)
        count()
        if len(matches) != len(all_matches):
            error(f"지원하지 않는 Implementation 번호 형식입니다: {relative}")
        exercise_number = None
        if len(relative.parts) >= 2 and relative.parts[0] == "exercises":
            match_number = re.match(r"^(\d{2})-", relative.parts[1])
            if match_number:
                exercise_number = int(match_number.group(1))
        if exercise_number is None or exercise_number == 7:
            error(f"Implementation annotation이 허용되지 않는 경로에 있습니다: {relative}")
            continue

        exercise = ROOT / "exercises" / f"{exercise_number:02d}-{exercise_names[exercise_number]}"
        readme = exercise / "README.md"
        reference = exercise / "reference"
        if path == readme:
            if exercise_number not in bootstrap_scopes | sidecar_scopes:
                error(f"source-owned scope의 README가 exact annotation을 소유합니다: {relative}")
        else:
            try:
                path.relative_to(reference)
            except ValueError:
                error(f"Implementation annotation은 reference 또는 owning README에만 허용됩니다: {relative}")
            if exercise_number in sidecar_scopes:
                error(f"expected-evidence YAML scope는 README walkthrough만 annotation을 소유합니다: {relative}")

        for found in matches:
            marker_by_scope[exercise_number].append((coordinate(found), path))
            line = text[: found.start()].count("\n") + 1
            marker_line = text.splitlines()[line - 1].lstrip()
            count()
            if not marker_line.startswith(("#", "//", ";", "--", "|")):
                error(f"Implementation annotation이 comment/walkthrough가 아닙니다: {relative}:{line}")

    for number, markers in marker_by_scope.items():
        exercise = ROOT / "exercises" / f"{number:02d}-{exercise_names[number]}"
        readme = exercise / "README.md"
        readme_text = readme.read_text(encoding="utf-8") if readme.is_file() else ""
        heading = "권장 작성 순서" if number in sidecar_scopes else "권장 구현 순서"
        section = re.search(
            rf"(?ms)^## {re.escape(heading)}\s*\n(.*?)(?=^## |\Z)",
            readme_text,
        )
        count()
        if section is None:
            error(f"exercise {number:02d}에 {heading} walkthrough가 없습니다.")

        readme_markers = list(marker.finditer(readme_text))
        count()
        if section is not None and any(
            not (section.start() <= found.start() < section.end())
            for found in readme_markers
        ):
            error(
                f"exercise {number:02d} README exact annotation은 "
                f"{heading} section 안에만 있어야 합니다."
            )

        values = [value for value, _path in markers]
        start = 0 if number in bootstrap_scopes else 1
        count()
        if not values:
            error(f"exercise {number:02d} reference scope에 Implementation annotation이 없습니다.")
            continue
        count()
        if len(values) != len(set(values)):
            error(f"exercise {number:02d} Implementation 번호가 중복됩니다.")

        top_level = sorted(major for major, child in set(values) if child is None)
        count()
        if not top_level or top_level != list(range(start, max(top_level) + 1)):
            error(
                f"exercise {number:02d} Implementation top-level 번호가 "
                f"{start}부터 연속되지 않습니다."
            )

        value_set = set(values)
        for major, child in sorted(value_set, key=coordinate_key):
            if child is None:
                continue
            count()
            if (major, None) not in value_set:
                error(
                    f"exercise {number:02d} Implementation {major}-{child}의 "
                    "parent top-level 번호가 없습니다."
                )

        child_parents = sorted({major for major, child in value_set if child is not None})
        for major in child_parents:
            children = sorted(
                child
                for candidate_major, child in value_set
                if candidate_major == major and child is not None
            )
            count()
            if children != list(range(1, max(children) + 1)):
                error(
                    f"exercise {number:02d} Implementation {major}의 child 번호가 "
                    "1부터 연속되지 않습니다."
                )

        if number in bootstrap_scopes:
            readme_coordinates = coordinates(readme_text)
            count()
            if readme_coordinates.count((0, None)) != 1:
                error(f"exercise {number:02d}의 Implementation 0은 README에 정확히 한 번 있어야 합니다.")
            count()
            if readme_coordinates != [(0, None)]:
                error(f"exercise {number:02d} README는 Implementation 0만 소유해야 합니다.")
        if number in sidecar_scopes:
            count()
            if any(path != readme for _value, path in markers):
                error(f"exercise {number:02d} expected evidence annotation은 README만 소유해야 합니다.")
        if number not in sidecar_scopes:
            bracketless = (
                [
                    (int(major), int(child) if child else None)
                    for major, child in re.findall(
                        r"(?m)^\| (\d+)(?:-(\d+))? \|",
                        section.group(1),
                    )
                ]
                if section
                else []
            )
            source_coordinates = sorted(
                (value for value, owner in markers if owner != readme),
                key=coordinate_key,
            )
            count()
            if bracketless != source_coordinates:
                error(f"exercise {number:02d} README 구현 순서가 source annotation과 다릅니다.")


def check_repository_contract() -> None:
    documents = {
        "README.md": ("./prepare.sh", "./verify.sh"),
        "docs/00-roadmap.md": ("./prepare.sh", "./verify.sh"),
        "CONTRIBUTING.md": ("./prepare.sh", "./verify.sh"),
    }
    document_texts: dict[str, str] = {}
    for relative, commands in documents.items():
        path = ROOT / relative
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8")
        document_texts[relative] = text
        for command in commands:
            count()
            if command not in text:
                error(f"정식 실행 명령이 문서에 없습니다: {relative}: {command}")

    readme = document_texts.get("README.md", "")
    if "python3 -m pip install -r scripts/requirements.txt" in readme:
        error("README가 prepare.sh 대신 전역 Python 의존성 설치를 안내합니다.")

    root_verify = ROOT / "verify.sh"
    count()
    if root_verify.is_file() and 'if [ "$#" -ne 0 ]' not in root_verify.read_text(encoding="utf-8"):
        error("root verify.sh가 예상하지 못한 learner mode 인자를 거부하지 않습니다.")

    makefile_path = ROOT / "Makefile"
    makefile = makefile_path.read_text(encoding="utf-8") if makefile_path.is_file() else ""
    count()
    if "PREPARED_PYTHON := .verify/venv/bin/python" not in makefile:
        error("Makefile이 prepare.sh의 고정 Python 환경을 기본으로 사용하지 않습니다.")
    for target in (
        "prepare",
        "check",
        "static",
        "meta",
        "verify",
        "verify-foundations",
        "verify-production",
        "verify-repeatability",
        "workspace-check",
        "evidence-check",
        "clean",
    ):
        count()
        if not re.search(rf"(?m)^{re.escape(target)}\s*:", makefile):
            error(f"Makefile target이 없습니다: {target}")

    requirements_path = ROOT / "scripts" / "requirements.txt"
    requirements = requirements_path.read_text(encoding="utf-8").strip() if requirements_path.is_file() else ""
    if requirements and requirements != "PyYAML==6.0.3":
        error("검증 의존성은 PyYAML==6.0.3으로 고정해야 합니다.")

    gitignore_path = ROOT / ".gitignore"
    gitignore = gitignore_path.read_text(encoding="utf-8") if gitignore_path.is_file() else ""
    for item in (
        ".verify/",
        "make-out.txt",
        "exercises/*/workspace/",
        "exercises/*/.workspace.lock",
        "exercises/*/.workspace.tmp.*/",
    ):
        count()
        if item not in gitignore:
            error(f"검증 상태가 .gitignore에 없습니다: {item}")

    for wrapper in sorted((ROOT / "exercises").glob("*/verify.sh")):
        text = wrapper.read_text(encoding="utf-8")
        if "python3" in text and "${PYTHON:-python3}" not in text:
            error(f"exercise wrapper가 prepare.sh의 Python 환경을 사용하지 않습니다: {wrapper.relative_to(ROOT)}")

    prepare_text = (ROOT / "prepare.sh").read_text(encoding="utf-8") if (ROOT / "prepare.sh").is_file() else ""
    verify_text = (ROOT / "verify.sh").read_text(encoding="utf-8") if (ROOT / "verify.sh").is_file() else ""
    cleanup_text = (ROOT / "scripts/cleanup-runtime.sh").read_text(encoding="utf-8") if (ROOT / "scripts/cleanup-runtime.sh").is_file() else ""
    for owner, owner_text, fragments in (
        ("prepare.sh", prepare_text, ("preparation_sha256", "prepared.json", "default-load=true")),
        ("verify.sh", verify_text, ("preparation_sha256", "ISOLATED WORKTREE", "assert-clean")),
        ("scripts/cleanup-runtime.sh", cleanup_text, ("buildx_buildkit_", "assert-clean", "docker volume rm")),
    ):
        for fragment in fragments:
            count()
            if fragment not in owner_text:
                error(f"준비·검증·정리 계약이 없습니다: {owner}: {fragment}")

    readme_path = ROOT / "README.md"
    roadmap_path = ROOT / "docs/00-roadmap.md"
    readme_text = document_texts.get("README.md", "")
    roadmap_text = document_texts.get("docs/00-roadmap.md", "")
    for number, name in DOCS:
        relative = f"docs/{number:02d}-{name}.md"
        filename = relative.split("docs/", 1)[-1]
        count()
        if filename not in readme_text:
            error(f"학습 지도에 문서 링크가 없습니다: README.md -> {relative}")
        # roadmap 자체가 자기 파일명까지 반복할 필요는 없습니다.
        if number != 0:
            count()
            if filename not in roadmap_text:
                error(f"학습 지도에 문서 링크가 없습니다: docs/00-roadmap.md -> {relative}")

    for number, name in EXERCISES:
        relative = f"exercises/{number:02d}-{name}"
        for owner, owner_text in ((readme_path, readme_text), (roadmap_path, roadmap_text)):
            count()
            if owner_text and relative not in owner_text:
                error(f"학습 지도에 exercise 링크가 없습니다: {owner.relative_to(ROOT)} -> {relative}")

    runbook_path = ROOT / "docs/runbooks/00-index.md"
    if runbook_path.is_file():
        runbook_index = runbook_path.read_text(encoding="utf-8")
        for runbook in RUNBOOKS[1:]:
            count()
            if f"{runbook}.md" not in runbook_index:
                error(f"runbook 색인에 문서가 없습니다: {runbook}.md")


def main() -> int:
    parse_args()
    require_files()
    check_top_level_layout()
    check_markdown()
    check_yaml()
    check_json()
    check_csv()
    check_shell()
    check_python()
    check_php()
    check_secrets_and_generated_files()
    check_compose_conventions()
    check_dockerfiles()
    check_exercise_contracts()
    check_workspace_contract()
    check_learning_mapping()
    check_implementation_annotations()
    check_repository_contract()

    if ERRORS:
        print(f"정적 검사 실패: {len(ERRORS)}건", file=sys.stderr)
        for item in ERRORS:
            print(f"- {item}", file=sys.stderr)
        return 1
    print(f"정적 검사 통과: {CHECKS}개 항목")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
