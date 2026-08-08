#!/usr/bin/env python3
"""Install an implementation and verify it without source-path injection."""

from __future__ import annotations

import argparse
import base64
import csv
import hashlib
import importlib.util
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXERCISE = ROOT / "exercises" / "command-checker"


def fail(message: str, result: subprocess.CompletedProcess[str] | None = None) -> None:
    print(f"PACKAGE CHECK: FAIL: {message}", file=sys.stderr)
    if result is not None:
        print(result.stdout, file=sys.stderr, end="")
        print(result.stderr, file=sys.stderr, end="")
    raise SystemExit(1)


def run(
    command: list[str],
    *,
    cwd: Path,
    environment: dict[str, str],
    timeout: float = 90,
) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            command,
            cwd=cwd,
            env=environment,
            text=True,
            capture_output=True,
            timeout=timeout,
            check=False,
        )
    except (OSError, subprocess.SubprocessError) as error:
        fail(f"명령을 실행하지 못했습니다: {command[0]}: {error}")


def implementation_root(arguments: argparse.Namespace) -> Path:
    override = arguments.implementation_root or os.environ.get("EXERCISE_IMPL_ROOT")
    if override:
        root = Path(override).resolve()
    else:
        implementation = os.environ.get("EXERCISE_IMPL", arguments.implementation)
        if implementation not in {"reference", "skeleton", "workspace"}:
            fail(f"지원하지 않는 EXERCISE_IMPL: {implementation}")
        root = (EXERCISE / implementation).resolve()
    if not root.is_dir():
        fail(f"구현 디렉터리가 없습니다: {root}")
    return root


