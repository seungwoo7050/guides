from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "examples"))

import gradient_check  # noqa: E402


class GradientCheckTests(unittest.TestCase):
    def test_analytic_and_numerical_gradients_match(self) -> None:
        result = gradient_check.check_gradient(
            [0.0, 1.0, 2.0],
            [1.0, 3.0, 5.0],
            weight=0.4,
            bias=-0.2,
        )
        self.assertTrue(result.passed)

    def test_invalid_shapes_are_rejected(self) -> None:
        with self.assertRaises(ValueError):
            gradient_check.mean_squared_error([1.0], [], weight=1.0, bias=0.0)
