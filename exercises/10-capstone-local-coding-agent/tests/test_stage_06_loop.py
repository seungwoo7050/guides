from __future__ import annotations

import unittest

from coding_agent.loop import IterationTracker, classify_failure
from coding_agent.types import CommandResult


def result(*, exit_kind: str = "EXITED", exit_code: int | None = 1, stderr: str = "") -> CommandResult:
    return CommandResult(
        command_id="unit",
        exit_kind=exit_kind,
        exit_code=exit_code,
        signal=None,
        stdout="",
        stderr=stderr,
        truncated=False,
        duration_ms=1,
        cleanup_status="CLEAN",
        workspace_before="before",
        workspace_after="after",
    )


class LoopContractTest(unittest.TestCase):
    def test_failure_categories_are_observable(self) -> None:
        self.assertEqual(classify_failure(result(exit_kind="TIMEOUT", exit_code=None)), "TIMEOUT")
        self.assertEqual(classify_failure(result(stderr="SyntaxError: invalid syntax")), "CODE_OR_CONTRACT")
        self.assertEqual(classify_failure(result(stderr="collected 0 items")), "TEST_DISCOVERY")
        self.assertEqual(classify_failure(result(exit_code=0)), "PASS")

    def test_repeated_identical_failure_stops_the_loop(self) -> None:
        tracker = IterationTracker(max_repeated_failures=2)
        failing = result(stderr="AssertionError: same revision")
        self.assertEqual(tracker.record(failing), "CODE_OR_CONTRACT")
        self.assertEqual(tracker.record(failing), "CODE_OR_CONTRACT")
        self.assertEqual(tracker.record(failing), "REPEATED_FAILURE")
        self.assertEqual(tracker.plan_revision, 3)


if __name__ == "__main__":
    unittest.main()
