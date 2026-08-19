from __future__ import annotations

import csv
import json
import tempfile
import unittest
from pathlib import Path

from planner import analyze

ROOT = Path(__file__).resolve().parents[1]


# [Implementation 7] Planner regression suite
class PlannerTest(unittest.TestCase):
    def test_example_produces_deterministic_prioritized_actions(self) -> None:
        arguments = (
            ROOT / "examples/metrics.csv",
            ROOT / "examples/policy.json",
            ROOT / "examples/components.json",
        )
        first = analyze(*arguments)
        second = analyze(*arguments)
        self.assertEqual(first, second)
        identifiers = [item["id"] for item in first["actions"]]
        self.assertEqual(
            identifiers,
            [
                "component-database-support-expired",
                "database-connection-reserve-violated",
                "disk-capacity-reserve-exhausted",
                "application-oom-restarts-observed",
                "component-docker-engine-support-ending",
                "error-rate-slo-exceeded",
                "latency-slo-exceeded",
                "memory-headroom-below-policy",
                "component-base-image-refresh-required",
            ],
        )
        self.assertTrue(
            all(
                set(item) == {"id", "severity", "evidence", "owner", "deadline", "verification", "rollback"}
                for item in first["actions"]
            )
        )
        self.assertLess(first["derived"]["disk_days_remaining"], 0)
        self.assertEqual(first["window"]["observations"], 30)

    def test_healthy_inputs_produce_no_actions(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            metrics = root / "metrics.csv"
            metrics.write_text(
                "date,host_memory_mb,memory_used_mb,disk_total_gb,disk_used_gb,backup_staging_peak_gb,app_oom_restarts,db_pool_max,db_max_connections,db_admin_reserve,p95_ms,error_rate\n"
                "2026-08-06,4096,2000,100,40,5,0,60,100,20,200,0.001\n"
                "2026-08-07,4096,2000,100,40,5,0,60,100,20,200,0.001\n",
                encoding="utf-8",
            )
            policy = root / "policy.json"
            policy.write_text((ROOT / "examples/policy.json").read_text(), encoding="utf-8")
            components = root / "components.json"
            components.write_text(
                json.dumps(
                    {
                        "as_of": "2026-08-07",
                        "components": [
                            {
                                "name": "runtime",
                                "current_version": "1.0",
                                "latest_approved_version": "1.0",
                                "support_end": "2028-01-01",
                                "last_rebuilt": "2026-08-01",
                                "owner": "release-owner",
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            report = analyze(metrics, policy, components)
            self.assertEqual(report["actions"], [])
            self.assertIsNone(report["derived"]["disk_days_remaining"])

    def test_unsorted_metric_dates_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            metrics = Path(directory) / "metrics.csv"
            rows = list(csv.reader((ROOT / "examples/metrics.csv").read_text(encoding="utf-8").splitlines()))
            rows[1], rows[2] = rows[2], rows[1]
            with metrics.open("w", newline="") as handle:
                csv.writer(handle).writerows(rows)
            with self.assertRaisesRegex(ValueError, "strictly increasing"):
                analyze(metrics, ROOT / "examples/policy.json", ROOT / "examples/components.json")


if __name__ == "__main__":
    unittest.main()
