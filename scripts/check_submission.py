#!/usr/bin/env python3
"""Check machine-verifiable exercise evidence without judging prose as complete."""
from __future__ import annotations

import argparse
import csv
import json
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
ALIASES = {
    "01": "01-time-step-analysis",
    "02": "02-input-command-contract",
    "03": "03-world-lifecycle-review",
    "04": "04-asset-loading-plan",
    "05": "05-save-and-replay-migration",
    "06": "06-authority-and-latency",
    "07": "07-performance-budget-review",
    "08": "08-release-readiness",
}
MANUAL = {
    "01-time-step-analysis": "clock policy, overload trade-off, telemetry sufficiency",
    "02-input-command-contract": "context priority, remapping semantics, cleanup ownership",
    "03-world-lifecycle-review": "ownership rationale, partial cleanup order, repeated-entry evidence",
    "04-asset-loading-plan": "fallback UX, workload representativeness, target capture gaps",
    "05-save-and-replay-migration": "loss policy, rollback rationale, determinism scope",
    "06-authority-and-latency": "player-visible correction, reconnect policy, trust assumptions",
    "07-performance-budget-review": "capture quality, optimization hypothesis, quality/accessibility trade-off",
    "08-release-readiness": "waiver authority, residual risk, rollback and user impact",
}


class SubmissionError(ValueError):
    pass


def read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SubmissionError(f"cannot read {path.name}: {exc}") from exc


