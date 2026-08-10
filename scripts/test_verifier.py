#!/usr/bin/env python3
"""Regression and negative tests for scripts/check_docs.py."""

from __future__ import annotations

import importlib.util
import json
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]


def load_checker():
    path = ROOT / "scripts/check_docs.py"
    spec = importlib.util.spec_from_file_location("guide_check_docs", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load check_docs.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


checker = load_checker()


def load_external_checker():
    path = ROOT / "scripts/check_external_links.py"
    spec = importlib.util.spec_from_file_location("guide_external_links", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load check_external_links.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


external = load_external_checker()


class ValidatorTests(unittest.TestCase):
    def copy_source(self, target: Path) -> Path:
        copy = target / "repo"
        shutil.copytree(
            ROOT,
            copy,
            symlinks=True,
            ignore=shutil.ignore_patterns(
                ".guide", ".git", "__pycache__", "*.pyc", "*.log",
                "workspace", "capstone-workspace", "build",
            ),
        )
        return copy

    def test_current_repository_is_valid(self) -> None:
        counts = checker.validate(ROOT)
        self.assertEqual(20, counts["documents"])
        self.assertEqual(6, counts["exercises"])
        self.assertEqual(7, counts["learning_units"])

    def test_broken_link_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory(prefix="embedded-validator-") as temporary:
            copy = self.copy_source(Path(temporary))
            with (copy / "README.md").open("a", encoding="utf-8") as stream:
                stream.write("\n[broken](docs/does-not-exist.md)\n")
            with self.assertRaisesRegex(checker.ValidationError, "깨진 링크"):
                checker.validate(copy)

    def test_missing_required_file_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory(prefix="embedded-validator-") as temporary:
            copy = self.copy_source(Path(temporary))
            (copy / "docs/00-roadmap.md").unlink()
            with self.assertRaisesRegex(checker.ValidationError, "필수 파일 누락 또는 symlink: docs/00-roadmap.md"):
                checker.validate(copy)

    def test_wrong_model_expectation_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory(prefix="embedded-validator-") as temporary:
            fixture = Path(temporary) / "fixture.json"
            data = json.loads((ROOT / "examples/interrupt-event-model/fixtures/normal.json").read_text(encoding="utf-8"))
            data["expected"]["dropped"] = 99
            fixture.write_text(json.dumps(data), encoding="utf-8")
            completed = subprocess.run(
                [sys.executable, str(ROOT / "examples/interrupt-event-model/model.py"), str(fixture), "--check"],
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
            )
            self.assertEqual(1, completed.returncode)
            self.assertIn("CHECK FAILED", completed.stdout)

    def test_heading_only_exercise_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory(prefix="embedded-validator-") as temporary:
            copy = self.copy_source(Path(temporary))
            exercise = copy / "exercises/06-update-rollback-model/README.md"
            exercise.write_text(
                "# exercise\n## 문제\n## 결과물\n## 완료 조건\n## 실패\n## starter reference check.py\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(checker.ValidationError, "교육 계약이 부족한 실습"):
                checker.validate(copy)

    def test_every_lab_part_is_required_and_nonempty(self) -> None:
        for part in checker.LEARNING_PARTS:
            with self.subTest(part=part), tempfile.TemporaryDirectory(prefix="embedded-validator-") as temporary:
                copy = self.copy_source(Path(temporary))
                target = copy / "exercises/03-sensor-driver-state-machine" / part
                shutil.rmtree(target)
                target.mkdir()
                with self.assertRaisesRegex(checker.ValidationError, "빈 학습 계약 directory"):
                    checker.validate(copy)

    def test_missing_and_nonexecutable_checker_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory(prefix="embedded-validator-") as temporary:
            copy = self.copy_source(Path(temporary))
            target = copy / "exercises/04-deadline-and-priority-review/check.py"
            target.unlink()
            with self.assertRaisesRegex(checker.ValidationError, "학습 checker 누락"):
                checker.validate(copy)
        with tempfile.TemporaryDirectory(prefix="embedded-validator-") as temporary:
            copy = self.copy_source(Path(temporary))
            target = copy / "exercises/04-deadline-and-priority-review/check.py"
            target.chmod(stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IROTH)
            with self.assertRaisesRegex(checker.ValidationError, "실행 불가능한 checker"):
                checker.validate(copy)

    def test_missing_capstone_acceptance_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory(prefix="embedded-validator-") as temporary:
            copy = self.copy_source(Path(temporary))
            (copy / "capstone/field-sensor-node/acceptance.md").unlink()
            with self.assertRaisesRegex(checker.ValidationError, "capstone/field-sensor-node/acceptance.md"):
                checker.validate(copy)

    def test_heading_only_capstone_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory(prefix="embedded-validator-") as temporary:
            copy = self.copy_source(Path(temporary))
            readme = copy / "capstone/field-sensor-node/README.md"
            readme.write_text(
                "# capstone\n## 문제\n## 결과물\n## 불변식\n## 완료\n## starter\n## reference\n## check.py\n## one\n## two\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(checker.ValidationError, "교육 계약이 부족한 capstone"):
                checker.validate(copy)

    def test_capstone_requires_exactly_twelve_numbered_scenarios(self) -> None:
        with tempfile.TemporaryDirectory(prefix="embedded-validator-") as temporary:
            copy = self.copy_source(Path(temporary))
            acceptance = copy / "capstone/field-sensor-node/acceptance.md"
            text = acceptance.read_text(encoding="utf-8")
            text = text.replace("12. new schema 때문에 previous image가 읽지 못하는 경우", "")
            acceptance.write_text(text, encoding="utf-8")
            with self.assertRaisesRegex(checker.ValidationError, "필수 시나리오가 1..12"):
                checker.validate(copy)

    def test_undisclosed_todo_marker_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory(prefix="embedded-validator-") as temporary:
            copy = self.copy_source(Path(temporary))
            with (copy / "docs/00-roadmap.md").open("a", encoding="utf-8") as stream:
                stream.write("\nTODO unresolved contract\n")
            with self.assertRaisesRegex(checker.ValidationError, "미완성 표식"):
                checker.validate(copy)


class _FakeResponse:
    def __init__(self, status: int, final_url: str):
        self.status = status
        self.final_url = final_url

    def getcode(self) -> int:
        return self.status

    def geturl(self) -> str:
        return self.final_url

    def close(self) -> None:
        return


class _FakeOpener:
    def __init__(self, outcomes):
        self.outcomes = list(outcomes)
        self.requests = []

    def open(self, request, timeout):
        self.requests.append((request, timeout))
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, BaseException):
            raise outcome
        return outcome


class ExternalLinkCheckerTests(unittest.TestCase):
    def test_markdown_urls_are_defragmented_deduplicated_and_sorted(self) -> None:
        with tempfile.TemporaryDirectory(prefix="embedded-links-") as temporary:
            root = Path(temporary)
            (root / "a.md").write_text(
                "[one](https://example.test/ok#first)\n<https://example.test/ok#second>\n",
                encoding="utf-8",
            )
            (root / "b.md").write_text("[two](https://example.test/redirect)\n", encoding="utf-8")
            self.assertEqual(
                ["https://example.test/ok", "https://example.test/redirect"],
                external.markdown_urls(root),
            )

    def test_redirect_user_agent_head_fallback_and_error_classes(self) -> None:
        redirect_opener = _FakeOpener([_FakeResponse(204, "https://example.test/final")])
        with mock.patch.object(external, "build_opener", return_value=redirect_opener):
            redirected = external.request_url("https://example.test/redirect", 1)
        self.assertEqual("OK", redirected["status"])
        self.assertEqual("https://example.test/final", redirected["final_url"])
        request, timeout = redirect_opener.requests[0]
        self.assertEqual("HEAD", request.get_method())
        self.assertEqual(1, timeout)
        self.assertEqual(external.USER_AGENT, request.get_header("User-agent"))

        fallback_opener = _FakeOpener(
            [
                external.HTTPError("https://example.test/get-only", 405, "method", None, None),
                _FakeResponse(206, "https://example.test/get-only"),
            ]
        )
        with mock.patch.object(external, "build_opener", return_value=fallback_opener):
            fallback = external.request_url("https://example.test/get-only", 1)
        self.assertEqual("OK", fallback["status"])
        self.assertEqual("GET", fallback_opener.requests[1][0].get_method())
        self.assertEqual("bytes=0-0", fallback_opener.requests[1][0].get_header("Range"))

        error_opener = _FakeOpener(
            [external.HTTPError("https://example.test/missing", 404, "missing", None, None)]
        )
        with mock.patch.object(external, "build_opener", return_value=error_opener):
            missing = external.request_url("https://example.test/missing", 1)
        self.assertEqual("HTTP_ERROR", missing["status"])
        self.assertEqual(404, missing["http_status"])

        timeout_opener = _FakeOpener([external.socket.timeout("deadline")])
        with mock.patch.object(external, "build_opener", return_value=timeout_opener):
            timed_out = external.request_url("https://example.test/slow", 0.01)
        self.assertEqual("TIMEOUT", timed_out["status"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
