from __future__ import annotations

import sys
import unittest

from support import run_cli, run_python


class EntrypointTest(unittest.TestCase):
    def test_import_has_no_output_or_exit(self) -> None:
        result = run_python("import command_checker")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "")
        self.assertEqual(result.stderr, "")

    def test_help_uses_stdout_and_zero(self) -> None:
        result = run_cli(["--help"])
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("command-checker", result.stdout)
        self.assertIn("--cases", result.stdout)
        self.assertEqual(result.stderr, "")

    def test_missing_command_is_usage_error(self) -> None:
        result = run_cli(["--cases", "missing.json"])
        self.assertEqual(result.returncode, 2)
        self.assertEqual(result.stdout, "")
        self.assertIn("오류", result.stderr)

    def test_jobs_must_be_positive(self) -> None:
        result = run_cli(
            ["--cases", "missing.json", "--jobs", "0", "--", sys.executable]
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("--jobs", result.stderr)


if __name__ == "__main__":
    unittest.main()
