"""Finite-difference check for scalar linear regression gradients."""
from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class GradientCheck:
    analytic_weight: float
    numerical_weight: float
    analytic_bias: float
    numerical_bias: float
    tolerance: float

    @property
    def passed(self) -> bool:
        return math.isclose(self.analytic_weight, self.numerical_weight, rel_tol=self.tolerance, abs_tol=self.tolerance) and math.isclose(
            self.analytic_bias,
            self.numerical_bias,
            rel_tol=self.tolerance,
            abs_tol=self.tolerance,
        )


def mean_squared_error(xs: list[float], ys: list[float], *, weight: float, bias: float) -> float:
    if not xs or len(xs) != len(ys):
        raise ValueError("xs and ys must be non-empty and have the same length")
    return sum(((weight * x + bias) - y) ** 2 for x, y in zip(xs, ys, strict=True)) / len(xs)


def analytic_gradient(xs: list[float], ys: list[float], *, weight: float, bias: float) -> tuple[float, float]:
    if not xs or len(xs) != len(ys):
        raise ValueError("xs and ys must be non-empty and have the same length")
    scale = 2.0 / len(xs)
    grad_weight = scale * sum(((weight * x + bias) - y) * x for x, y in zip(xs, ys, strict=True))
    grad_bias = scale * sum((weight * x + bias) - y for x, y in zip(xs, ys, strict=True))
    return grad_weight, grad_bias


def finite_difference_gradient(
    xs: list[float],
    ys: list[float],
    *,
    weight: float,
    bias: float,
    epsilon: float = 1e-6,
) -> tuple[float, float]:
    if epsilon <= 0:
        raise ValueError("epsilon must be positive")
    plus_w = mean_squared_error(xs, ys, weight=weight + epsilon, bias=bias)
    minus_w = mean_squared_error(xs, ys, weight=weight - epsilon, bias=bias)
    plus_b = mean_squared_error(xs, ys, weight=weight, bias=bias + epsilon)
    minus_b = mean_squared_error(xs, ys, weight=weight, bias=bias - epsilon)
    return (plus_w - minus_w) / (2.0 * epsilon), (plus_b - minus_b) / (2.0 * epsilon)


def check_gradient(
    xs: list[float],
    ys: list[float],
    *,
    weight: float,
    bias: float,
    epsilon: float = 1e-6,
    tolerance: float = 1e-5,
) -> GradientCheck:
    analytic_w, analytic_b = analytic_gradient(xs, ys, weight=weight, bias=bias)
    numerical_w, numerical_b = finite_difference_gradient(
        xs,
        ys,
        weight=weight,
        bias=bias,
        epsilon=epsilon,
    )
    return GradientCheck(
        analytic_weight=analytic_w,
        numerical_weight=numerical_w,
        analytic_bias=analytic_b,
        numerical_bias=numerical_b,
        tolerance=tolerance,
    )
