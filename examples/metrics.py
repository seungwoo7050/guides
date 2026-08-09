"""Small, dependency-free binary classification metrics.

These functions are intentionally explicit so learners can inspect the
contracts behind library metrics. They are not optimized for large datasets.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Iterable, Sequence


@dataclass(frozen=True)
class ConfusionMatrix:
    true_positive: int
    false_positive: int
    true_negative: int
    false_negative: int

    @property
    def total(self) -> int:
        return (
            self.true_positive
            + self.false_positive
            + self.true_negative
            + self.false_negative
        )


def _binary_labels(values: Iterable[int], *, name: str) -> list[int]:
    result = list(values)
    if not result:
        raise ValueError(f"{name} must not be empty")
    invalid = [value for value in result if value not in (0, 1)]
    if invalid:
        raise ValueError(f"{name} must contain only 0 or 1: {invalid[:3]}")
    return result


def confusion_matrix(y_true: Iterable[int], y_pred: Iterable[int]) -> ConfusionMatrix:
    actual = _binary_labels(y_true, name="y_true")
    predicted = _binary_labels(y_pred, name="y_pred")
    if len(actual) != len(predicted):
        raise ValueError("y_true and y_pred must have the same length")

    tp = fp = tn = fn = 0
    for expected, observed in zip(actual, predicted, strict=True):
        if expected == 1 and observed == 1:
            tp += 1
        elif expected == 0 and observed == 1:
            fp += 1
        elif expected == 0 and observed == 0:
            tn += 1
        else:
            fn += 1
    return ConfusionMatrix(tp, fp, tn, fn)


def safe_divide(numerator: float, denominator: float, *, zero_division: float = 0.0) -> float:
    if denominator == 0:
        return zero_division
    return numerator / denominator


def precision(matrix: ConfusionMatrix, *, zero_division: float = 0.0) -> float:
    return safe_divide(
        matrix.true_positive,
        matrix.true_positive + matrix.false_positive,
        zero_division=zero_division,
    )


def recall(matrix: ConfusionMatrix, *, zero_division: float = 0.0) -> float:
    return safe_divide(
        matrix.true_positive,
        matrix.true_positive + matrix.false_negative,
        zero_division=zero_division,
    )


def f1_score(matrix: ConfusionMatrix, *, zero_division: float = 0.0) -> float:
    p = precision(matrix, zero_division=zero_division)
    r = recall(matrix, zero_division=zero_division)
    return safe_divide(2.0 * p * r, p + r, zero_division=zero_division)


def probabilities_to_labels(probabilities: Iterable[float], *, threshold: float) -> list[int]:
    if not 0.0 <= threshold <= 1.0:
        raise ValueError("threshold must be between 0 and 1")
    result: list[int] = []
    for probability in probabilities:
        if not math.isfinite(probability) or not 0.0 <= probability <= 1.0:
            raise ValueError(f"invalid probability: {probability!r}")
        result.append(1 if probability >= threshold else 0)
    if not result:
        raise ValueError("probabilities must not be empty")
    return result


def _validated_probabilities(values: Iterable[float], *, name: str) -> list[float]:
    result = list(values)
    if not result:
        raise ValueError(f"{name} must not be empty")
    for value in result:
        if not math.isfinite(value) or not 0.0 <= value <= 1.0:
            raise ValueError(f"{name} contains invalid probability: {value!r}")
    return result


def brier_score(y_true: Iterable[int], probabilities: Iterable[float]) -> float:
    actual = _binary_labels(y_true, name="y_true")
    predicted = _validated_probabilities(probabilities, name="probabilities")
    if len(actual) != len(predicted):
        raise ValueError("y_true and probabilities must have the same length")
    return sum((probability - expected) ** 2 for expected, probability in zip(actual, predicted, strict=True)) / len(actual)


def binary_log_loss(
    y_true: Iterable[int],
    probabilities: Iterable[float],
    *,
    epsilon: float = 1e-15,
) -> float:
    actual = _binary_labels(y_true, name="y_true")
    predicted = _validated_probabilities(probabilities, name="probabilities")
    if len(actual) != len(predicted):
        raise ValueError("y_true and probabilities must have the same length")
    if not 0.0 < epsilon < 0.5:
        raise ValueError("epsilon must be between 0 and 0.5")

    total = 0.0
    for expected, raw_probability in zip(actual, predicted, strict=True):
        probability = min(max(raw_probability, epsilon), 1.0 - epsilon)
        total -= expected * math.log(probability) + (1 - expected) * math.log(1.0 - probability)
    return total / len(actual)


def calibration_bins(
    y_true: Sequence[int],
    probabilities: Sequence[float],
    *,
    bins: int = 10,
) -> list[dict[str, float | int]]:
    actual = _binary_labels(y_true, name="y_true")
    predicted = _validated_probabilities(probabilities, name="probabilities")
    if len(actual) != len(predicted):
        raise ValueError("y_true and probabilities must have the same length")
    if bins <= 0:
        raise ValueError("bins must be positive")

    bucket_rows: list[list[tuple[int, float]]] = [[] for _ in range(bins)]
    for expected, probability in zip(actual, predicted, strict=True):
        index = min(int(probability * bins), bins - 1)
        bucket_rows[index].append((expected, probability))

    report: list[dict[str, float | int]] = []
    for index, rows in enumerate(bucket_rows):
        if not rows:
            continue
        count = len(rows)
        report.append(
            {
                "bin": index,
                "lower": index / bins,
                "upper": (index + 1) / bins,
                "count": count,
                "mean_probability": sum(row[1] for row in rows) / count,
                "positive_rate": sum(row[0] for row in rows) / count,
            }
        )
    return report
