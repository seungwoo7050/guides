from __future__ import annotations

import math
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "examples"))

import metrics  # noqa: E402


class MetricsTests(unittest.TestCase):
    def test_confusion_and_derived_metrics(self) -> None:
        matrix = metrics.confusion_matrix([1, 1, 0, 0], [1, 0, 1, 0])
        self.assertEqual((matrix.true_positive, matrix.false_negative), (1, 1))
        self.assertEqual((matrix.false_positive, matrix.true_negative), (1, 1))
        self.assertAlmostEqual(metrics.precision(matrix), 0.5)
        self.assertAlmostEqual(metrics.recall(matrix), 0.5)
        self.assertAlmostEqual(metrics.f1_score(matrix), 0.5)

    def test_probability_metrics(self) -> None:
        y_true = [1, 0]
        probabilities = [0.8, 0.2]
        self.assertAlmostEqual(metrics.brier_score(y_true, probabilities), 0.04)
        self.assertAlmostEqual(metrics.binary_log_loss(y_true, probabilities), -math.log(0.8))

    def test_probability_validation(self) -> None:
        with self.assertRaises(ValueError):
            metrics.probabilities_to_labels([1.1], threshold=0.5)
        with self.assertRaises(ValueError):
            metrics.confusion_matrix([], [])

    def test_calibration_bins_include_probability_one(self) -> None:
        report = metrics.calibration_bins([0, 1], [0.0, 1.0], bins=2)
        self.assertEqual([row["count"] for row in report], [1, 1])
