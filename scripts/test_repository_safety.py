#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import stat
import tempfile
import unittest
from pathlib import Path

from source_fingerprint import UnsafeTreeError, fingerprint
from verify_isolated import ROOT as ISOLATION_ROOT, external_temp_root
from verify_repository import (
    VerificationError,
    _github_slug,
    _unique_anchor,
    check_yaml_subset,
    strict_json,
    validate_schema,
)


class SourceFingerprintTests(unittest.TestCase):
    def test_mode_and_content_are_part_of_fingerprint(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            path = root / 'file.txt'
            path.write_text('one\n', encoding='utf-8')
            first = fingerprint(root, excluded_dirs=frozenset(), excluded_files=frozenset())
            path.chmod(stat.S_IMODE(path.stat().st_mode) | stat.S_IXUSR)
            second = fingerprint(root, excluded_dirs=frozenset(), excluded_files=frozenset())
            path.write_text('two\n', encoding='utf-8')
            third = fingerprint(root, excluded_dirs=frozenset(), excluded_files=frozenset())
            self.assertNotEqual(first, second)
            self.assertNotEqual(second, third)

    def test_file_boundaries_are_length_framed(self) -> None:
        with tempfile.TemporaryDirectory() as first_directory, tempfile.TemporaryDirectory() as second_directory:
            first = Path(first_directory)
            second = Path(second_directory)
            (first / 'a').write_bytes(b'A')
            (first / 'b').write_bytes(b'\0b\0' + b'644' + b'\0B')
            (second / 'a').write_bytes(b'A\0b\0' + b'644' + b'\0')
            (second / 'b').write_bytes(b'B')
            for path in (*first.iterdir(), *second.iterdir()):
                path.chmod(0o644)
            first_hash = fingerprint(first, excluded_dirs=frozenset(), excluded_files=frozenset())
            second_hash = fingerprint(second, excluded_dirs=frozenset(), excluded_files=frozenset())
            self.assertNotEqual(first_hash, second_hash)

    def test_empty_directory_and_directory_mode_are_fingerprinted(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            first = fingerprint(root, excluded_dirs=frozenset(), excluded_files=frozenset())
            empty = root / 'empty'
            empty.mkdir(mode=0o755)
            second = fingerprint(root, excluded_dirs=frozenset(), excluded_files=frozenset())
            empty.chmod(0o700)
            third = fingerprint(root, excluded_dirs=frozenset(), excluded_files=frozenset())
            self.assertNotEqual(first, second)
            self.assertNotEqual(second, third)

    def test_excluded_workspace_does_not_change_source(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / 'source.txt').write_text('source\n', encoding='utf-8')
            first = fingerprint(root)
            workspace = root / '.workspace'
            workspace.mkdir()
            (workspace / 'learner.json').write_text('{}\n', encoding='utf-8')
            self.assertEqual(first, fingerprint(root))

    def test_git_worktree_pointer_is_excluded(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / 'source.txt').write_text('source\n', encoding='utf-8')
            first = fingerprint(root)
            (root / '.git').write_text('gitdir: /tmp/example\n', encoding='utf-8')
            self.assertEqual(first, fingerprint(root))

    @unittest.skipUnless(hasattr(os, 'symlink'), 'symlink is unavailable')
    def test_symlink_is_rejected_without_following(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / 'target').write_text('value\n', encoding='utf-8')
            os.symlink(root / 'target', root / 'link')
            with self.assertRaises(UnsafeTreeError):
                fingerprint(root, excluded_dirs=frozenset(), excluded_files=frozenset())

    @unittest.skipUnless(hasattr(os, 'symlink'), 'symlink is unavailable')
    def test_excluded_workspace_symlink_is_still_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            outside = root / 'outside'
            outside.mkdir()
            os.symlink(outside, root / '.workspace')
            with self.assertRaises(UnsafeTreeError):
                fingerprint(root)

    @unittest.skipUnless(hasattr(os, 'symlink'), 'symlink is unavailable')
    def test_excluded_ds_store_symlink_is_still_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            target = root / 'target'
            target.write_text('value\n', encoding='utf-8')
            os.symlink(target, root / '.DS_Store')
            with self.assertRaises(UnsafeTreeError):
                fingerprint(root)

    def test_nested_reserved_directory_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            nested = root / 'docs/.workspace'
            nested.mkdir(parents=True)
            (nested / 'hidden.txt').write_text('hidden\n', encoding='utf-8')
            with self.assertRaises(UnsafeTreeError):
                fingerprint(root)

    def test_workspace_mode_includes_nested_git_and_pycache_when_exclusions_are_empty(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            first = fingerprint(root, excluded_dirs=frozenset(), excluded_files=frozenset())
            nested_git = root / 'project/.git'
            nested_git.mkdir(parents=True)
            (nested_git / 'HEAD').write_text('ref: refs/heads/main\n', encoding='utf-8')
            pycache = root / '__pycache__'
            pycache.mkdir()
            (pycache / 'module.pyc').write_bytes(b'learner-cache')
            second = fingerprint(root, excluded_dirs=frozenset(), excluded_files=frozenset())
            self.assertNotEqual(first, second)


class RepositoryPrimitiveTests(unittest.TestCase):
    def test_isolation_temp_root_rejects_repository_internal_candidate(self) -> None:
        selected = external_temp_root([ISOLATION_ROOT, Path('/private/tmp'), Path('/tmp')])
        self.assertNotEqual(selected, ISOLATION_ROOT)
        self.assertNotIn(ISOLATION_ROOT, selected.parents)

    def test_strict_json_rejects_duplicates_and_non_finite_numbers(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / 'input.json'
            path.write_text('{"key": 1, "key": 2}\n', encoding='utf-8')
            with self.assertRaises(VerificationError):
                strict_json(path)
            path.write_text('{"value": NaN}\n', encoding='utf-8')
            with self.assertRaises(VerificationError):
                strict_json(path)

    def test_schema_validator_rejects_known_bad_digest(self) -> None:
        schema = {
            'type': 'object',
            'required': ['digest'],
            'properties': {
                'digest': {'type': 'string', 'pattern': r'^sha256:[a-f0-9]{64}$'},
            },
            'additionalProperties': False,
        }
        validate_schema({'digest': 'sha256:' + ('a' * 64)}, schema)
        with self.assertRaises(VerificationError):
            validate_schema({'digest': 'latest'}, schema)
        with self.assertRaises(VerificationError):
            validate_schema({'digest': 'sha256:' + ('a' * 64), 'extra': True}, schema)

    def test_yaml_subset_rejects_unquoted_mapping_delimiter_in_scalar(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / 'invalid.yaml'
            path.write_text(
                'apiVersion: v1\nkind: ConfigMap\nmetadata:\n  name: checkout: invalid\n',
                encoding='utf-8',
            )
            with self.assertRaises(VerificationError):
                check_yaml_subset([path])

    def test_yaml_subset_accepts_braces_inside_quoted_scalar(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / 'valid.yaml'
            path.write_text(
                'apiVersion: v1\nkind: ConfigMap\ndata:\n  template: "literal { brace"\n',
                encoding='utf-8',
            )
            self.assertEqual(check_yaml_subset([path]), 1)

    def test_yaml_subset_rejects_nested_duplicate_key(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / 'duplicate.yaml'
            path.write_text(
                'apiVersion: v1\nkind: ConfigMap\nmetadata:\n  name: first\n  name: second\n',
                encoding='utf-8',
            )
            with self.assertRaises(VerificationError):
                check_yaml_subset([path])

    def test_heading_slug_is_deterministic_for_korean_and_code(self) -> None:
        self.assertEqual(_github_slug('OWN-1: 플랫폼을 제품으로'), 'own-1-플랫폼을-제품으로')
        self.assertEqual(_github_slug('`Ready` 증거 / 실패'), 'ready-증거--실패')

    def test_heading_slug_collision_does_not_create_duplicate_anchor(self) -> None:
        used: set[str] = set()
        counters: dict[str, int] = {}
        actual = [
            _unique_anchor(base, used, counters)
            for base in ('failure', 'failure', 'failure-1', 'failure')
        ]
        self.assertEqual(actual, ['failure', 'failure-1', 'failure-1-1', 'failure-2'])


if __name__ == '__main__':
    unittest.main()
