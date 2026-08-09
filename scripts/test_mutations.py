#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys
import time
import uuid


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "exercises"))
import check as exercise_check  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Prove that every declared known-bad mutation is rejected.")
    parser.add_argument("--gpu", choices=("auto", "required", "off"), required=True)
    args = parser.parse_args()
    executable = exercise_check.configure_and_build("reference", args.gpu)
    artifact_root = ROOT / "out/mutations" / f"{int(time.time())}-{uuid.uuid4().hex[:8]}"
    artifact_root.mkdir(parents=True, exist_ok=False)
    checked = 0
    skipped_gpu: list[str] = []

    for stage in exercise_check.STAGES:
        if args.gpu == "off" and stage in exercise_check.GPU_STAGES:
            skipped_gpu.append(stage)
            continue
        contract_path = ROOT / "exercises" / stage / "contract.json"
        contract = json.loads(contract_path.read_text(encoding="utf-8"))
        for mutation in contract["known_bad_mutations"]:
            output = artifact_root / stage / mutation
            command = exercise_check.exercise_command(executable, stage, output, args.gpu, mutation)
            result = subprocess.run(
                command, cwd=ROOT, text=True, stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT, timeout=120, check=False,
            )
            if result.returncode == 5 and args.gpu == "auto" and stage in exercise_check.GPU_STAGES:
                skipped_gpu.append(stage)
                break
            if result.returncode != 4:
                raise exercise_check.CheckFailure(
                    f"{stage}/{mutation}: expected contract-failure exit=4, got {result.returncode}\n"
                    f"{result.stdout}"
                )
            exercise_check.validate_run(stage, output, "fail", mutation)
            checked += 1
            print(f"[REJECTED] {stage}/{mutation}")

    if args.gpu == "required" and skipped_gpu:
        raise exercise_check.CheckFailure(f"required GPU mutation stages skipped: {sorted(set(skipped_gpu))}")
    print(f"MUTATION_TEST_OK checked={checked} gpu={args.gpu} artifacts={artifact_root}")
    if skipped_gpu:
        print(f"GPU_MUTATIONS_NOT_EVALUATED stages={','.join(sorted(set(skipped_gpu)))}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (
        exercise_check.CheckFailure,
        subprocess.TimeoutExpired,
        OSError,
        json.JSONDecodeError,
        KeyError,
        TypeError,
        ValueError,
    ) as error:
        print(f"MUTATION_TEST_ERROR: {error}", file=sys.stderr)
        raise SystemExit(1)
