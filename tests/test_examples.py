from __future__ import annotations

import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from examples.cdc_merge import Change, Position, SnapshotRow, materialize
from examples.lineage_model import Dataset, build_event
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

    def test_optional_writer_cannot_satisfy_required_reader_without_default(self) -> None:
        writer = [Field("id", "string", required=False)]
        required_reader = [Field("id", "string", required=True)]
        defaulted_reader = [Field("id", "string", required=True, default="unknown", has_default=True)]

        incompatible = compare(writer, required_reader)
        self.assertFalse(incompatible.backward)
        self.assertIn("writer may omit field required by reader: id", incompatible.backward_reasons)
        self.assertTrue(compare(writer, defaulted_reader).backward)

    def test_invalid_or_duplicate_field_contract_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            compare([Field("id", "mystery")], [Field("id", "mystery")])
        with self.assertRaises(ValueError):
            compare([Field("id", "string"), Field("id", "string")], [])


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

    def test_conflicting_duplicate_event_is_rejected_in_any_order(self) -> None:
        first = {"event_id": "e1", "sales_date": "2026-08-09", "currency": "KRW", "amount_minor": 100}
        conflict = {**first, "amount_minor": 999}
        for records in ([first, conflict], [conflict, first]):
            with self.subTest(records=records), self.assertRaises(ValueError):
                aggregate(records)

    def test_invalid_amount_is_not_coerced(self) -> None:
        with self.assertRaises(ValueError):
            aggregate(
                [{"event_id": "e1", "sales_date": "2026-08-09", "currency": "KRW", "amount_minor": True}]
            )

    def test_snapshot_identity_is_row_order_and_logical_interval_aware(self) -> None:
        rows = [
            {"sales_date": "2026-08-09", "currency": "USD", "net_amount_minor": 7},
            {"sales_date": "2026-08-09", "currency": "KRW", "net_amount_minor": 150},
        ]
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            first = publish_snapshot(root, "d=2026-08-09", rows)
            replay = publish_snapshot(root, "d=2026-08-09", list(reversed(rows)))
            next_interval = publish_snapshot(root, "d=2026-08-10", rows)
            self.assertEqual(first, replay)
            self.assertNotEqual(first, next_interval)
            self.assertEqual(len(list((root / "snapshots").iterdir())), 2)

    def test_corrupt_existing_snapshot_is_rejected_before_pointer_update(self) -> None:
        rows = [{"sales_date": "2026-08-09", "currency": "KRW", "net_amount_minor": 100}]
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            content_id = publish_snapshot(root, "d=2026-08-09", rows)
            (root / "snapshots" / content_id / "data.json").write_text("[]\n", encoding="utf-8")
            (root / "CURRENT").write_text("previous\n", encoding="utf-8")
            with self.assertRaises(ValueError):
                publish_snapshot(root, "d=2026-08-09", rows)
            self.assertEqual((root / "CURRENT").read_text(encoding="utf-8"), "previous\n")

    def test_current_reader_rejects_manifest_corruption(self) -> None:
        rows = [{"sales_date": "2026-08-09", "currency": "KRW", "net_amount_minor": 100}]
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            content_id = publish_snapshot(root, "d=2026-08-09", rows)
            manifest = root / "snapshots" / content_id / "manifest.json"
            value = json.loads(manifest.read_text(encoding="utf-8"))
            value["row_count"] = 999
            manifest.write_text(json.dumps(value), encoding="utf-8")
            with self.assertRaises(ValueError):
                read_current(root)

    def test_snapshot_inputs_must_be_explicit_json_contracts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with self.assertRaises(ValueError):
                publish_snapshot(root, "", [])
            with self.assertRaises(ValueError):
                publish_snapshot(root, "d=2026-08-09", [{"value": float("nan")}])


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
        self.assertEqual(agg.advance_watermark(datetime(2026, 8, 9, 0, 6, tzinfo=UTC)), [])

    def test_conflicting_duplicate_event_is_rejected_in_batch_and_incremental_paths(self) -> None:
        first = Event("e1", "store", datetime(2026, 8, 9, 0, 1, tzinfo=UTC), 3)
        conflict = Event("e1", "store", datetime(2026, 8, 9, 0, 1, tzinfo=UTC), 4)
        for events in ([first, conflict], [conflict, first]):
            with self.subTest(events=events), self.assertRaises(ValueError):
                closed_totals(events, timedelta(minutes=5))

        agg = FixedWindowAggregator(timedelta(minutes=5), timedelta(hours=1))
        agg.add(first)
        with self.assertRaises(ValueError):
            agg.add(conflict)

    def test_watermark_emits_once_and_pane_identity_tracks_version(self) -> None:
        agg = FixedWindowAggregator(timedelta(minutes=5), timedelta(hours=1))
        early = agg.add(Event("early", "s", datetime(2026, 8, 9, 0, 2, tzinfo=UTC), 3))
        assert early is not None
        on_time = agg.advance_watermark(datetime(2026, 8, 9, 0, 5, tzinfo=UTC))
        self.assertEqual(len(on_time), 1)
        self.assertEqual(on_time[0].completeness, "ON_TIME")
        self.assertEqual(agg.advance_watermark(datetime(2026, 8, 9, 0, 5, tzinfo=UTC)), [])
        self.assertEqual(agg.advance_watermark(datetime(2026, 8, 9, 0, 30, tzinfo=UTC)), [])

        correction = agg.add(Event("late", "s", datetime(2026, 8, 9, 0, 3, tzinfo=UTC), 4))
        assert correction is not None
        self.assertEqual(correction.completeness, "CORRECTED")
        self.assertEqual((early.version, on_time[0].version, correction.version), (1, 2, 3))
        self.assertEqual(len({early.pane_id, on_time[0].pane_id, correction.pane_id}), 3)

        replay = FixedWindowAggregator(timedelta(minutes=5), timedelta(hours=1))
        replay_early = replay.add(Event("early", "s", datetime(2026, 8, 9, 0, 2, tzinfo=UTC), 3))
        assert replay_early is not None
        replay_on_time = replay.advance_watermark(datetime(2026, 8, 9, 0, 5, tzinfo=UTC))[0]
        replay_correction = replay.add(
            Event("late", "s", datetime(2026, 8, 9, 0, 3, tzinfo=UTC), 4)
        )
        assert replay_correction is not None
        self.assertEqual(
            [early.pane_id, on_time[0].pane_id, correction.pane_id],
            [replay_early.pane_id, replay_on_time.pane_id, replay_correction.pane_id],
        )
        self.assertEqual(agg.advance_watermark(datetime(2026, 8, 9, 0, 31, tzinfo=UTC)), [])

    def test_window_and_watermark_boundaries_are_validated(self) -> None:
        with self.assertRaises(ValueError):
            FixedWindowAggregator(timedelta(0), timedelta(0))
        with self.assertRaises(ValueError):
            closed_totals([], timedelta(0))
        with self.assertRaises(ValueError):
            FixedWindowAggregator(timedelta(minutes=5), timedelta(seconds=-1))
        agg = FixedWindowAggregator(timedelta(minutes=5), timedelta(0))
        with self.assertRaises(ValueError):
            agg.advance_watermark(datetime(2026, 8, 9, 0, 5))


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

    def test_same_position_conflicts_are_rejected_in_any_order(self) -> None:
        changes = [
            Change("o1", Position(12), "UPDATE", {"status": "A"}),
            Change("o1", Position(12), "UPDATE", {"status": "B"}),
        ]
        snapshots = [
            SnapshotRow("o1", {"status": "A"}, Position(10)),
            SnapshotRow("o1", {"status": "B"}, Position(10)),
        ]
        for candidate in (changes, list(reversed(changes))):
            with self.subTest(changes=candidate), self.assertRaises(ValueError):
                materialize([], candidate)
        for candidate in (snapshots, list(reversed(snapshots))):
            with self.subTest(snapshots=candidate), self.assertRaises(ValueError):
                materialize(candidate, [])

    def test_identical_same_position_records_are_idempotent(self) -> None:
        snapshot = SnapshotRow("o1", {"status": "NEW"}, Position(10))
        change = Change("o1", Position(11), "UPDATE", {"status": "PAID"})
        self.assertEqual(
            materialize([snapshot, snapshot], [change, change]),
            {"o1": {"status": "PAID"}},
        )

    def test_invalid_stale_change_is_still_rejected(self) -> None:
        snapshot = [SnapshotRow("o1", {"status": "NEW"}, Position(10))]
        with self.assertRaises(ValueError):
            materialize(snapshot, [Change("o1", Position(9), "MYSTERY", None)])
        with self.assertRaises(ValueError):
            materialize(snapshot, [Change("o1", Position(9), "DELETE", {"status": "STALE"})])
        with self.assertRaises(ValueError):
            materialize(snapshot, [Change("o1", Position(True), "DELETE", None)])