def validate_project(project_root: Path) -> str:
    pyproject_path = project_root / "pyproject.toml"
    try:
        data = tomllib.loads(pyproject_path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError) as error:
        fail(f"pyproject.toml을 읽을 수 없습니다: {error}")
    build = data.get("build-system", {})
    project = data.get("project", {})
    scripts = project.get("scripts", {})
    type_contract = data.get("tool", {}).get("command-checker", {}).get("type-contract", {})
    expected = {
        "name": "command-checker",
        "requires-python": ">=3.12",
        "dependencies": [],
    }
    for key, value in expected.items():
        if project.get(key) != value:
            fail(f"project.{key} 계약이 다릅니다: {project.get(key)!r}")
    if not isinstance(project.get("version"), str) or not project["version"]:
        fail("project.version이 비어 있습니다.")
    if scripts != {"command-checker": "command_checker.cli:main"}:
        fail("project.scripts의 command-checker 진입점이 정확하지 않습니다.")
    if build != {
        "requires": [],
        "build-backend": "_command_checker_build",
        "backend-path": ["."],
    }:
        fail("외부 의존성 없는 in-tree build backend 계약이 다릅니다.")
    if type_contract != {
        "require-annotations": True,
        "disallow-any-in-public-api": True,
    }:
        fail("정적 공개 타입 계약 설정이 다릅니다.")
    if not (project_root / "command_checker" / "py.typed").is_file():
        fail("typed package marker인 command_checker/py.typed가 없습니다.")
    return project["version"]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--implementation",
        choices=("reference", "skeleton", "workspace"),
        default="reference",
    )
    parser.add_argument("--implementation-root", type=Path)
    parser.add_argument("--entrypoint-only", action="store_true")
    arguments = parser.parse_args()
    project_root = implementation_root(arguments)
    expected_version = validate_project(project_root)
    expected_package_files = sorted(
        f"command_checker/{path.name}"
        for path in (project_root / "command_checker").iterdir()
        if path.is_file() and (path.suffix == ".py" or path.name == "py.typed")
    )
    expected_modules = sorted(
        Path(relative).stem
        for relative in expected_package_files
        if relative.endswith(".py")
        and not relative.endswith(("/__init__.py", "/__main__.py"))
    )
    expected_cache_files = {
        importlib.util.cache_from_source(relative)
        for relative in expected_package_files
        if relative.endswith(".py")
    }

    with tempfile.TemporaryDirectory(prefix="guide-command-checker-install-") as directory:
        temporary = Path(directory)
        venv = temporary / "venv"
        probe = temporary / "outside-source"
        build_source = temporary / "build-source"
        probe.mkdir()
        shutil.copytree(project_root, build_source)
        environment = os.environ.copy()
        for name in ("PYTHONHOME", "PYTHONPATH", "EXERCISE_IMPL", "EXERCISE_IMPL_ROOT"):
            environment.pop(name, None)
        environment.update({
            "PIP_DISABLE_PIP_VERSION_CHECK": "1",
            "PIP_NO_INDEX": "1",
            "PYTHONDONTWRITEBYTECODE": "1",
        })

        created = run([sys.executable, "-B", "-m", "venv", str(venv)], cwd=probe, environment=environment)
        if created.returncode:
            fail("격리 설치용 venv를 만들지 못했습니다.", created)
        venv = venv.resolve()
        python = venv / "bin" / "python"
        console = venv / "bin" / "command-checker"
        installed = run(
            [
                str(python), "-B", "-m", "pip", "install",
                "--disable-pip-version-check", "--no-cache-dir", "--no-index",
                "--no-deps", "--no-build-isolation", str(build_source),
            ],
            cwd=probe,
            environment=environment,
        )
        if installed.returncode:
            fail("wheel 설치에 실패했습니다.", installed)
        shutil.rmtree(build_source)
        if not console.is_file() or not os.access(console, os.X_OK):
            fail("설치된 command-checker console script가 없습니다.")

        metadata_code = f"""
import importlib
import importlib.metadata as metadata
import json
import os
from pathlib import Path
import sys

forbidden_roots = [
    Path(value).resolve()
    for value in {json.dumps([str(project_root), str(build_source)])}
]
installed_root = Path({str(venv)!r}).resolve()

def reject_source_access(event, arguments):
    candidate = None
    if event == "open" and arguments and isinstance(arguments[0], (str, bytes)):
        candidate = Path(os.fsdecode(arguments[0]))
    elif event == "compile" and len(arguments) > 1 and isinstance(arguments[1], (str, bytes)):
        candidate = Path(os.fsdecode(arguments[1]))
    if candidate is None or not candidate.is_absolute():
        return
    resolved = candidate.resolve()
    for root in forbidden_roots:
        try:
            resolved.relative_to(root)
        except ValueError:
            continue
        raise RuntimeError(f"installed package accessed source path: {{resolved}}")
    if resolved.suffix in {{".py", ".pyc"}} and "command_checker" in resolved.parts:
        try:
            resolved.relative_to(installed_root)
        except ValueError:
            raise RuntimeError(f"installed package executed external Python source: {{resolved}}")

sys.addaudithook(reject_source_access)
import command_checker
distribution = metadata.distribution("command-checker")
entry_points = {{
    entry.name: entry.value
    for entry in distribution.entry_points
    if entry.group == "console_scripts"
}}
expected_modules = {json.dumps(expected_modules)}
module_files = {{
    name: str(Path(importlib.import_module(f"command_checker.{{name}}").__file__).resolve())
    for name in expected_modules
}}
distribution_files = [str(path) for path in distribution.files or ()]
locations = {{
    relative: str(Path(distribution.locate_file(relative)).resolve())
    for relative in {json.dumps(expected_package_files)}
}}
print(json.dumps({{
    "module": str(Path(command_checker.__file__).resolve()),
    "package_paths": [str(Path(path).resolve()) for path in command_checker.__path__],
    "module_files": module_files,
    "distribution_files": distribution_files,
    "locations": locations,
    "record": distribution.read_text("RECORD"),
    "version": distribution.version,
    "package_version": command_checker.__version__,
    "entrypoint": entry_points.get("command-checker"),
    "typed": (Path(command_checker.__file__).parent / "py.typed").is_file(),
}}))
"""
        metadata_result = run(
            [str(python), "-I", "-B", "-c", metadata_code],
            cwd=probe,
            environment=environment,
        )
        if metadata_result.returncode:
            fail("설치된 package import/metadata 검사에 실패했습니다.", metadata_result)
        try:
            metadata = json.loads(metadata_result.stdout)
        except json.JSONDecodeError:
            fail("설치 metadata probe가 JSON을 반환하지 않았습니다.", metadata_result)
        installed_paths = [metadata.get("module")]
        installed_paths.extend(metadata.get("package_paths", []))
        installed_paths.extend(metadata.get("module_files", {}).values())
        installed_paths.extend(metadata.get("locations", {}).values())
        try:
            for raw_path in installed_paths:
                Path(raw_path).resolve().relative_to(venv)
        except (TypeError, ValueError):
            fail("설치 package의 경로가 격리 venv 밖 source를 가리킵니다.", metadata_result)

        distribution_package_files = {
            relative
            for relative in metadata.get("distribution_files", [])
            if relative.startswith("command_checker/")
        }
        installed_cache_files = {
            relative
            for relative in distribution_package_files
            if "/__pycache__/" in relative
        }
        if not installed_cache_files <= expected_cache_files:
            fail("설치 과정에서 예상하지 않은 Python cache 파일이 생겼습니다.", metadata_result)
        installed_package_files = {
            relative
            for relative in distribution_package_files
            if "/__pycache__/" not in relative
        }
        if installed_package_files != set(expected_package_files):
            fail(
                "설치 distribution의 command_checker 파일 목록이 source 계약과 다릅니다.",
                metadata_result,
            )
        required_metadata = {"METADATA", "WHEEL", "entry_points.txt", "RECORD"}
        installed_metadata = {
            Path(relative).name
            for relative in metadata.get("distribution_files", [])
            if ".dist-info/" in relative
        }
        if not required_metadata <= installed_metadata:
            fail("설치 distribution metadata/RECORD가 불완전합니다.", metadata_result)

        try:
            rows = {
                row[0]: row[1:]
                for row in csv.reader(io.StringIO(metadata["record"]))
                if len(row) == 3
            }
        except (KeyError, TypeError):
            fail("설치 distribution의 RECORD를 읽지 못했습니다.", metadata_result)
        for relative in expected_package_files:
            location = Path(metadata["locations"][relative])
            record = rows.get(relative)
            if record is None or not location.is_file():
                fail(f"RECORD 또는 설치 파일이 누락되었습니다: {relative}", metadata_result)
            digest_field, size_field = record
            try:
                algorithm, encoded = digest_field.split("=", 1)
                expected_digest = base64.urlsafe_b64decode(
                    encoded + "=" * (-len(encoded) % 4)
                )
                actual_digest = hashlib.new(algorithm, location.read_bytes()).digest()
                expected_size = int(size_field)
            except (OSError, ValueError):
                fail(f"RECORD hash/size 형식이 잘못되었습니다: {relative}", metadata_result)
            if actual_digest != expected_digest or location.stat().st_size != expected_size:
                fail(f"RECORD hash/size가 설치 파일과 다릅니다: {relative}", metadata_result)
        if metadata.get("version") != expected_version:
            fail("설치 metadata version과 pyproject version이 다릅니다.", metadata_result)
        if metadata.get("package_version") != expected_version:
            fail("package __version__과 pyproject version이 다릅니다.", metadata_result)
        if metadata.get("entrypoint") != "command_checker.cli:main" or not metadata.get("typed"):
            fail("설치된 console entry point 또는 py.typed marker가 다릅니다.", metadata_result)

        help_result = run([str(console), "--help"], cwd=probe, environment=environment)
        if help_result.returncode or "command-checker" not in help_result.stdout or "--cases" not in help_result.stdout:
            fail("설치된 console script의 도움말 계약이 다릅니다.", help_result)
        module_help = run(
            [str(python), "-I", "-B", "-m", "command_checker", "--help"],
            cwd=probe,
            environment=environment,
        )
        if (
            module_help.returncode
            or "command-checker" not in module_help.stdout
            or "--cases" not in module_help.stdout
        ):
            fail("설치된 python -m command_checker 도움말 계약이 다릅니다.", module_help)

        audited_help_code = metadata_code.split("import command_checker\n", 1)[0] + """
from command_checker.cli import main
try:
    status = main(["--help"])
except SystemExit as error:
    status = error.code
raise SystemExit(status)
"""
        audited_help = run(
            [str(python), "-I", "-B", "-c", audited_help_code],
            cwd=probe,
            environment=environment,
        )
        if (
            audited_help.returncode
            or "command-checker" not in audited_help.stdout
            or "--cases" not in audited_help.stdout
        ):
            fail("설치 package의 source 격리 도움말 검사가 실패했습니다.", audited_help)

        if not arguments.entrypoint_only:
            cases = EXERCISE / "fixtures" / "sort-cases.json"
            target = EXERCISE / "fixtures" / "line-sort.py"
            functional = run(
                [str(console), "--cases", str(cases), "--", sys.executable, str(target)],
                cwd=probe,
                environment=environment,
            )
            if functional.returncode or "요약: 통과 2건, 실패 0건" not in functional.stdout:
                fail("설치된 console script의 종단 간 실행이 실패했습니다.", functional)
            audited_e2e_code = metadata_code.split("import command_checker\n", 1)[0] + f"""
from command_checker.cli import main
raise SystemExit(main({json.dumps([
    "--cases", str(cases), "--", sys.executable, str(target),
])}))
"""
            audited_functional = run(
                [str(python), "-I", "-B", "-c", audited_e2e_code],
                cwd=probe,
                environment=environment,
            )
            if (
                audited_functional.returncode
                or "요약: 통과 2건, 실패 0건" not in audited_functional.stdout
            ):
                fail("설치 package의 source 격리 종단 간 검사가 실패했습니다.", audited_functional)

    mode = "entrypoint" if arguments.entrypoint_only else "install/import/entrypoint/e2e"
    print(f"PACKAGE CHECK: PASS ({mode}, no source-path injection)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
