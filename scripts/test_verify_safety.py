#!/usr/bin/env python3
"""Exercise verify log ownership, signals, and timeout process cleanup."""

from __future__ import annotations

import os
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class VerifySafetyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="embedded-verify-safety-")
        self.base = Path(self.temporary.name).resolve()
        self.copy = self.base / "repo"
        shutil.copytree(
            ROOT,
            self.copy,
            symlinks=True,
            ignore=shutil.ignore_patterns(
                ".git", ".guide", "__pycache__", "*.pyc", "*.log",
                "workspace", "capstone-workspace", "build",
            ),
        )
        prepared = subprocess.run(
            ["sh", "prepare.sh"],
            cwd=self.copy,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        if prepared.returncode != 0:
            self.fail(prepared.stdout + prepared.stderr)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def run_verify(self, *, log: str | Path, probe: str = "success") -> subprocess.CompletedProcess[str]:
        environment = os.environ.copy()
        environment.update(
            VERIFY_LOG=str(log),
            VERIFY_SAFETY_PROBE=probe,
            PYTHONDONTWRITEBYTECODE="1",
        )
        return subprocess.run(
            ["sh", "verify.sh"],
            cwd=self.copy,
            env=environment,
            capture_output=True,
            text=True,
            timeout=20,
            check=False,
        )

    def test_new_external_log_is_created_as_regular_file(self) -> None:
        log = self.base / "valid.log"
        completed = self.run_verify(log=log)
        self.assertEqual(0, completed.returncode, completed.stdout + completed.stderr)
        self.assertTrue(log.is_file())
        self.assertFalse(log.is_symlink())
        self.assertIn("VERIFY PROBE OK", log.read_text(encoding="utf-8"))

    def test_relative_and_repository_logs_are_rejected(self) -> None:
        relative = self.run_verify(log="relative.log")
        self.assertNotEqual(0, relative.returncode)
        self.assertIn("절대 경로", relative.stderr)
        inside = self.copy / "inside.log"
        repository = self.run_verify(log=inside)
        self.assertNotEqual(0, repository.returncode)
        self.assertIn("저장소 밖", repository.stderr)
        self.assertFalse(inside.exists())

    def test_preexisting_log_is_not_truncated(self) -> None:
        log = self.base / "existing.log"
        log.write_text("do-not-truncate", encoding="utf-8")
        completed = self.run_verify(log=log)
        self.assertNotEqual(0, completed.returncode)
        self.assertIn("이미 존재하거나 symlink", completed.stderr)
        self.assertEqual("do-not-truncate", log.read_text(encoding="utf-8"))

    def test_symlink_log_and_symlink_parent_are_rejected(self) -> None:
        target = self.base / "target.log"
        target.write_text("target", encoding="utf-8")
        link = self.base / "link.log"
        link.symlink_to(target)
        linked = self.run_verify(log=link)
        self.assertNotEqual(0, linked.returncode)
        self.assertIn("이미 존재하거나 symlink", linked.stderr)
        self.assertEqual("target", target.read_text(encoding="utf-8"))

        real_parent = self.base / "real-parent"
        real_parent.mkdir()
        alias = self.base / "parent-alias"
        alias.symlink_to(real_parent, target_is_directory=True)
        parent_result = self.run_verify(log=alias / "new.log")
        self.assertNotEqual(0, parent_result.returncode)
        self.assertIn("symlink 경로", parent_result.stderr)
        self.assertFalse((real_parent / "new.log").exists())

    def test_hup_int_and_term_are_nonzero_and_remove_temp(self) -> None:
        signals = ((signal.SIGHUP, 129), (signal.SIGINT, 130), (signal.SIGTERM, 143))
        for index, (sent, expected) in enumerate(signals):
            with self.subTest(signal=sent):
                log = self.base / f"signal-{index}.log"
                environment = os.environ.copy()
                environment.update(
                    VERIFY_LOG=str(log),
                    VERIFY_SAFETY_PROBE="wait",
                    PYTHONDONTWRITEBYTECODE="1",
                )
                process = subprocess.Popen(
                    ["sh", "verify.sh"],
                    cwd=self.copy,
                    env=environment,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                )
                assert process.stdout is not None
                temporary_path: Path | None = None
                deadline = time.monotonic() + 10
                while time.monotonic() < deadline:
                    line = process.stdout.readline()
                    if line.startswith("VERIFY PROBE READY "):
                        temporary_path = Path(line.strip().split(" ", 3)[-1])
                        break
                    if process.poll() is not None:
                        break
                self.assertIsNotNone(temporary_path, "verify probe did not become ready")
                process.send_signal(sent)
                stdout, stderr = process.communicate(timeout=8)
                self.assertEqual(expected, process.returncode, stdout + stderr)
                assert temporary_path is not None
                self.assertFalse(temporary_path.exists(), f"temporary directory leaked: {temporary_path}")

    def test_timeout_runner_kills_the_child_process_group(self) -> None:
        pid_file = self.base / "child.pid"
        code = (
            "import os,time,pathlib; "
            f"pathlib.Path({str(pid_file)!r}).write_text(str(os.getpid())); "
            "time.sleep(30)"
        )
        completed = subprocess.run(
            [
                sys.executable,
                str(self.copy / "scripts/run_with_timeout.py"),
                "--timeout",
                "0.2",
                "--",
                sys.executable,
                "-c",
                code,
            ],
            capture_output=True,
            text=True,
            timeout=8,
            check=False,
        )
        self.assertEqual(124, completed.returncode, completed.stdout + completed.stderr)
        self.assertIn("TIMEOUT", completed.stderr)
        child_pid = int(pid_file.read_text(encoding="utf-8"))
        with self.assertRaises(ProcessLookupError):
            os.kill(child_pid, 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
