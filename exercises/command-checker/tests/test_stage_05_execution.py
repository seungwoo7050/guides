from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

from support import FIXTURES, module


class ProcessExecutionTest(unittest.TestCase):
    def setUp(self) -> None:
        self.model = module("model")
        self.process = module("process")
        self.behavior = [sys.executable, str(FIXTURES / "behavior.py")]

    def test_runs_line_sort_and_compares_all_channels(self) -> None:
        case = self.model.Case(
            name="sort",
            stdin="3 1 2\n",
            stdout="1\n2\n3\n",
        )
        result = self.process.run_case(
            case,
            [sys.executable, str(FIXTURES / "line-sort.py")],
        )
        self.assertTrue(result.passed, result.failures)
        self.assertEqual(result.returncode, 0)

    def test_argument_boundaries_are_preserved(self) -> None:
        expected = json.dumps(["a b", "*"], ensure_ascii=False) + "\n"
        case = self.model.Case(
            name="args",
            args=("args", "a b", "*"),
            stdout=expected,
        )
        result = self.process.run_case(case, self.behavior)
        self.assertTrue(result.passed, result.failures)

    def test_environment_and_working_directory_are_explicit(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            environment_case = self.model.Case(
                name="environment",
                args=("environment",),
                stdout="hello\n",
                env=(("CHECKER_VALUE", "hello"),),
            )
            cwd_case = self.model.Case(
                name="cwd",
                args=("cwd",),
                stdout=str(root) + "\n",
                cwd=root,
            )
            environment_result = self.process.run_case(environment_case, self.behavior)
            cwd_result = self.process.run_case(cwd_case, self.behavior)
        self.assertTrue(environment_result.passed, environment_result.failures)
        self.assertTrue(cwd_result.passed, cwd_result.failures)

    def test_mismatched_stderr_and_returncode_are_results_not_exceptions(self) -> None:
        case = self.model.Case(
            name="channels",
            args=("channels",),
            stdout="expected",
            stderr="expected-error",
            returncode=0,
            env=(("CODE", "7"), ("ERR", "actual-error"), ("OUT", "actual")),
        )
        result = self.process.run_case(case, self.behavior)
        self.assertFalse(result.passed)
        self.assertEqual(len(result.failures), 3)


if __name__ == "__main__":
    unittest.main()
