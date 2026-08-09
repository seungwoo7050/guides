#!/usr/bin/env python3
"""Black-box public contract checks for a Relay Arena implementation CLI."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parent
INPUTS = PROJECT / "inputs"
EXPECTED = PROJECT / "reference" / "expected-contract.json"


class ContractFailure(AssertionError):
    pass


def run(implementation: Path, args: list[str], *, expect_success: bool = True) -> subprocess.CompletedProcess[str]:
    result = subprocess.run([sys.executable, str(implementation), *args], text=True, capture_output=True, check=False)
    if expect_success and result.returncode != 0:
        raise ContractFailure(f"command failed: {result.stdout}\n{result.stderr}")
    if not expect_success and result.returncode == 0:
        raise ContractFailure("known-invalid command unexpectedly succeeded")
    return result


def read(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def simulate(implementation: Path, temp: Path, schedule: str, scenario: str = "normal") -> dict[str, Any]:
    output = temp / f"{schedule}-{scenario}.json"
    run(
        implementation,
        ["simulate", "--inputs", str(INPUTS), "--schedule", schedule, "--scenario", scenario, "--output", str(output)],
    )
    return read(output)


def check_complete(implementation: Path) -> None:
    with tempfile.TemporaryDirectory(prefix="relay-contract-") as raw:
        temp = Path(raw)
        smooth = simulate(implementation, temp, "smooth")
        jittered = simulate(implementation, temp, "jittered")
        hitch = simulate(implementation, temp, "hitch")
        expected = read(EXPECTED)
        if len({smooth["canonical_state_hash"], jittered["canonical_state_hash"], hitch["canonical_state_hash"]}) != 1:
            raise ContractFailure("frame schedules changed canonical gameplay state")
        if smooth["canonical_state_hash"] != expected["canonical_state_hash"]:
            raise ContractFailure("normal path differs from the published public-behavior oracle")
        if smooth["state"]["active_cores"] != expected["active_cores"]:
            raise ContractFailure("normal command path did not activate all cores")
        if smooth["state"]["result_commit_ids"] != expected["result_commit_ids"]:
            raise ContractFailure("match result was not committed exactly once")
        if smooth["replay_evidence"]["first_divergent_checkpoint_tick"] != expected["first_divergent_checkpoint_tick"]:
            raise ContractFailure("known-bad replay did not diverge first at checkpoint tick 60")
        if smooth["replay_evidence"]["first_divergent_checkpoint_tick"] != smooth["replay_evidence"][
            "expected_first_affected_checkpoint_tick"
        ]:
            raise ContractFailure("replay evidence disagrees with the published fixture contract")
        if hitch["frame_evidence"]["max_steps_per_frame"] > 4 or hitch["frame_evidence"]["dropped_simulation_us"] <= 0:
            raise ContractFailure("hitch did not exercise bounded catch-up")

        duplicate = simulate(implementation, temp, "smooth", "duplicate")
        non_owner = simulate(implementation, temp, "smooth", "non-owner")
        if duplicate["canonical_state_hash"] != smooth["canonical_state_hash"]:
            raise ContractFailure("duplicate command changed canonical state")
        if "duplicate_or_stale" not in {item["reason"] for item in duplicate["rejected_commands"]}:
            raise ContractFailure("duplicate command was not rejected")
        if "non_owner" not in {item["reason"] for item in non_owner["rejected_commands"]}:
            raise ContractFailure("non-owner command was not rejected")
        required_authority_rejections = set(expected["required_authority_rejections"])
        if not required_authority_rejections.issubset(smooth["authority_evidence"]["rejected"]):
            raise ContractFailure("authority trace did not reject every required invalid transition")

        stale = simulate(implementation, temp, "smooth", "stale-load")
        missing = simulate(implementation, temp, "smooth", "missing-cosmetic")
        if stale["resource_evidence"]["stale_completions_rejected"] != 1:
            raise ContractFailure("stale load completion was not rejected")
        if not stale["resource_evidence"]["resource_baseline_restored"]:
            raise ContractFailure("resource baseline was not restored")
        if not missing["resource_evidence"]["control_ready"] or not missing["resource_evidence"]["degraded"]:
            raise ContractFailure("optional cosmetic failure did not degrade safely")

        migrated_path = temp / "save-v2.json"
        run(
            implementation,
            [
                "migrate-save",
                "--input",
                str(INPUTS / "save-v1.json"),
                "--contract",
                str(INPUTS / "save-v2-contract.json"),
                "--output",
                str(migrated_path),
            ],
        )
        migrated = read(migrated_path)
        if migrated["schema_version"] != 2 or migrated["payload"]["best_time_ms"] != 51_720:
            raise ContractFailure("save migration lost version or best time")
        sentinel = temp / "preserved.json"
        sentinel.write_text('{"preserve":true}\n', encoding="utf-8")
        corrupt = temp / "corrupt.json"
        corrupt.write_text("{not-json", encoding="utf-8")
        run(
            implementation,
            [
                "migrate-save",
                "--input",
                str(corrupt),
                "--contract",
                str(INPUTS / "save-v2-contract.json"),
                "--output",
                str(sentinel),
            ],
            expect_success=False,
        )
        if sentinel.read_text(encoding="utf-8") != '{"preserve":true}\n':
            raise ContractFailure("failed migration overwrote the previous save")

        profile_path = temp / "profile.json"
        run(implementation, ["profile", "--inputs", str(INPUTS), "--output", str(profile_path)])
        profile = read(profile_path)
        if profile["after"]["dependency_visits"] >= profile["before"]["dependency_visits"]:
            raise ContractFailure("profile fix did not reduce the reproduced hotspot")
        if not profile["invariants_preserved"]:
            raise ContractFailure("profile fix did not preserve gameplay invariants")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--implementation", type=Path, required=True)
    parser.add_argument("--expect", choices=("pass", "incomplete"), default="pass")
    args = parser.parse_args()
    try:
        check_complete(args.implementation)
    except (ContractFailure, KeyError, OSError, json.JSONDecodeError) as exc:
        if args.expect == "incomplete":
            print(f"EXPECTED_INCOMPLETE {exc}")
            return 0
        print(f"CAPSTONE_CONTRACT_ERROR {exc}", file=sys.stderr)
        return 1
    if args.expect == "incomplete":
        print("CAPSTONE_CONTRACT_ERROR starter unexpectedly passed", file=sys.stderr)
        return 1
    print("CAPSTONE_CONTRACT_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
