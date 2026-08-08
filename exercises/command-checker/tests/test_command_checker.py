from __future__ import annotations

import unittest

from support import IMPLEMENTATION_ROOT, module


class ArchitectureTest(unittest.TestCase):
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

    def test_lower_level_modules_do_not_depend_on_cli(self) -> None:
        package = IMPLEMENTATION_ROOT / "command_checker"
        for filename in (
            "model.py",
            "comparison.py",
            "specification.py",
            "process.py",
            "reports.py",
        ):
            text = (package / filename).read_text(encoding="utf-8")
            self.assertNotIn("from .cli", text, filename)
            self.assertNotIn("import command_checker.cli", text, filename)

    def test_reference_has_no_scaffold_markers(self) -> None:
        package = IMPLEMENTATION_ROOT / "command_checker"
        for path in sorted(package.glob("*.py")):
            text = path.read_text(encoding="utf-8")
            self.assertNotIn("NotImplementedError", text, path.name)
            self.assertNotIn("TODO(stage", text, path.name)


if __name__ == "__main__":
    unittest.main()
