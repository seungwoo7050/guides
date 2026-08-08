#!/usr/bin/env python3
"""Statically check the exercise's public annotation contract with the stdlib AST."""

from __future__ import annotations

import argparse
import ast
import os
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXERCISE = ROOT / "exercises" / "command-checker"
REQUIRED_PUBLIC = {
    "cli.py": {"build_parser", "parse_arguments", "main"},
    "comparison.py": {"compare_observation"},
    "process.py": {"run_case"},
    "reports.py": {
        "atomic_write_text", "render_json", "write_json_report",
        "xml_text", "render_junit", "write_junit_report",
    },
    "runner.py": {"validate_executable", "run_cases", "print_results", "exit_status"},
    "specification.py": {"load_cases"},
}


def typing_imports(tree: ast.Module) -> tuple[set[str], set[str]]:
    """Return local names bound to typing.Any and to the typing module."""
    any_names = {"Any"}
    module_names = {"typing"}

    def module_scope(node: ast.AST):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Lambda)):
            return
        yield node
        for child in ast.iter_child_nodes(node):
            yield from module_scope(child)

    nodes = tuple(module_scope(tree))
    for node in nodes:
        if isinstance(node, ast.ImportFrom) and node.module == "typing":
            for alias in node.names:
                if alias.name == "Any":
                    any_names.add(alias.asname or alias.name)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == "typing":
                    module_names.add(alias.asname or alias.name)

    changed = True
    while changed:
        changed = False
        for node in nodes:
            targets: list[ast.expr] = []
            value: ast.expr | None = None
            if isinstance(node, ast.Assign):
                targets = list(node.targets)
                value = node.value
            elif isinstance(node, ast.AnnAssign) and node.value is not None:
                targets = [node.target]
                value = node.value
            if value is None or not annotation_contains_any(value, any_names, module_names):
                continue
            for target in targets:
                if isinstance(target, ast.Name) and target.id not in any_names:
                    any_names.add(target.id)
                    changed = True
    return any_names, module_names


def annotation_contains_any(
    annotation: ast.expr | None,
    any_names: set[str],
    typing_modules: set[str],
) -> bool:
    if annotation is None:
        return False
    if isinstance(annotation, ast.Constant) and isinstance(annotation.value, str):
        try:
            annotation = ast.parse(annotation.value, mode="eval").body
        except SyntaxError:
            return False
    return any(
        isinstance(node, ast.Name) and node.id in any_names
        or (
            isinstance(node, ast.Attribute)
            and node.attr == "Any"
            and isinstance(node.value, ast.Name)
            and node.value.id in typing_modules
        )
        for node in ast.walk(annotation)
    )


def check_function(
    path: Path,
    node: ast.FunctionDef | ast.AsyncFunctionDef,
    errors: list[str],
    any_names: set[str],
    typing_modules: set[str],
) -> None:
    positional = [*node.args.posonlyargs, *node.args.args]
    for index, argument in enumerate(positional):
        if index == 0 and argument.arg in {"self", "cls"}:
            continue
        if argument.annotation is None:
            errors.append(f"{path.name}:{node.lineno}: 인자 annotation 누락: {node.name}.{argument.arg}")
    for argument in node.args.kwonlyargs:
        if argument.annotation is None:
            errors.append(f"{path.name}:{node.lineno}: 인자 annotation 누락: {node.name}.{argument.arg}")
    for argument in (node.args.vararg, node.args.kwarg):
        if argument is not None and argument.annotation is None:
            errors.append(f"{path.name}:{node.lineno}: 가변 인자 annotation 누락: {node.name}.{argument.arg}")
    if node.returns is None:
        errors.append(f"{path.name}:{node.lineno}: 반환 annotation 누락: {node.name}")
    if not node.name.startswith("_"):
        annotations = [argument.annotation for argument in positional]
        annotations.extend(argument.annotation for argument in node.args.kwonlyargs)
        annotations.extend([node.args.vararg.annotation if node.args.vararg else None,
                            node.args.kwarg.annotation if node.args.kwarg else None, node.returns])
        if any(
            annotation_contains_any(annotation, any_names, typing_modules)
            for annotation in annotations
        ):
            errors.append(f"{path.name}:{node.lineno}: 공개 API에 Any 사용: {node.name}")


