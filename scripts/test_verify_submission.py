#!/usr/bin/env python3
from __future__ import annotations

import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
ROOT = SCRIPT_DIR.parent
sys.path.insert(0, str(SCRIPT_DIR))

from verify_submission import ContractError, load_json, validate  # noqa: E402


def contract_fixture() -> dict:
    return {
        'schemaVersion': 2,
        'title': 'Verifier meta contract',
        'requiredPaths': ['/status', '/name', '/other', '/mirror', '/items', '/tags', '/count'],
        'nonEmptyPaths': ['/name'],
        'minimumItems': {'/items': 2},
        'arrayItemRequiredFields': {'/items': ['label', 'kind', 'enabled']},
        'arrayUniqueBy': {'/items': 'label'},
        'containsValues': {'/tags': ['normal', 'failure']},
        'allowedValues': {'/status': ['complete']},
        'matches': {'/name': '[a-z-]+'},
        'forbiddenSubstrings': ['TODO'],
        'valueTypes': {
            '/status': 'string',
            '/count': 'integer',
            '/items/*/enabled': 'boolean',
        },
        'arrayContainsObjects': {
            '/items': [
                {'kind': 'normal', 'enabled': True},
                {'kind': 'failure', 'enabled': False},
            ]
        },
        'pathComparisons': [
            {'left': '/name', 'op': 'eq', 'right': '/mirror'},
            {'left': '/name', 'op': 'ne', 'right': '/other'},
        ],
        'conditionalRequirements': [
            {
                'if': {'path': '/status', 'equals': 'complete'},
                'then': {
                    'requiredPaths': ['/evidence'],
                    'nonEmptyPaths': ['/evidence'],
                    'valueTypes': {'/evidence': 'string'},
                },
            }
        ],
    }


def submission_fixture() -> dict:
    return {
        'status': 'complete',
        'name': 'platform-path',
        'other': 'different-path',
        'mirror': 'platform-path',
        'count': 2,
        'items': [
            {'label': 'ok', 'kind': 'normal', 'enabled': True},
            {'label': 'deny', 'kind': 'failure', 'enabled': False},
        ],
        'tags': ['normal', 'failure'],
        'evidence': 'trace-123',
    }


class ValidationPrimitiveTests(unittest.TestCase):
    def test_all_v2_primitives_accept_valid_submission(self) -> None:
        self.assertEqual(validate(contract_fixture(), submission_fixture()), [])

    def test_value_types_reject_boolean_lookalike(self) -> None:
        submission = submission_fixture()
        submission['items'][0]['enabled'] = 'true'
        self.assertTrue(any('type' in error for error in validate(contract_fixture(), submission)))

    def test_array_contains_objects_rejects_missing_category(self) -> None:
        submission = submission_fixture()
        submission['items'][1]['kind'] = 'normal'
        self.assertTrue(
            any('category/invariant' in error for error in validate(contract_fixture(), submission))
        )

    def test_path_comparisons_enforce_eq_and_ne(self) -> None:
        eq_submission = submission_fixture()
        eq_submission['mirror'] = 'not-the-name'
        self.assertTrue(any('경로 비교' in error for error in validate(contract_fixture(), eq_submission)))

        ne_submission = submission_fixture()
        ne_submission['other'] = ne_submission['name']
        self.assertTrue(any('경로 비교' in error for error in validate(contract_fixture(), ne_submission)))

    def test_conditional_requirements_apply_only_when_triggered(self) -> None:
        submission = submission_fixture()
        del submission['evidence']
        self.assertTrue(any('/evidence' in error for error in validate(contract_fixture(), submission)))

        contract = contract_fixture()
        contract['allowedValues']['/status'] = ['draft']
        submission['status'] = 'draft'
        self.assertEqual(validate(contract, submission), [])

        contract['conditionalRequirements'][0]['if'] = {
            'path': '/status',
            'notEquals': 'complete',
        }
        self.assertTrue(any('/evidence' in error for error in validate(contract, submission)))

    def test_unknown_contract_key_is_contract_error(self) -> None:
        contract = contract_fixture()
        contract['surprise'] = True
        with self.assertRaises(ContractError):
            validate(contract, submission_fixture())

    def test_invalid_rule_shape_is_contract_error(self) -> None:
        contract = contract_fixture()
        contract['pathComparisons'][0]['op'] = 'approximately'
        with self.assertRaises(ContractError):
            validate(contract, submission_fixture())


