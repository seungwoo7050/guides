from __future__ import annotations

import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from examples.cdc_merge import Change, Position, SnapshotRow, materialize
from examples.partition_cost import distribution, imbalance_ratio
from examples.quality_report import inspect
from examples.replay_safe_batch import aggregate, build_input_manifest, publish_snapshot, read_current
from examples.schema_compatibility import Field, compare
from examples.windowing_model import Event, FixedWindowAggregator, closed_totals

UTC = timezone.utc


class SchemaCompatibilityTests(unittest.TestCase):
    def test_optional_field_and_widening_are_backward_readable(self) -> None:
        old = [Field("id", "string"), Field("amount", "int")]
        new = [
            Field("id", "string"),
            Field("amount", "long"),
            Field("channel", "string", required=False, has_default=True),
        ]
        result = compare(old, new)
        self.assertTrue(result.backward)
        self.assertFalse(result.forward)  # old reader cannot narrow long to int

    def test_new_required_field_breaks_old_data(self) -> None:
        old = [Field("id", "string")]
        new = [Field("id", "string"), Field("country", "string")]
        self.assertFalse(compare(old, new).backward)


class ReplaySafeBatchTests(unittest.TestCase):
    def test_manifest_is_order_independent(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            a = root / "a.json"
            b = root / "b.json"
            a.write_text("a", encoding="utf-8")
            b.write_text("b", encoding="utf-8")
            self.assertEqual(
                build_input_manifest([a, b])["manifest_id"],
                build_input_manifest([b, a])["manifest_id"],
            )

    def test_duplicate_event_and_republish_are_idempotent(self) -> None:
        records = [
            {"event_id": "e1", "sales_date": "2026-08-09", "currency": "KRW", "amount_minor": 100},
            {"event_id": "e1", "sales_date": "2026-08-09", "currency": "KRW", "amount_minor": 100},
        ]
        rows = aggregate(records)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            first = publish_snapshot(root, "d=2026-08-09", rows)
            second = publish_snapshot(root, "d=2026-08-09", rows)
            self.assertEqual(first, second)
            self.assertEqual(read_current(root), rows)


class WindowingTests(unittest.TestCase):
    def test_arrival_order_does_not_change_closed_totals(self) -> None:
        events = [
            Event("e1", "store", datetime(2026, 8, 9, 0, 1, tzinfo=UTC), 3),
            Event("e2", "store", datetime(2026, 8, 9, 0, 4, tzinfo=UTC), 5),
            Event("e1", "store", datetime(2026, 8, 9, 0, 1, tzinfo=UTC), 3),
        ]
        self.assertEqual(
            closed_totals(events, timedelta(minutes=5)),
            closed_totals(reversed(events), timedelta(minutes=5)),
        )

    def test_late_correction_within_lateness_is_emitted(self) -> None:
        agg = FixedWindowAggregator(timedelta(minutes=5), timedelta(hours=1))
        agg.advance_watermark(datetime(2026, 8, 9, 0, 6, tzinfo=UTC))
        emission = agg.add(Event("late", "s", datetime(2026, 8, 9, 0, 2, tzinfo=UTC), 7))
        self.assertIsNotNone(emission)
        assert emission is not None
        self.assertEqual(emission.completeness, "CORRECTED")


class CdcTests(unittest.TestCase):
    def test_stale_update_does_not_override_newer_state(self) -> None:
        snapshot = [SnapshotRow("o1", {"status": "NEW"}, Position(10))]
        changes = [
            Change("o1", Position(12), "UPDATE", {"status": "PAID"}),
            Change("o1", Position(11), "UPDATE", {"status": "CANCELLED"}),
        ]
        self.assertEqual(materialize(snapshot, changes)["o1"]["status"], "PAID")

    def test_delete_removes_current_state(self) -> None:
        snapshot = [SnapshotRow("o1", {"status": "NEW"}, Position(10))]
        self.assertEqual(materialize(snapshot, [Change("o1", Position(11), "DELETE", None)]), {})


class QualityAndPartitionTests(unittest.TestCase):
    def test_quality_detects_duplicate_and_null(self) -> None:
        report = inspect(
            [
                {"id": "a", "event_time": "2026-08-09T00:00:00Z", "value": 1},
                {"id": "a", "event_time": "2026-08-09T00:01:00Z", "value": None},
            ],
            key_field="id",
            required_fields=("id", "value"),
            event_time_field="event_time",
        )
        self.assertFalse(report.passed)
        self.assertEqual(report.duplicate_keys, ("a",))
        self.assertEqual(report.null_required, 1)

    def test_partition_distribution_covers_all_partitions(self) -> None:
        counts = distribution([f"key-{i}" for i in range(100)], 8)
        self.assertEqual(set(counts), set(range(8)))
        self.assertGreaterEqual(imbalance_ratio(counts), 1.0)


if __name__ == "__main__":
    unittest.main()