def check_dataclass(
    path: Path,
    node: ast.ClassDef,
    errors: list[str],
    any_names: set[str],
    typing_modules: set[str],
) -> None:
    decorators = set()
    for decorator in node.decorator_list:
        candidate = decorator.func if isinstance(decorator, ast.Call) else decorator
        if isinstance(candidate, ast.Name):
            decorators.add(candidate.id)
    if "dataclass" not in decorators:
        return
    for statement in node.body:
        if isinstance(statement, ast.Assign):
            errors.append(f"{path.name}:{statement.lineno}: dataclass 필드 annotation 누락: {node.name}")
        if (
            isinstance(statement, ast.AnnAssign)
            and annotation_contains_any(statement.annotation, any_names, typing_modules)
        ):
            errors.append(f"{path.name}:{statement.lineno}: 공개 dataclass 필드에 Any 사용: {node.name}")


def implementation_root(arguments: argparse.Namespace) -> Path:
    override = arguments.implementation_root or os.environ.get("EXERCISE_IMPL_ROOT")
    if override:
        return Path(override).resolve()
    implementation = os.environ.get("EXERCISE_IMPL", arguments.implementation)
    if implementation not in {"reference", "skeleton", "workspace"}:
        raise SystemExit(f"지원하지 않는 EXERCISE_IMPL: {implementation}")
    return (EXERCISE / implementation).resolve()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--implementation",
        choices=("reference", "skeleton", "workspace"),
        default="reference",
    )
    parser.add_argument("--implementation-root", type=Path)
    arguments = parser.parse_args()
    project = implementation_root(arguments)
    package = project / "command_checker"
    errors: list[str] = []
    if not package.is_dir():
        errors.append(f"package 디렉터리 누락: {package}")
    if not (package / "py.typed").is_file():
        errors.append("command_checker/py.typed 누락")
    try:
        configuration = tomllib.loads((project / "pyproject.toml").read_text(encoding="utf-8"))
        contract = configuration["tool"]["command-checker"]["type-contract"]
        if contract != {"require-annotations": True, "disallow-any-in-public-api": True}:
            errors.append("pyproject의 정적 공개 타입 계약 설정 불일치")
    except (OSError, KeyError, tomllib.TOMLDecodeError) as error:
        errors.append(f"pyproject 정적 타입 계약을 읽을 수 없음: {error}")

    if package.is_dir():
        for path in sorted(package.glob("*.py")):
            try:
                tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            except (OSError, SyntaxError) as error:
                errors.append(f"{path.name}: AST를 읽을 수 없음: {error}")
                continue
            any_names, typing_modules = typing_imports(tree)
            public = {
                node.name for node in tree.body
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
                and not node.name.startswith("_")
            }
            missing = REQUIRED_PUBLIC.get(path.name, set()) - public
            if missing:
                errors.append(f"{path.name}: 공개 함수 누락: {sorted(missing)}")
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    check_function(path, node, errors, any_names, typing_modules)
            for node in tree.body:
                if isinstance(node, ast.ClassDef):
                    check_dataclass(path, node, errors, any_names, typing_modules)
            if path.name == "model.py":
                classes = {node.name for node in tree.body if isinstance(node, ast.ClassDef)}
                missing_classes = {"Case", "Result", "SpecificationError", "ExecutionError"} - classes
                if missing_classes:
                    errors.append(f"model.py: 공개 클래스 누락: {sorted(missing_classes)}")

    if errors:
        print("TYPE CONTRACT: FAIL", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    print("TYPE CONTRACT: PASS (stdlib AST, annotated public API, no public Any, py.typed)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
