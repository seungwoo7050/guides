#!/usr/bin/env python3
"""Python exercise의 reference 통과와 skeleton 실패를 함께 검증한다."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PYTHON_EXERCISES = [
    (
        "exercises/02-storage-and-indexes/01-slotted-page",
        "test_insert_read_delete_and_slot_reuse",
        "GUIDE_SEMANTIC:slotted-page-insert",
    ),
    (
        "exercises/02-storage-and-indexes/02-bplus-tree",
        "test_insert_search_and_root_growth",
        "GUIDE_SEMANTIC:bplus-tree-insert",
    ),
    (
        "exercises/02-storage-and-indexes/03-buffer-pool-clock",
        "test_cache_hit_avoids_second_disk_read",
        "GUIDE_SEMANTIC:buffer-pool-allocation",
    ),
    (
        "exercises/03-transactions-and-recovery/02-wal-recovery",
        "test_wal_must_be_flushed_before_page",
        "GUIDE_SEMANTIC:wal-update-record",
    ),
    (
        "exercises/04-execution-and-optimization/01-join-algorithms",
        "test_all_algorithms_preserve_bag_semantics",
        "GUIDE_SEMANTIC:join-bag-semantics",
    ),
    (
        "exercises/05-capstones/02-mini-storage-engine",
        "test_insert_get_range_and_duplicate_contract",
        "GUIDE_SEMANTIC:mini-storage-engine",
    ),
]


def run_tests(
    base: Path,
    implementation: str,
    selected_test: str | None = None,
) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(base / implementation)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    command = [sys.executable, "-m", "unittest", "discover", "-s", str(base / "tests"), "-v"]
    if selected_test is not None:
        command.extend(["-k", selected_test])
    return subprocess.run(
        command,
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        timeout=90,
        check=False,
    )


def main() -> int:
    for rel, selected_test, semantic_token in PYTHON_EXERCISES:
        base = ROOT / rel
        reference = run_tests(base, "reference")
        if reference.returncode != 0:
            print(f"[FAIL] reference: {rel}", file=sys.stderr)
            print(reference.stdout, file=sys.stderr)
            print(reference.stderr, file=sys.stderr)
            return 1
        print(f"[PASS] reference: {rel}")

        skeleton = run_tests(base, "skeleton", selected_test)
        if skeleton.returncode == 0:
            print(f"[FAIL] skeleton이 모든 테스트를 통과함: {rel}", file=sys.stderr)
            return 1
        output = f"{skeleton.stdout}\n{skeleton.stderr}"
        infrastructure_errors = (
            "SyntaxError",
            "ImportError",
            "ModuleNotFoundError",
            "AttributeError",
            "ConnectionError",
        )
        if any(token in output for token in infrastructure_errors):
            print(f"[FAIL] skeleton infrastructure failure: {rel}", file=sys.stderr)
            print(output, file=sys.stderr)
            return 1
        expected_failure = f"NotImplementedError: {semantic_token}"
        if skeleton.returncode != 1 or expected_failure not in output:
            print(f"[FAIL] skeleton이 지정된 학습 계약에서 실패하지 않음: {rel}", file=sys.stderr)
            print(output, file=sys.stderr)
            return 1
        print(f"[PASS] skeleton designated semantic failure: {rel} ({semantic_token})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