class LineageTests(unittest.TestCase):
    def test_event_time_can_be_injected_deterministically(self) -> None:
        observed_at = datetime(2026, 8, 9, 9, 30, tzinfo=timezone(timedelta(hours=9)))
        kwargs = {
            "event_type": "COMPLETE",
            "run_id": "run-1",
            "job_name": "daily-orders",
            "inputs": [Dataset("warehouse", "orders", "snapshot-1")],
            "outputs": [Dataset("mart", "daily_orders", "snapshot-2")],
            "code_revision": "abc123",
            "event_time": observed_at,
        }
        first = build_event(**kwargs)
        second = build_event(**kwargs)
        self.assertEqual(first, second)
        self.assertEqual(first.event_time, "2026-08-09T00:30:00+00:00")

    def test_naive_event_time_and_unknown_event_type_are_rejected(self) -> None:
        common = {
            "run_id": "run-1",
            "job_name": "daily-orders",
            "inputs": [],
            "outputs": [],
            "code_revision": "abc123",
        }
        with self.assertRaises(ValueError):
            build_event(event_type="START", event_time=datetime(2026, 8, 9), **common)
        with self.assertRaises(ValueError):
            build_event(event_type="UNKNOWN", event_time=datetime(2026, 8, 9, tzinfo=UTC), **common)


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