def read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    try:
        with path.open(encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            headers = reader.fieldnames or []
            rows = list(reader)
    except (OSError, csv.Error) as exc:
        raise SubmissionError(f"cannot read {path.name}: {exc}") from exc
    if not headers or not rows:
        raise SubmissionError(f"{path.name} requires a header and completed rows")
    return headers, rows


def require_files(submission: Path, names: tuple[str, ...]) -> None:
    for name in names:
        path = submission / name
        if not path.is_file():
            raise SubmissionError(f"missing submission file: {name}")
        if path.suffix in {".md", ".json", ".csv"}:
            text = path.read_text(encoding="utf-8")
            if "TODO" in text or "TODO_INTEGER" in text:
                raise SubmissionError(f"{name} still contains an incomplete marker")


def map_rows(rows: list[dict[str, str]], key_fields: tuple[str, ...], context: str) -> dict[tuple[str, ...], dict[str, str]]:
    result: dict[tuple[str, ...], dict[str, str]] = {}
    for row in rows:
        key = tuple(row.get(field, "") for field in key_fields)
        if not all(key) or key in result:
            raise SubmissionError(f"{context} has missing or duplicate key {key}")
        result[key] = row
    return result


def compare_csv_subset(
    actual_path: Path,
    reference_path: Path,
    key_fields: tuple[str, ...],
    compared_fields: tuple[str, ...],
) -> None:
    actual_headers, actual_rows = read_csv(actual_path)
    reference_headers, reference_rows = read_csv(reference_path)
    required_headers = set(key_fields + compared_fields)
    if not required_headers.issubset(actual_headers) or not required_headers.issubset(reference_headers):
        raise SubmissionError(f"{actual_path.name} is missing public contract columns")
    actual = map_rows(actual_rows, key_fields, actual_path.name)
    reference = map_rows(reference_rows, key_fields, reference_path.name)
    for key, expected in reference.items():
        row = actual.get(key)
        if row is None:
            raise SubmissionError(f"{actual_path.name} is missing required row {key}")
        for field in compared_fields:
            if row.get(field) != expected.get(field):
                raise SubmissionError(
                    f"{actual_path.name} row {key} field {field}: expected {expected.get(field)!r}, got {row.get(field)!r}"
                )


def check_01(submission: Path, reference: Path) -> None:
    require_files(submission, ("analysis.md", "frame-analysis.csv"))
    compare_csv_subset(
        submission / "frame-analysis.csv",
        reference / "frame-analysis.csv",
        ("frame",),
        (
            "raw_delta_us",
            "clamped_delta_us",
            "accumulator_before_us",
            "executed_ticks",
            "consumed_sequences",
            "accumulator_after_us",
            "dropped_us",
        ),
    )


def check_02(submission: Path, reference: Path) -> None:
    require_files(submission, ("input-contract.md", "command-trace.json"))
    actual = read_json(submission / "command-trace.json")
    expected = read_json(reference / "command-trace.json")
    if actual.get("tick_assignment") != expected.get("tick_assignment"):
        raise SubmissionError("command trace tick-assignment contract differs")
    actual_commands = [
        {key: item.get(key) for key in ("tick", "player", "sequence", "channel", "kind", "value", "source_event_sequences")}
        for item in actual.get("commands", [])
    ]
    expected_commands = [
        {key: item.get(key) for key in ("tick", "player", "sequence", "channel", "kind", "value", "source_event_sequences")}
        for item in expected["commands"]
    ]
    if actual_commands != expected_commands:
        raise SubmissionError("command trace does not preserve the public event-to-command behavior")
    actual_decisions = [
        {key: item.get(key) for key in ("source_event_sequence", "resolved_action", "disposition", "command_sequence")}
        for item in actual.get("event_decisions", [])
    ]
    expected_decisions = [
        {key: item.get(key) for key in ("source_event_sequence", "resolved_action", "disposition", "command_sequence")}
        for item in expected["event_decisions"]
    ]
    if actual_decisions != expected_decisions:
        raise SubmissionError("raw-event disposition differs from the fixture contract")
    neutral_players = {
        item.get("player")
        for item in actual.get("synthetic_cleanup_events", [])
        if item.get("kind") == "move" and item.get("value") == [0.0, 0.0]
    }
    if neutral_players != {"player-a", "player-b"}:
        raise SubmissionError("focus loss must neutralize both local players")


def check_03(submission: Path, reference: Path) -> None:
    require_files(submission, ("lifecycle-review.md", "owner-map.csv"))
    compare_csv_subset(
        submission / "owner-map.csv",
        reference / "owner-map.csv",
        ("object_or_state",),
        ("scope", "owner", "stable_identity", "runtime_generation"),
    )


def check_04(submission: Path, reference: Path) -> None:
    require_files(submission, ("loading-plan.md", "budget-review.csv"))
    compare_csv_subset(
        submission / "budget-review.csv",
        reference / "budget-review.csv",
        ("target", "scenario"),
        (
            "cpu_baseline_mib",
            "cpu_added_mib",
            "cpu_peak_mib",
            "gpu_baseline_mib",
            "gpu_added_mib",
            "gpu_peak_mib",
            "transient_peak_mib",
            "within_budget",
        ),
    )


def check_05(submission: Path, reference: Path) -> None:
    require_files(submission, ("migration-plan.md", "divergence-report.md", "evidence.json"))
    actual = read_json(submission / "evidence.json")
    expected = read_json(reference / "evidence.json")
    if actual != expected:
        raise SubmissionError("migration or replay evidence differs from the public fixture result")


def check_06(submission: Path, reference: Path) -> None:
    require_files(submission, ("authority-review.md", "fault-matrix.csv"))
    compare_csv_subset(
        submission / "fault-matrix.csv",
        reference / "fault-matrix.csv",
        ("case",),
        ("expected_server_state", "expected_client_state", "pass_condition"),
    )


def check_07(submission: Path, reference: Path) -> None:
    require_files(submission, ("performance-review.md", "budget-decision.csv"))
    compare_csv_subset(
        submission / "budget-decision.csv",
        reference / "budget-decision.csv",
        ("metric",),
        ("budget", "observed", "percentile_or_marker", "pass", "evidence"),
    )


def check_08(submission: Path, reference: Path) -> None:
    require_files(submission, ("release-review.md", "gate-matrix.csv"))
    compare_csv_subset(
        submission / "gate-matrix.csv",
        reference / "gate-matrix.csv",
        ("gate",),
        ("status", "evidence_id", "evidence_build", "blocking_condition"),
    )


CHECKERS: dict[str, Callable[[Path, Path], None]] = {
    "01-time-step-analysis": check_01,
    "02-input-command-contract": check_02,
    "03-world-lifecycle-review": check_03,
    "04-asset-loading-plan": check_04,
    "05-save-and-replay-migration": check_05,
    "06-authority-and-latency": check_06,
    "07-performance-budget-review": check_07,
    "08-release-readiness": check_08,
}


def check_submission(slug: str, submission: Path) -> None:
    reference = ROOT / "exercises" / slug / "reference"
    CHECKERS[slug](submission, reference)


def mutate(slug: str, submission: Path) -> None:
    if slug == "01-time-step-analysis":
        path = submission / "frame-analysis.csv"
        text = path.read_text(encoding="utf-8").replace(",3330,33334,", ",3330,0,", 1)
        path.write_text(text, encoding="utf-8")
    elif slug == "02-input-command-contract":
        path = submission / "command-trace.json"
        value = read_json(path)
        value["commands"].pop()
        path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    elif slug == "03-world-lifecycle-review":
        path = submission / "owner-map.csv"
        lines = path.read_text(encoding="utf-8").splitlines()
        path.write_text("\n".join(lines[:-1]) + "\n", encoding="utf-8")
    elif slug == "04-asset-loading-plan":
        path = submission / "budget-review.csv"
        path.write_text(path.read_text(encoding="utf-8").replace(",no,", ",yes,", 1), encoding="utf-8")
    elif slug == "05-save-and-replay-migration":
        path = submission / "evidence.json"
        value = read_json(path)
        value["replay"]["first_unequal_checkpoint_tick"] = 5
        path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    elif slug == "06-authority-and-latency":
        path = submission / "fault-matrix.csv"
        lines = path.read_text(encoding="utf-8").splitlines()
        path.write_text("\n".join(line for line in lines if ",duplicate_command," not in line) + "\n", encoding="utf-8")
    elif slug == "07-performance-budget-review":
        path = submission / "budget-decision.csv"
        path.write_text(path.read_text(encoding="utf-8").replace(",false,medium,frame-samples.csv", ",true,medium,frame-samples.csv", 1), encoding="utf-8")
    else:
        path = submission / "gate-matrix.csv"
        text = path.read_text(encoding="utf-8").replace("suspend_result_commit,handheld-linux,fail,", "suspend_result_commit,handheld-linux,pass,", 1)
        path.write_text(text, encoding="utf-8")


def self_test() -> None:
    for slug in CHECKERS:
        base = ROOT / "exercises" / slug
        check_submission(slug, base / "reference")
        try:
            check_submission(slug, base / "template")
        except SubmissionError:
            pass
        else:
            raise SubmissionError(f"{slug}: incomplete template unexpectedly passed")
        with tempfile.TemporaryDirectory(prefix=f"submission-mutant-{slug[:2]}-") as raw:
            mutant = Path(raw) / "submission"
            shutil.copytree(base / "reference", mutant)
            mutate(slug, mutant)
            try:
                check_submission(slug, mutant)
            except SubmissionError:
                pass
            else:
                raise SubmissionError(f"{slug}: known-bad mutant unexpectedly passed")


def main() -> int:
    parser = argparse.ArgumentParser(description="Check machine-verifiable game-development exercise evidence")
    parser.add_argument("--exercise", choices=tuple(ALIASES) + tuple(CHECKERS))
    parser.add_argument("--submission", type=Path)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    try:
        if args.self_test:
            if args.exercise or args.submission:
                raise SubmissionError("--self-test cannot be combined with submission arguments")
            self_test()
            print(f"SUBMISSION_SELF_TEST_OK references={len(CHECKERS)} templates_rejected={len(CHECKERS)} mutants_rejected={len(CHECKERS)}")
            return 0
        if not args.exercise or args.submission is None:
            raise SubmissionError("--exercise and --submission are required")
        slug = ALIASES.get(args.exercise, args.exercise)
        check_submission(slug, args.submission.resolve())
    except SubmissionError as exc:
        print(f"SUBMISSION_ERROR {exc}", file=sys.stderr)
        return 1
    print(f"AUTOMATED_OK exercise={slug}")
    print(f"MANUAL_REVIEW_REQUIRED {MANUAL[slug]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
