from __future__ import annotations

import copy
import unittest

from examples.compaction_cost import estimate
from examples.dataset_identity import build_manifest, dataset_identity


class DatasetIdentityTests(unittest.TestCase):
    def arguments(self) -> dict:
        return {
            "product": "daily-revenue",
            "data_interval": "[2026-08-09T00:00:00Z,2026-08-10T00:00:00Z)",
            "source_positions": {"orders": "lsn:120", "payments": "manifest:abc"},
            "code_revision": "git:deadbeef",
            "config": {"timezone": "UTC", "options": {"currency": "minor", "rounding": "half-even"}},
            "schema_versions": {"orders": "avro:17"},
            "reference_versions": {"fx": "snapshot:2026-08-09-r2"},
        }

    def test_mapping_order_does_not_change_identity_or_inputs(self) -> None:
        arguments = self.arguments()
        original = copy.deepcopy(arguments)
        reordered = copy.deepcopy(arguments)
        reordered["source_positions"] = dict(reversed(list(reordered["source_positions"].items())))
        reordered["config"] = {"options": {"rounding": "half-even", "currency": "minor"}, "timezone": "UTC"}

        self.assertEqual(dataset_identity(**arguments), dataset_identity(**reordered))
        self.assertEqual(arguments, original)
        self.assertEqual(build_manifest(**arguments)["source_positions"], arguments["source_positions"])

    def test_each_pinned_execution_layer_changes_identity(self) -> None:
        arguments = self.arguments()
        baseline = dataset_identity(**arguments)
        changes = [
            {"source_positions": {"orders": "lsn:121", "payments": "manifest:abc"}},
            {"code_revision": "git:cafebabe"},
            {"config": {"timezone": "Asia/Seoul"}},
            {"schema_versions": {"orders": "avro:18"}},
            {"reference_versions": {"fx": "snapshot:2026-08-09-r3"}},
        ]
        for change in changes:
            with self.subTest(change=change):
                self.assertNotEqual(baseline, dataset_identity(**{**arguments, **change}))

    def test_floating_versions_and_non_json_config_are_rejected(self) -> None:
        arguments = self.arguments()
        with self.assertRaises(ValueError):
            dataset_identity(**{**arguments, "code_revision": "git:main"})
        with self.assertRaises(ValueError):
            dataset_identity(**{**arguments, "source_positions": {"orders": "latest"}})
        with self.assertRaises(ValueError):
            dataset_identity(**{**arguments, "config": {"bad": object()}})


class CompactionCostTests(unittest.TestCase):
    def test_small_files_trade_metadata_requests_for_rewrite_bytes(self) -> None:
        report = estimate([10, 10, 10, 90], 100)
        self.assertEqual(report["input_files"], 4)
        self.assertEqual(report["output_files"], 2)
        self.assertEqual(report["metadata_requests_saved"], 2)
        self.assertEqual(report["rewrite_bytes"], 30)
        self.assertEqual(report["rewrite_groups"], [{"inputs": [10, 10, 10], "input_bytes": 30, "output_files": 1}])
        self.assertEqual(report["unchanged_files"], [90])

    def test_plan_is_order_independent_and_does_not_mutate_input(self) -> None:
        sizes = [70, 10, 20, 10]
        original = list(sizes)
        self.assertEqual(estimate(sizes, 100), estimate(list(reversed(sizes)), 100))
        self.assertEqual(sizes, original)

    def test_exact_target_and_singleton_are_not_rewritten(self) -> None:
        report = estimate([25, 100, 140], 100)
        self.assertEqual(report["output_files"], 3)
        self.assertEqual(report["metadata_requests_saved"], 0)
        self.assertEqual(report["rewrite_bytes"], 0)

    def test_invalid_sizes_are_rejected(self) -> None:
        for sizes, target in [([True], 100), ([-1], 100), ([1], True), ([1], 0)]:
            with self.subTest(sizes=sizes, target=target):
                with self.assertRaises(ValueError):
                    estimate(sizes, target)


if __name__ == "__main__":
    unittest.main()
