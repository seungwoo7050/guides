from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "examples"))

import split_audit  # noqa: E402


class SplitAuditTests(unittest.TestCase):
    def test_valid_entity_disjoint_split(self) -> None:
        rows = [
            {"row_id": "r1", "entity_id": "e1", "churn_30d": "0"},
            {"row_id": "r2", "entity_id": "e1", "churn_30d": "1"},
            {"row_id": "r3", "entity_id": "e2", "churn_30d": "0"},
        ]
        manifest = [
            {"row_id": "r1", "split": "train"},
            {"row_id": "r2", "split": "train"},
            {"row_id": "r3", "split": "test"},
        ]
        result = split_audit.audit_rows(rows, manifest)
        self.assertTrue(result.valid)
        self.assertEqual(result.rows["train"], 2)

    def test_entity_overlap_is_rejected(self) -> None:
        rows = [
            {"row_id": "r1", "entity_id": "e1", "churn_30d": "0"},
            {"row_id": "r2", "entity_id": "e1", "churn_30d": "1"},
        ]
        manifest = [
            {"row_id": "r1", "split": "train"},
            {"row_id": "r2", "split": "test"},
        ]
        result = split_audit.audit_rows(rows, manifest)
        self.assertFalse(result.valid)
        self.assertEqual(result.entity_overlap, ["e1"])
