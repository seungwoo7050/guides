from __future__ import annotations

import ast
import unittest

from support import IMPLEMENTATION_ROOT, module


class ArchitectureTest(unittest.TestCase):
    ALLOWED_INTERNAL_DEPENDENCIES = {
        "__init__": set(),
        "__main__": {"cli"},
        "cli": {"model", "reports", "runner", "specification"},
        "comparison": {"model"},
        "model": set(),
        "process": {"comparison", "model"},
        "reports": {"model"},
        "runner": {"model", "process"},
        "specification": {"model"},
    }

    def test_all_public_modules_import(self) -> None:
        for name in (
            "model",
            "comparison",
            "specification",
            "process",
            "reports",
            "runner",
            "cli",
        ):
            with self.subTest(module=name):
                self.assertIsNotNone(module(name))

    def test_package_layout_includes_packaging_and_typed_marker(self) -> None:
        package = IMPLEMENTATION_ROOT / "command_checker"
        self.assertEqual(
            {path.name for path in package.iterdir() if path.is_file()},
            {*(f"{name}.py" for name in self.ALLOWED_INTERNAL_DEPENDENCIES), "py.typed"},
        )
        self.assertTrue((IMPLEMENTATION_ROOT / "pyproject.toml").is_file())

    def test_internal_dependency_graph_matches_contract(self) -> None:
        package = IMPLEMENTATION_ROOT / "command_checker"
        graph: dict[str, set[str]] = {}
        for name, allowed in self.ALLOWED_INTERNAL_DEPENDENCIES.items():
            tree = ast.parse((package / f"{name}.py").read_text(encoding="utf-8"))
            dependencies: set[str] = set()
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom):
                    if node.level == 1:
                        if node.module:
                            dependencies.add(node.module.split(".", 1)[0])
                        else:
                            dependencies.update(
                                alias.name.split(".", 1)[0] for alias in node.names
                            )
                    elif node.level == 0 and node.module == "command_checker":
                        dependencies.update(
                            alias.name.split(".", 1)[0] for alias in node.names
                        )
                    elif node.level == 0 and node.module is not None:
                        prefix = "command_checker."
                        if node.module.startswith(prefix):
                            dependencies.add(node.module[len(prefix):].split(".", 1)[0])
                elif isinstance(node, ast.Import):
                    for alias in node.names:
                        if alias.name.startswith("command_checker."):
                            dependencies.add(alias.name.split(".", 2)[1])
                elif (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                      and node.func.id == "__import__"):
                    self.fail(f"동적 내부 import는 의존 그래프를 숨깁니다: {name}.py")
                elif (
                    isinstance(node, ast.Call)
                    and (
                        isinstance(node.func, ast.Name)
                        and node.func.id == "import_module"
                        or isinstance(node.func, ast.Attribute)
                        and node.func.attr in {"import_module", "__import__"}
                    )
                ):
                    self.fail(f"동적 내부 import는 의존 그래프를 숨깁니다: {name}.py")
            internal = dependencies & self.ALLOWED_INTERNAL_DEPENDENCIES.keys()
            self.assertLessEqual(internal, allowed, f"{name}.py: {sorted(internal - allowed)}")
            graph[name] = internal

        visiting: set[str] = set()
        visited: set[str] = set()

        def visit(name: str) -> None:
            if name in visiting:
                self.fail(f"순환 내부 의존성: {name}")
            if name in visited:
                return
            visiting.add(name)
            for dependency in graph[name]:
                visit(dependency)
            visiting.remove(name)
            visited.add(name)

        for name in graph:
            visit(name)

    def test_reference_has_no_scaffold_markers(self) -> None:
        package = IMPLEMENTATION_ROOT / "command_checker"
        for path in sorted(package.glob("*.py")):
            text = path.read_text(encoding="utf-8")
            self.assertNotIn("NotImplementedError", text, path.name)
            self.assertNotIn("TODO(stage", text, path.name)


if __name__ == "__main__":
    unittest.main()