class CliExitCodeTests(unittest.TestCase):
    def run_cli(self, contract_text: str, submission_text: str) -> subprocess.CompletedProcess[str]:
        with tempfile.TemporaryDirectory() as directory:
            temp = Path(directory)
            contract_path = temp / 'contract.json'
            submission_path = temp / 'submission.json'
            contract_path.write_text(contract_text, encoding='utf-8')
            submission_path.write_text(submission_text, encoding='utf-8')
            return subprocess.run(
                [sys.executable, '-B', str(SCRIPT_DIR / 'verify_submission.py'), str(contract_path), str(submission_path)],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )

    def valid_json(self) -> tuple[str, str]:
        return (
            json.dumps(contract_fixture(), ensure_ascii=False),
            json.dumps(submission_fixture(), ensure_ascii=False),
        )

    def test_exit_zero_for_pass_and_one_for_rejection(self) -> None:
        contract_text, submission_text = self.valid_json()
        passed = self.run_cli(contract_text, submission_text)
        self.assertEqual(passed.returncode, 0, passed.stderr)

        rejected_submission = copy.deepcopy(submission_fixture())
        rejected_submission['status'] = 'incomplete'
        rejected = self.run_cli(
            contract_text,
            json.dumps(rejected_submission, ensure_ascii=False),
        )
        self.assertEqual(rejected.returncode, 1, rejected.stderr)
        self.assertIn('REJECTED', rejected.stderr)

    def test_duplicate_keys_have_role_specific_exit_codes(self) -> None:
        contract_text, submission_text = self.valid_json()
        duplicate_contract = contract_text[:-1] + ',"title":"duplicate"}'
        self.assertEqual(self.run_cli(duplicate_contract, submission_text).returncode, 2)

        duplicate_submission = submission_text[:-1] + ',"status":"complete"}'
        self.assertEqual(self.run_cli(contract_text, duplicate_submission).returncode, 1)

    def test_non_finite_numbers_have_role_specific_exit_codes(self) -> None:
        contract_text, submission_text = self.valid_json()
        non_finite_contract = contract_text[:-1] + ',"minimumItems":{"/items":NaN}}'
        self.assertEqual(self.run_cli(non_finite_contract, submission_text).returncode, 2)

        non_finite_submission = submission_text[:-1] + ',"unsafe":Infinity}'
        self.assertEqual(self.run_cli(contract_text, non_finite_submission).returncode, 1)

    def test_malformed_submission_is_rejection(self) -> None:
        contract_text, _ = self.valid_json()
        result = self.run_cli(contract_text, '{"status":')
        self.assertEqual(result.returncode, 1)
        self.assertIn('REJECTED', result.stderr)

    def test_bad_contract_schema_is_harness_error(self) -> None:
        contract = contract_fixture()
        contract['schemaVersion'] = 1
        _, submission_text = self.valid_json()
        result = self.run_cli(json.dumps(contract), submission_text)
        self.assertEqual(result.returncode, 2)
        self.assertIn('ERROR', result.stderr)


class ExerciseFixtureTests(unittest.TestCase):
    def test_all_reference_starter_and_known_bad_outcomes(self) -> None:
        exercises = sorted(
            path for path in (ROOT / 'exercises').iterdir()
            if path.is_dir() and path.name[:2].isdigit() and int(path.name[:2]) <= 12
        )
        self.assertEqual(len(exercises), 12)
        for exercise in exercises:
            with self.subTest(exercise=exercise.name):
                contract = load_json(exercise / 'contract.json')
                reference = load_json(exercise / 'reference/submission.json', submission=True)
                skeleton = load_json(exercise / 'skeleton/submission.json', submission=True)
                known_bad = load_json(exercise / 'known_bad/submission.json', submission=True)

                self.assertEqual(validate(contract, reference), [])
                self.assertNotEqual(validate(contract, skeleton), [])
                self.assertNotEqual(validate(contract, known_bad), [])


if __name__ == '__main__':
    unittest.main()
