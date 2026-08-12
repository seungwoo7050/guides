from __future__ import annotations

import json
import tempfile
import threading
import unittest
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest import mock

from support import module


class ConcurrencyAndReportsTest(unittest.TestCase):
    def setUp(self) -> None:
        self.model = module("model")
        self.runner = module("runner")
        self.reports = module("reports")

    def result(self, *, name: str, passed: bool, stdout: str = ""):
        return self.model.Result(
            name=name,
            passed=passed,
            duration_ms=25,
            failures=() if passed else ("불일치",),
            returncode=0,
            stdout=stdout,
            stderr="",
            timed_out=False,
            exceeded_stream=None,
        )

    def test_parallel_completion_keeps_input_order(self) -> None:
        cases = (
            self.model.Case(name="slow"),
            self.model.Case(name="fast"),
            self.model.Case(name="middle"),
        )
        started = threading.Barrier(4)
        releases = {case.name: threading.Event() for case in cases}
        completed = {case.name: threading.Event() for case in cases}
        completion_order: list[str] = []

        def controlled_run(case, command):
            del command
            started.wait(timeout=2.0)
            if not releases[case.name].wait(timeout=2.0):
                raise AssertionError(f"release되지 않은 사례: {case.name}")
            completion_order.append(case.name)
            completed[case.name].set()
            return self.result(name=case.name, passed=True)

        with mock.patch.object(self.runner, "run_case", side_effect=controlled_run):
            with ThreadPoolExecutor(max_workers=1) as coordinator:
                future = coordinator.submit(self.runner.run_cases, cases, ("unused",), 3)
                started.wait(timeout=2.0)
                for name in ("fast", "middle", "slow"):
                    releases[name].set()
                    self.assertTrue(completed[name].wait(timeout=2.0), name)
                results = future.result(timeout=2.0)

        self.assertEqual(completion_order, ["fast", "middle", "slow"])
        self.assertEqual([result.name for result in results], ["slow", "fast", "middle"])
        self.assertTrue(all(result.passed for result in results))

    def test_json_and_junit_share_the_same_results(self) -> None:
        results = (self.result(name="pass", passed=True), self.result(name="fail", passed=False))
        payload = json.loads(self.reports.render_json(results))
        suite = ET.fromstring(self.reports.render_junit(results))
        self.assertEqual(payload["passed"], 1)
        self.assertEqual(payload["failed"], 1)
        self.assertEqual([item["name"] for item in payload["results"]], ["pass", "fail"])
        self.assertEqual(suite.attrib["tests"], "2")
        self.assertEqual(suite.attrib["failures"], "1")

    def test_junit_replaces_invalid_xml_control_characters(self) -> None:
        xml = self.reports.render_junit(
            (self.result(name="control", passed=True, stdout="ok\x01bad\n"),)
        )
        self.assertNotIn("\x01", xml)
        self.assertIn("\ufffd", xml)
        ET.fromstring(xml)

    def test_atomic_write_preserves_existing_file_when_replace_fails(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / "report.json"
            target.write_text("old\n", encoding="utf-8")
            with mock.patch.object(
                self.reports.os,
                "replace",
                side_effect=OSError("injected replace failure"),
            ):
                with self.assertRaises(OSError):
                    self.reports.atomic_write_text(target, "new\n")
            self.assertEqual(target.read_text(encoding="utf-8"), "old\n")
            self.assertEqual([path.name for path in root.iterdir()], ["report.json"])

    def test_report_writers_create_parseable_files(self) -> None:
        results = (self.result(name="pass", passed=True),)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            json_path = root / "report.json"
            junit_path = root / "report.xml"
            self.reports.write_json_report(json_path, results)
            self.reports.write_junit_report(junit_path, results)
            self.assertEqual(json.loads(json_path.read_text(encoding="utf-8"))["passed"], 1)
            ET.parse(junit_path)


if __name__ == "__main__":
    unittest.main()
