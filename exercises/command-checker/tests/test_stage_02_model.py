from __future__ import annotations

import unittest
from dataclasses import FrozenInstanceError
from pathlib import Path

from support import module


class ModelTest(unittest.TestCase):
    def test_case_is_slotted_frozen_and_deeply_shareable(self) -> None:
        model = module("model")
        case = model.Case(
            name="sample",
            args=("a b",),
            stdin="input\n",
            stdout="output\n",
            stderr="",
            returncode=0,
            timeout=1.5,
            cwd=Path("/tmp"),
            env=(("A", "1"), ("B", "2")),
            output_limit=4096,
        )
        self.assertTrue(hasattr(type(case), "__slots__"))
        self.assertIsInstance(case.env, tuple)
        self.assertEqual(case.environment_overrides(), {"A": "1", "B": "2"})
        with self.assertRaises(FrozenInstanceError):
            case.name = "changed"  # type: ignore[misc]

    def test_result_contains_lifecycle_state(self) -> None:
        model = module("model")
        result = model.Result(
            name="timeout",
            passed=False,
            duration_ms=200,
            failures=("제한 시간",),
            returncode=-15,
            stdout="",
            stderr="",
            timed_out=True,
            exceeded_stream=None,
        )
        self.assertTrue(result.timed_out)
        self.assertIsNone(result.exceeded_stream)
        self.assertTrue(hasattr(type(result), "__slots__"))

    def test_boundary_exceptions_preserve_categories(self) -> None:
        model = module("model")
        self.assertTrue(issubclass(model.SpecificationError, ValueError))
        self.assertTrue(issubclass(model.ExecutionError, RuntimeError))


if __name__ == "__main__":
    unittest.main()
