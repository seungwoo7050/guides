#!/usr/bin/env python3
from __future__ import annotations

import csv
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PYTHON = sys.executable


def run_expect_failure(command: list[str], *, contains: str | None = None) -> None:
    completed = subprocess.run(command, cwd=ROOT, text=True, capture_output=True, check=False)
    if completed.returncode == 0:
        raise AssertionError(f"mutation was accepted: {' '.join(command)}")
    combined = completed.stdout + completed.stderr
    if contains is not None and contains not in combined:
        raise AssertionError(f"failure did not mention {contains!r}: {combined}")


def update_fixture_hash(fixtures: Path, name: str) -> None:
    manifest_path = fixtures / "fixture-manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["files"][name] = hashlib.sha256((fixtures / name).read_bytes()).hexdigest()
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def split_overlap_mutation(temporary: Path) -> None:
    fixtures = temporary / "fixtures-overlap"
    shutil.copytree(ROOT / "exercises/model-lifecycle/fixtures", fixtures)
    manifest_path = fixtures / "split_manifest.csv"
    with manifest_path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
        fieldnames = list(rows[0].keys())
    first_entity = rows[0]["entity_id"]
    original_split = rows[0]["split"]
    for row in rows:
        if row["entity_id"] == first_entity and row["split"] == original_split:
            row["split"] = "test" if original_split != "test" else "train"
            break
    with manifest_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    update_fixture_hash(fixtures, "split_manifest.csv")
    run_expect_failure(
        [PYTHON, "scripts/verify-fixtures.py", "--fixtures-dir", str(fixtures), "--skip-regeneration"],
        contains="invalid split audit",
    )


def row_count_mutation(temporary: Path) -> None:
    fixtures = temporary / "fixtures-row-count"
    shutil.copytree(ROOT / "exercises/model-lifecycle/fixtures", fixtures)
    dataset = fixtures / "dataset.csv"
    lines = dataset.read_text(encoding="utf-8").splitlines()
    dataset.write_text("\n".join(lines[:-1]) + "\n", encoding="utf-8")
    update_fixture_hash(fixtures, "dataset.csv")
    run_expect_failure(
        [PYTHON, "scripts/verify-fixtures.py", "--fixtures-dir", str(fixtures), "--skip-regeneration"],
        contains="row_count",
    )


def contract_gap_mutation(temporary: Path) -> None:
    source = ROOT / "exercises/model-lifecycle/contracts/stages.json"
    data = json.loads(source.read_text(encoding="utf-8"))
    del data["stages"][3]
    mutated = temporary / "stages-gap.json"
    mutated.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    run_expect_failure([PYTHON, "scripts/verify-contracts.py", "--contracts", str(mutated)], contains="consecutive")


def broken_link_mutation(temporary: Path) -> None:
    copy = temporary / "repo"
    shutil.copytree(
        ROOT,
        copy,
        ignore=shutil.ignore_patterns(".git", ".guide", "workspace", "__pycache__", "*.pyc"),
    )
    with (copy / "README.md").open("a", encoding="utf-8") as handle:
        handle.write("\n[broken](docs/does-not-exist.md)\n")
    run_expect_failure([PYTHON, "scripts/verify-docs.py", "--root", str(copy)], contains="broken link")


def empty_template_mutation(temporary: Path) -> None:
    workspace = temporary / "workspace"
    (workspace / "reports").mkdir(parents=True)
    shutil.copy2(
        ROOT / "exercises/model-lifecycle/templates/problem-statement.md",
        workspace / "reports/problem-contract.md",
    )
    run_expect_failure(
        [PYTHON, "scripts/check-submission.py", "--workspace", str(workspace), "--stage", "1"],
        contains="has no content",
    )


def main() -> int:
    try:
        with tempfile.TemporaryDirectory(prefix="ml-quality-") as raw:
            temporary = Path(raw)
            split_overlap_mutation(temporary)
            row_count_mutation(temporary)
            contract_gap_mutation(temporary)
            broken_link_mutation(temporary)
            empty_template_mutation(temporary)
    except (AssertionError, OSError, json.JSONDecodeError) as exc:
        print(f"ERROR {exc}")
        return 1
    print("QUALITY OK mutations=5")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
