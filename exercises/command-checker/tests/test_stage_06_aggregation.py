from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

from support import FIXTURES, module, run_cli, write_cases


class AggregationTest(unittest.TestCase):
    def setUp(self) -> None:
        self.model = module("model")
        self.runner = module("runner")
        self.behavior = [sys.executable, str(FIXTURES / "behavior.py")]

    def test_all_cases_run_and_keep_input_order(self) -> None:
        cases = (
            self.model.Case(
                name="first",
                args=("channels",),
                stdout="one",
                env=(("OUT", "one"),),
            ),
            self.model.Case(
                name="second",
                args=("channels",),
                stdout="expected",
                env=(("OUT", "actual"),),
            ),
            self.model.Case(
                name="third",
                args=("channels",),
                stdout="three",
                env=(("OUT", "three"),),
            ),
        )
        results = self.runner.run_cases(cases, self.behavior, 1)
        self.assertEqual([result.name for result in results], ["first", "second", "third"])
        self.assertEqual([result.passed for result in results], [True, False, True])
        self.assertEqual(self.runner.exit_status(results), 1)

    def test_cli_distinguishes_case_failure_from_specification_error(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            cases = write_cases(
                root,
                [
                    {
                        "name": "pass",
                        "args": ["channels"],
                        "stdout": "one",
                        "env": {"OUT": "one"},
                    },
                    {
                        "name": "fail",
                        "args": ["channels"],
                        "stdout": "expected",
                        "env": {"OUT": "actual"},
                    },
                ],
            )
            result = run_cli(
                [
                    "--cases",
                    str(cases),
                    "--",
                    sys.executable,
                    str(FIXTURES / "behavior.py"),
                ]
            )
            invalid = write_cases(root, {"name": "not-an-array"}, "invalid.json")
            invalid_result = run_cli(
                ["--cases", str(invalid), "--", sys.executable]
            )

        self.assertEqual(result.returncode, 1)
        self.assertIn("통과 pass", result.stdout)
        self.assertIn("요약: 통과 1건, 실패 1건", result.stdout)
        self.assertIn("실패 fail", result.stderr)
        self.assertEqual(invalid_result.returncode, 2)
        self.assertIn("최상위 값", invalid_result.stderr)

    def test_missing_executable_is_startup_error(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            cases = write_cases(Path(directory), [{"name": "x"}])
            result = run_cli(
                ["--cases", str(cases), "--", "guide-python-command-that-does-not-exist"]
            )
        self.assertEqual(result.returncode, 2)
        self.assertIn("찾을 수 없습니다", result.stderr)

    def test_executable_is_selected_once_before_case_context(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            case_work = root / "case-work"
            case_work.mkdir()
            executable = root / "probe"
            executable.write_text("#!/bin/sh\npwd\n", encoding="utf-8")
            executable.chmod(0o700)
            cases = write_cases(
                root,
                [
                    {
                        "name": "selected",
                        "cwd": "case-work",
                        "env": {"PATH": ""},
                        "stdout": str(case_work) + "\n",
                    }
                ],
            )

            for command, environment in (
                ("./probe", None),
                ("probe", {"PATH": str(root)}),
            ):
                with self.subTest(command=command):
                    result = run_cli(
                        ["--cases", str(cases), "--", command],
                        cwd=root,
                        environment=environment,
                    )
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertIn("통과 selected", result.stdout)


if __name__ == "__main__":
    unittest.main()
