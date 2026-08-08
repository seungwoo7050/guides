from __future__ import annotations

import unittest

from support import module


class ComparisonTest(unittest.TestCase):
    def setUp(self) -> None:
        self.model = module("model")
        self.comparison = module("comparison")
        self.case = self.model.Case(
            name="sample",
            stdout="ok\n",
            stderr="",
            returncode=0,
            timeout=0.5,
            output_limit=100,
        )

    def test_equal_observation_has_no_failures(self) -> None:
        failures = self.comparison.compare_observation(
            self.case,
            returncode=0,
            stdout="ok\n",
            stderr="",
        )
        self.assertEqual(failures, ())

    def test_three_channels_are_compared_independently(self) -> None:
        failures = self.comparison.compare_observation(
            self.case,
            returncode=3,
            stdout="ok",
            stderr="warning\n",
        )
        self.assertEqual(len(failures), 3)
        self.assertIn("종료 상태", failures[0])
        self.assertTrue(any("표준 출력" in failure for failure in failures))
        self.assertTrue(any("표준 오류" in failure for failure in failures))

    def test_whitespace_is_part_of_the_contract(self) -> None:
        failures = self.comparison.compare_observation(
            self.case,
            returncode=0,
            stdout="ok",
            stderr="",
        )
        self.assertEqual(len(failures), 1)
        self.assertIn("표준 출력", failures[0])

    def test_timeout_and_output_limit_are_explicit_failures(self) -> None:
        timeout = self.comparison.compare_observation(
            self.case,
            returncode=-15,
            stdout="",
            stderr="",
            timed_out=True,
        )
        exceeded = self.comparison.compare_observation(
            self.case,
            returncode=-15,
            stdout="x" * 100,
            stderr="",
            exceeded_stream="stdout",
        )
        self.assertEqual(len(timeout), 1)
        self.assertIn("제한 시간", timeout[0])
        self.assertEqual(len(exceeded), 1)
        self.assertIn("출력 상한", exceeded[0])


if __name__ == "__main__":
    unittest.main()
