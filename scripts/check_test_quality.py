#!/usr/bin/env python3
"""Known-bad mutations must be rejected by exercise and project checks."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXERCISE = ROOT / "exercises" / "command-checker"
REFERENCE = EXERCISE / "reference"
TESTS = EXERCISE / "tests"


@dataclass(frozen=True, slots=True)
class Mutation:
    name: str
    path: str
    before: str
    after: str
    pattern: str
    expected_test: str


@dataclass(frozen=True, slots=True)
class ProjectMutation:
    name: str
    path: str
    before: str
    after: str
    checker: str
    expected_output: str
    additional_edits: tuple[tuple[str, str, str], ...] = ()


MUTATIONS = (
    Mutation(
        name="stderr comparison removed",
        path="command_checker/comparison.py",
        before="if stderr != case.stderr:",
        after="if False and stderr != case.stderr:",
        pattern="test_stage_03_*.py",
        expected_test="test_three_channels_are_compared_independently",
    ),
    Mutation(
        name="boolean timeout accepted",
        path="command_checker/specification.py",
        before="if isinstance(timeout, bool) or not isinstance(timeout, (int, float)):",
        after="if not isinstance(timeout, (int, float)):",
        pattern="test_stage_04_*.py",
        expected_test="test_bool_is_not_a_numeric_timeout_or_limit",
    ),
    Mutation(
        name="absolute cwd accepted",
        path="command_checker/specification.py",
        before="if not cwd_text or cwd_path.is_absolute():",
        after="if not cwd_text:",
        pattern="test_stage_04_*.py",
        expected_test="test_cwd_is_a_nonempty_relative_path_from_the_cases_file",
    ),
    Mutation(
        name="cwd resolved from invocation directory",
        path="command_checker/specification.py",
        before="cwd = (base / cwd_path).resolve()",
        after="cwd = cwd_path.resolve()",
        pattern="test_stage_04_*.py",
        expected_test="test_cwd_is_a_nonempty_relative_path_from_the_cases_file",
    ),
    Mutation(
        name="normalized executable identity discarded by resolver",
        path="command_checker/runner.py",
        before="return str(path)",
        after="return command",
        pattern="test_stage_06_*.py",
        expected_test="test_executable_is_selected_once_before_case_context",
    ),
    Mutation(
        name="normalized executable identity discarded by CLI",
        path="command_checker/cli.py",
        before="command = (executable, *arguments.command[1:])",
        after="command = tuple(arguments.command)",
        pattern="test_stage_06_*.py",
        expected_test="test_executable_is_selected_once_before_case_context",
    ),
    Mutation(
        name="output limit disabled",
        path="command_checker/process.py",
        before="if len(chunk) > remaining_capacity:",
        after="if False and len(chunk) > remaining_capacity:",
        pattern="test_stage_07_*.py",
        expected_test="test_stdout_and_stderr_limits_stop_collection",
    ),
    Mutation(
        name="parallel result order reversed",
        path="command_checker/runner.py",
        before="return tuple(executor.map(lambda case: run_case(case, command), cases))",
        after=(
            "return tuple(reversed(tuple(executor.map("
            "lambda case: run_case(case, command), cases))))"
        ),
        pattern="test_stage_08_*.py",
        expected_test="test_parallel_completion_keeps_input_order",
    ),
    Mutation(
        name="parallel execution collapsed to sequential",
        path="command_checker/runner.py",
        before="if jobs == 1:",
        after="if jobs >= 1:",
        pattern="test_stage_08_*.py",
        expected_test="test_parallel_completion_keeps_input_order",
    ),
    Mutation(
        name="invalid XML controls preserved",
        path="command_checker/reports.py",
        before='else "\\uFFFD"',
        after="else character",
        pattern="test_stage_08_*.py",
        expected_test="test_junit_replaces_invalid_xml_control_characters",
    ),
    Mutation(
        name="forbidden reports-to-specification dependency",
        path="command_checker/reports.py",
        before="from .model import Result",
        after="from .model import Result\nfrom .specification import load_cases",
        pattern="test_command_checker.py",
        expected_test="test_internal_dependency_graph_matches_contract",
    ),
    Mutation(
        name="absolute package import hides reports-to-specification dependency",
        path="command_checker/reports.py",
        before="from .model import Result",
        after="from .model import Result\nfrom command_checker import specification",
        pattern="test_command_checker.py",
        expected_test="test_internal_dependency_graph_matches_contract",
    ),
    Mutation(
        name="absolute submodule import hides reports-to-specification dependency",
        path="command_checker/reports.py",
        before="from .model import Result",
        after=(
            "from .model import Result\n"
            "from command_checker.specification import load_cases"
        ),
        pattern="test_command_checker.py",
        expected_test="test_internal_dependency_graph_matches_contract",
    ),
    Mutation(
        name="dynamic import hides reports-to-specification dependency",
        path="command_checker/reports.py",
        before="from .model import Result",
        after=(
            "from .model import Result\n"
            "import importlib\n"
            "load_cases = importlib.import_module("
            "\"command_checker.specification\").load_cases"
        ),
        pattern="test_command_checker.py",
        expected_test="test_internal_dependency_graph_matches_contract",
    ),
)

PROJECT_MUTATIONS = (
    ProjectMutation(
        name="public return annotation removed",
        path="command_checker/cli.py",
        before="def main(argv: Sequence[str] | None = None) -> int:",
        after="def main(argv: Sequence[str] | None = None):",
        checker="scripts/check_type_contracts.py",
        expected_output="TYPE CONTRACT: FAIL",
    ),
    ProjectMutation(
        name="aliased string Any exposed in public API",
        path="command_checker/cli.py",
        before="from typing import Sequence",
        after="from typing import Any as PublicType, Sequence",
        checker="scripts/check_type_contracts.py",
        expected_output="TYPE CONTRACT: FAIL",
        additional_edits=((
            "command_checker/cli.py",
            "def main(argv: Sequence[str] | None = None) -> int:",
            'def main(argv: Sequence[str] | None = None) -> "PublicType":',
        ),),
    ),
    ProjectMutation(
        name="typing module alias Any exposed in public API",
        path="command_checker/cli.py",
        before="from typing import Sequence",
        after="import typing as t\nfrom typing import Sequence",
        checker="scripts/check_type_contracts.py",
        expected_output="TYPE CONTRACT: FAIL",
        additional_edits=((
            "command_checker/cli.py",
            "def main(argv: Sequence[str] | None = None) -> int:",
            "def main(argv: Sequence[str] | None = None) -> t.Any:",
        ),),
    ),
    ProjectMutation(
        name="assigned Any alias exposed in public API",
        path="command_checker/cli.py",
        before="from typing import Sequence",
        after="from typing import Any, Sequence\n\nPublicType = Any",
        checker="scripts/check_type_contracts.py",
        expected_output="TYPE CONTRACT: FAIL",
        additional_edits=((
            "command_checker/cli.py",
            "def main(argv: Sequence[str] | None = None) -> int:",
            "def main(argv: Sequence[str] | None = None) -> PublicType:",
        ),),
    ),
    ProjectMutation(
        name="annotated assigned Any alias exposed in public API",
        path="command_checker/cli.py",
        before="from typing import Sequence",
        after="from typing import Any, Sequence\n\nPublicType: object = Any",
        checker="scripts/check_type_contracts.py",
        expected_output="TYPE CONTRACT: FAIL",
        additional_edits=((
            "command_checker/cli.py",
            "def main(argv: Sequence[str] | None = None) -> int:",
            "def main(argv: Sequence[str] | None = None) -> PublicType:",
        ),),
    ),
    ProjectMutation(
        name="TYPE_CHECKING Any alias exposed in public API",
        path="command_checker/cli.py",
        before="from typing import Sequence",
        after=(
            "from typing import TYPE_CHECKING, Sequence\n\n"
            "if TYPE_CHECKING:\n"
            "    from typing import Any as PublicType"
        ),
        checker="scripts/check_type_contracts.py",
        expected_output="TYPE CONTRACT: FAIL",
        additional_edits=((
            "command_checker/cli.py",
            "def main(argv: Sequence[str] | None = None) -> int:",
            "def main(argv: Sequence[str] | None = None) -> PublicType:",
        ),),
    ),
    ProjectMutation(
        name="console script target changed",
        path="pyproject.toml",
        before='command-checker = "command_checker.cli:main"',
        after='command-checker = "command_checker.cli:missing"',
        checker="scripts/check_package_install.py",
        expected_output="PACKAGE CHECK: FAIL",
    ),
    ProjectMutation(
        name="wheel omits cli module",
        path="_command_checker_build.py",
        before=(
            'if path.is_file() and (path.suffix == ".py" '
            'or path.name == "py.typed"):'
        ),
        after=(
            'if path.is_file() and path.name != "cli.py" and '
            '(path.suffix == ".py" or path.name == "py.typed"):'
        ),
        checker="scripts/check_package_install.py",
        expected_output="PACKAGE CHECK: FAIL",
    ),
    ProjectMutation(
        name="wheel omits python module entrypoint",
        path="_command_checker_build.py",
        before=(
            'if path.is_file() and (path.suffix == ".py" '
            'or path.name == "py.typed"):'
        ),
        after=(
            'if path.is_file() and path.name != "__main__.py" and '
            '(path.suffix == ".py" or path.name == "py.typed"):'
        ),
        checker="scripts/check_package_install.py",
        expected_output="PACKAGE CHECK: FAIL",
    ),
    ProjectMutation(
        name="installed package path delegates to source tree",
        path="command_checker/__init__.py",
        before='__version__ = "1.0.0"',
        after=(
            '__version__ = "1.0.0"\n'
            f"__path__[:] = [{str(REFERENCE / 'command_checker')!r}]"
        ),
        checker="scripts/check_package_install.py",
        expected_output="PACKAGE CHECK: FAIL",
    ),
    ProjectMutation(
        name="installed cli executes an absolute source file",
        path="command_checker/cli.py",
        before="from __future__ import annotations\n\nimport argparse",
        after=(
            "from __future__ import annotations\n\n"
            "exec(compile(open("
            f"{str(REFERENCE / 'command_checker' / 'cli.py')!r}, encoding='utf-8').read(), "
            f"{str(REFERENCE / 'command_checker' / 'cli.py')!r}, 'exec'))\n\n"
            "import argparse"
        ),
        checker="scripts/check_package_install.py",
        expected_output="PACKAGE CHECK: FAIL",
    ),
    ProjectMutation(
        name="installed cli defers absolute source execution until main",
        path="command_checker/cli.py",
        before="def main(argv: Sequence[str] | None = None) -> int:\n",
        after=(
            "def main(argv: Sequence[str] | None = None) -> int:\n"
            "    exec(compile(open("
            f"{str(REFERENCE / 'command_checker' / 'cli.py')!r}, encoding='utf-8').read(), "
            f"{str(REFERENCE / 'command_checker' / 'cli.py')!r}, 'exec'))\n"
        ),
        checker="scripts/check_package_install.py",
        expected_output="PACKAGE CHECK: FAIL",
    ),
)


def apply_mutation(root: Path, mutation: Mutation) -> None:
    target = root / mutation.path
    text = target.read_text(encoding="utf-8")
    count = text.count(mutation.before)
    if count != 1:
        raise RuntimeError(
            f"mutation anchor mismatch for {mutation.name}: "
            f"expected 1 occurrence, found {count} in {mutation.path}"
        )
    target.write_text(text.replace(mutation.before, mutation.after, 1), encoding="utf-8")


def rejected(mutation: Mutation) -> bool:
    with tempfile.TemporaryDirectory(prefix="guide-python-mutation-") as directory:
        implementation = Path(directory) / "implementation"
        shutil.copytree(REFERENCE, implementation)
        apply_mutation(implementation, mutation)

        environment = os.environ.copy()
        environment["EXERCISE_IMPL_ROOT"] = str(implementation)
        environment["PYTHONDONTWRITEBYTECODE"] = "1"
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "unittest",
                "discover",
                "-s",
                str(TESTS),
                "-p",
                mutation.pattern,
                "-v",
            ],
            cwd=ROOT,
            env=environment,
            text=True,
            capture_output=True,
            check=False,
            timeout=30,
        )

    combined = result.stdout + result.stderr
    if result.returncode == 0:
        print(f"FAIL  mutation survived: {mutation.name}", file=sys.stderr)
        return False
    if mutation.expected_test not in combined:
        print(
            f"FAIL  mutation failed for an unexpected reason: {mutation.name}",
            file=sys.stderr,
        )
        print(combined, file=sys.stderr)
        return False
    print(f"PASS  mutation rejected: {mutation.name}")
    return True


def project_contract_rejected(mutation: ProjectMutation) -> bool:
    with tempfile.TemporaryDirectory(prefix="guide-python-project-mutation-") as directory:
        implementation = Path(directory) / "implementation"
        shutil.copytree(REFERENCE, implementation)
        edits = ((mutation.path, mutation.before, mutation.after), *mutation.additional_edits)
        for relative, before, after in edits:
            target = implementation / relative
            text = target.read_text(encoding="utf-8")
            if text.count(before) != 1:
                raise RuntimeError(
                    f"project mutation anchor mismatch for {mutation.name}: {relative}"
                )
            target.write_text(text.replace(before, after, 1), encoding="utf-8")
        environment = os.environ.copy()
        environment["PYTHONDONTWRITEBYTECODE"] = "1"
        result = subprocess.run(
            [
                sys.executable, "-B", str(ROOT / mutation.checker),
                "--implementation-root", str(implementation),
            ],
            cwd=ROOT,
            env=environment,
            text=True,
            capture_output=True,
            check=False,
            timeout=30,
        )
    combined = result.stdout + result.stderr
    if result.returncode == 0 or mutation.expected_output not in combined:
        print(f"FAIL  project mutation survived: {mutation.name}", file=sys.stderr)
        print(combined, file=sys.stderr)
        return False
    print(f"PASS  project mutation rejected: {mutation.name}")
    return True


def main() -> int:
    failures = 0
    for mutation in MUTATIONS:
        try:
            if not rejected(mutation):
                failures += 1
        except (OSError, RuntimeError, subprocess.SubprocessError) as error:
            print(f"FAIL  mutation setup: {mutation.name}: {error}", file=sys.stderr)
            failures += 1
    for mutation in PROJECT_MUTATIONS:
        try:
            if not project_contract_rejected(mutation):
                failures += 1
        except (OSError, RuntimeError, subprocess.SubprocessError) as error:
            print(f"FAIL  project mutation setup: {mutation.name}: {error}", file=sys.stderr)
            failures += 1

    if failures:
        print(f"테스트 품질 검사 실패: {failures}건", file=sys.stderr)
        return 1
    total = len(MUTATIONS) + len(PROJECT_MUTATIONS)
    print(f"테스트 품질 검사 통과: {total}개 구현·프로젝트 결함을 모두 검출했습니다.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
