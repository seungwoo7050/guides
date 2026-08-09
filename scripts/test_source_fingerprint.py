#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import stat
import tempfile
import unittest
from pathlib import Path

import source_fingerprint as subject


def write(path: Path, data: bytes) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return path


class SourceFingerprintTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="cloud-source-fingerprint-")
        self.root = Path(self.temporary.name) / "guide"
        self.root.mkdir()

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def test_content_path_and_mode_changes_change_digest(self) -> None:
        source = write(self.root / "docs/guide.md", b"first\n")
        baseline = subject.source_fingerprint(self.root)

        source.write_bytes(b"second\n")
        content_changed = subject.source_fingerprint(self.root)
        self.assertNotEqual(baseline, content_changed)

        renamed = source.with_name("renamed.md")
        source.rename(renamed)
        path_changed = subject.source_fingerprint(self.root)
        self.assertNotEqual(content_changed, path_changed)

        current_mode = stat.S_IMODE(renamed.stat().st_mode)
        renamed.chmod(current_mode | stat.S_IXUSR)
        mode_changed = subject.source_fingerprint(self.root)
        self.assertNotEqual(path_changed, mode_changed)

    def test_only_declared_generated_paths_are_ignored(self) -> None:
        write(self.root / "README.md", b"source\n")
        baseline = subject.source_fingerprint(self.root)

        ignored = (
            self.root / ".git/state",
            self.root / ".guide/prepared.json",
            self.root / ".workspace/answer.md",
            self.root / "pkg/__pycache__/module.pyc",
            self.root / "pkg/generated.pyc",
            self.root / "pkg/generated.pyo",
            self.root / "run.log",
            self.root / ".DS_Store",
        )
        for index, path in enumerate(ignored):
            write(path, f"generated-{index}\n".encode())
        self.assertEqual(baseline, subject.source_fingerprint(self.root))

        write(self.root / "pkg/generated.tmp", b"not ignored\n")
        named_file_digest = subject.source_fingerprint(self.root)
        self.assertNotEqual(baseline, named_file_digest)

        write(self.root / "audit.log/evidence.txt", b"directory is learner-authored\n")
        self.assertNotEqual(named_file_digest, subject.source_fingerprint(self.root))

        generated_name_link = self.root / "linked.log"
        generated_name_link.symlink_to("outside")
        with self.assertRaises(subject.FingerprintError) as raised:
            subject.source_fingerprint(self.root)
        self.assertEqual("E_SOURCE_SYMLINK", raised.exception.code)

    def test_source_symlinks_are_rejected_and_target_is_hashable_without_following(self) -> None:
        external = Path(self.temporary.name) / "external"
        write(external / "one.txt", b"same bytes\n")
        write(external / "two.txt", b"same bytes\n")
        link = self.root / "external-link"
        link.symlink_to(external / "one.txt")

        with self.assertRaisesRegex(subject.FingerprintError, "external-link") as raised:
            subject.source_fingerprint(self.root)
        self.assertEqual("E_SOURCE_SYMLINK", raised.exception.code)

        first_target = subject.source_fingerprint(self.root, reject_symlinks=False)
        link.unlink()
        link.symlink_to(external / "two.txt")
        second_target = subject.source_fingerprint(self.root, reject_symlinks=False)
        self.assertNotEqual(first_target, second_target)

        (external / "two.txt").write_bytes(b"changed outside\n")
        self.assertEqual(
            second_target,
            subject.source_fingerprint(self.root, reject_symlinks=False),
            "symlink target bytes must never be followed",
        )

    def _marker_value(self) -> dict[str, object]:
        return {
            "schema_version": 2,
            "fingerprint_version": 2,
            "guide": "cloud-computing",
            "source_fingerprint": subject.source_fingerprint(self.root),
            "python": "3.10.0",
            "network_required": False,
            "required_external_services": [],
        }

    def test_marker_schema_and_source_change_are_checked(self) -> None:
        write(self.root / "README.md", b"source\n")
        marker = self.root / ".guide/cloud-computing/prepared.json"
        marker.parent.mkdir(parents=True)
        value = self._marker_value()
        marker.write_text(json.dumps(value), encoding="utf-8")
        self.assertEqual(value["source_fingerprint"], subject.validate_marker(self.root, marker))

        invalid_values = (
            ("schema", {**value, "schema_version": 1}),
            ("fingerprint-version", {**value, "fingerprint_version": 1}),
            ("guide", {**value, "guide": "other"}),
            ("digest", {**value, "source_fingerprint": "not-a-digest"}),
            ("network", {**value, "network_required": True}),
            ("services", {**value, "required_external_services": ["cloud"]}),
        )
        for label, invalid in invalid_values:
            with self.subTest(label=label):
                marker.write_text(json.dumps(invalid), encoding="utf-8")
                with self.assertRaises(subject.FingerprintError) as raised:
                    subject.validate_marker(self.root, marker)
                self.assertEqual("E_MARKER_SCHEMA", raised.exception.code)

        marker.write_text(json.dumps(value), encoding="utf-8")
        write(self.root / "README.md", b"changed\n")
        with self.assertRaises(subject.FingerprintError) as raised:
            subject.validate_marker(self.root, marker)
        self.assertEqual("E_SOURCE_CHANGED", raised.exception.code)

    def test_marker_symlink_and_outside_path_are_rejected(self) -> None:
        write(self.root / "README.md", b"source\n")
        outside = write(Path(self.temporary.name) / "outside-marker.json", b"{}\n")
        marker = self.root / ".guide/cloud-computing/prepared.json"
        marker.parent.mkdir(parents=True)
        marker.symlink_to(outside)
        with self.assertRaises(subject.FingerprintError) as raised:
            subject.validate_marker(self.root, marker)
        self.assertEqual("E_MARKER_SYMLINK", raised.exception.code)

        with self.assertRaises(subject.FingerprintError) as raised:
            subject.validate_marker(self.root, outside)
        self.assertEqual("E_MARKER_PATH", raised.exception.code)

    def test_workspace_absence_content_path_mode_and_link_target_are_detected(self) -> None:
        absent = subject.workspace_fingerprint(self.root)
        workspace = self.root / ".workspace"
        workspace.mkdir()
        empty = subject.workspace_fingerprint(self.root)
        self.assertNotEqual(absent, empty)

        answer = write(workspace / "capstone/answer.md", b"answer\n")
        content = subject.workspace_fingerprint(self.root)
        answer.write_bytes(b"changed\n")
        changed = subject.workspace_fingerprint(self.root)
        self.assertNotEqual(content, changed)

        renamed = answer.with_name("renamed.md")
        answer.rename(renamed)
        renamed_digest = subject.workspace_fingerprint(self.root)
        self.assertNotEqual(changed, renamed_digest)

        renamed.chmod(stat.S_IMODE(renamed.stat().st_mode) | stat.S_IXUSR)
        mode_digest = subject.workspace_fingerprint(self.root)
        self.assertNotEqual(renamed_digest, mode_digest)

        link = workspace / "capstone/external"
        link.symlink_to("target-one")
        link_one = subject.workspace_fingerprint(self.root)
        link.unlink()
        link.symlink_to("target-two")
        link_two = subject.workspace_fingerprint(self.root)
        self.assertNotEqual(link_one, link_two)

        generated_name = write(workspace / "run.log", b"learner evidence\n")
        log_digest = subject.workspace_fingerprint(self.root)
        self.assertNotEqual(link_two, log_digest)
        generated_name.write_bytes(b"changed learner evidence\n")
        changed_log_digest = subject.workspace_fingerprint(self.root)
        self.assertNotEqual(log_digest, changed_log_digest)

        nested_ignored_name = write(workspace / "nested/.git/answer.txt", b"learner answer\n")
        nested_digest = subject.workspace_fingerprint(self.root)
        self.assertNotEqual(changed_log_digest, nested_digest)
        nested_ignored_name.write_bytes(b"changed learner answer\n")
        self.assertNotEqual(nested_digest, subject.workspace_fingerprint(self.root))


if __name__ == "__main__":
    unittest.main(verbosity=2)
