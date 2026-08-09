"""Public trace and history oracles for the capstone evidence contract."""

from .checks import (
    Diagnostic,
    HistoryResult,
    InvariantResult,
    canonical_trace_digest,
    check_expected,
    check_history,
    check_invariants,
    check_scenario_evidence,
    shrink_failure,
    validate_trace,
)

__all__ = [
    "Diagnostic",
    "HistoryResult",
    "InvariantResult",
    "canonical_trace_digest",
    "check_expected",
    "check_history",
    "check_invariants",
    "check_scenario_evidence",
    "shrink_failure",
    "validate_trace",
]
