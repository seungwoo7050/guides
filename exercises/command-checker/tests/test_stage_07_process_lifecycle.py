from __future__ import annotations

import os
import sys
import tempfile
import time
import unittest
from pathlib import Path

from support import FIXTURES, module


@unittest.skipUnless(os.name == "posix", "POSIX 프로세스 그룹이 필요합니다.")
class ProcessLifecycleTest(unittest.TestCase):
    def setUp(self) -> None:
        self.model = module("model")
        self.process = module("process")
        self.behavior = [sys.executable, str(FIXTURES / "behavior.py")]

    def assert_process_disappears(self, pid: int) -> None:
        deadline = time.monotonic() + 2.0
        while time.monotonic() < deadline:
            try:
                os.kill(pid, 0)
            except ProcessLookupError:
                return
            time.sleep(0.02)
        self.fail(f"자식 프로세스가 남았습니다: {pid}")

    def test_timeout_terminates_child_process_group(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            pid_file = Path(directory) / "child.pid"
            case = self.model.Case(
                name="timeout-child",
                args=("spawn-child",),
                timeout=0.4,
                env=(("CHILD_PID_FILE", str(pid_file)),),
            )
            started = time.monotonic()
            result = self.process.run_case(case, self.behavior)
            elapsed = time.monotonic() - started
            self.assertTrue(pid_file.is_file())
            child_pid = int(pid_file.read_text(encoding="utf-8"))

        self.assertFalse(result.passed)
        self.assertTrue(result.timed_out)
        self.assertLess(elapsed, 2.0)
        self.assert_process_disappears(child_pid)

    def test_parent_exit_does_not_hide_child_holding_pipe(self) -> None:
        case = self.model.Case(
            name="orphan-pipe",
            args=("orphan-pipe",),
            timeout=0.3,
        )
        result = self.process.run_case(case, self.behavior)
        self.assertFalse(result.passed)
        self.assertTrue(result.timed_out)

    def test_stdout_and_stderr_limits_stop_collection(self) -> None:
        for stream in ("stdout", "stderr"):
            with self.subTest(stream=stream):
                case = self.model.Case(
                    name=stream,
                    args=("flood", stream, "4096"),
                    timeout=1.0,
                    output_limit=1024,
                )
                result = self.process.run_case(case, self.behavior)
                self.assertFalse(result.passed)
                self.assertEqual(result.exceeded_stream, stream)
                actual = result.stdout if stream == "stdout" else result.stderr
                self.assertEqual(len(actual.encode("utf-8")), 1024)


if __name__ == "__main__":
    unittest.main()
