from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from support import module, write_cases


class SpecificationTest(unittest.TestCase):
    def setUp(self) -> None:
        self.model = module("model")
        self.specification = module("specification")

    def test_valid_case_uses_defaults_and_resolves_cwd(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "work").mkdir()
            path = write_cases(
                root,
                [
                    {
                        "name": "sample",
                        "args": ["a b"],
                        "cwd": "work",
                        "env": {"B": "2", "A": "1"},
                    }
                ],
            )
            cases = self.specification.load_cases(path)
        self.assertEqual(len(cases), 1)
        case = cases[0]
        self.assertEqual(case.args, ("a b",))
        self.assertEqual(case.cwd, (root / "work").resolve())
        self.assertEqual(case.env, (("A", "1"), ("B", "2")))
        self.assertEqual(case.output_limit, self.model.DEFAULT_OUTPUT_LIMIT)

    def test_unknown_field_and_duplicate_name_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            unknown = write_cases(root, [{"name": "x", "unknown": 1}], "unknown.json")
            duplicate = write_cases(
                root,
                [{"name": "x"}, {"name": "x"}],
                "duplicate.json",
            )
            with self.assertRaises(self.model.SpecificationError):
                self.specification.load_cases(unknown)
            with self.assertRaises(self.model.SpecificationError):
                self.specification.load_cases(duplicate)

    def test_bool_is_not_a_numeric_timeout_or_limit(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            timeout = write_cases(root, [{"name": "x", "timeout": True}], "timeout.json")
            limit = write_cases(
                root,
                [{"name": "x", "output_limit": False}],
                "limit.json",
            )
            with self.assertRaises(self.model.SpecificationError):
                self.specification.load_cases(timeout)
            with self.assertRaises(self.model.SpecificationError):
                self.specification.load_cases(limit)

    def test_invalid_environment_and_missing_directory_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            invalid_env = write_cases(
                root,
                [{"name": "x", "env": {"BAD=KEY": "value"}}],
                "env.json",
            )
            missing_cwd = write_cases(
                root,
                [{"name": "x", "cwd": "missing"}],
                "cwd.json",
            )
            with self.assertRaises(self.model.SpecificationError):
                self.specification.load_cases(invalid_env)
            with self.assertRaises(self.model.SpecificationError):
                self.specification.load_cases(missing_cwd)

    def test_top_level_must_be_a_nonempty_array(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            empty = write_cases(root, [], "empty.json")
            object_path = write_cases(root, {"name": "x"}, "object.json")
            with self.assertRaises(self.model.SpecificationError):
                self.specification.load_cases(empty)
            with self.assertRaises(self.model.SpecificationError):
                self.specification.load_cases(object_path)


if __name__ == "__main__":
    unittest.main()
