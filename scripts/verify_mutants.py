#!/usr/bin/env python3
from __future__ import annotations

import tempfile
from pathlib import Path

from process_runner import CommandSpawnError, run_process

ROOT = Path(__file__).resolve().parents[1]
MODEL = ROOT / "examples/sync-model/sync-model.mjs"
TEST = ROOT / "examples/sync-model/sync-model.test.mjs"

MUTANTS = {
    "permanent failure reported as synced": (
        'if (state.terminal) return "permanent-failure";',
        'if (state.terminal) return "synced";',
        "permanent failure is not reported as synced or retried automatically",
    ),
    "server version regression accepted": (
        """  if (state.remote && server.version < state.remote.version) {
    throw new Error(\"server version regression\");
  }""",
        "  // MUTANT: accepts a version older than the stored remote version",
        "server version regression is rejected",
    ),
    "malformed server payload accepted": (
        """  if (typeof payload.notes !== \"string\") {
    throw new Error(\"payload.notes is required\");
  }""",
        "  // MUTANT: missing notes is accepted",
        "malformed success is rejected without partial state change",
    ),
}


def fail(message: str) -> None:
    raise SystemExit(f"MUTANT ERROR: {message}")


def main() -> None:
    source = MODEL.read_text()
    test_source = TEST.read_text()
    rejected = 0

    with tempfile.TemporaryDirectory(prefix="mobile-app-mutant-baseline-") as temporary:
        baseline_dir = Path(temporary)
        (baseline_dir / "sync-model.mjs").write_text(source)
        (baseline_dir / "sync-model.test.mjs").write_text(test_source)
        try:
            baseline = run_process(
            ["node", "--test", "--test-reporter=tap", "sync-model.test.mjs"],
            cwd=baseline_dir,
                timeout_seconds=45,
                combine_output=False,
            )
        except CommandSpawnError as error:
            fail(str(error))
    if baseline.timed_out or baseline.returncode != 0:
        fail("baseline contract suite가 먼저 통과하지 않았습니다.")

    for name, (needle, replacement, expected_test) in MUTANTS.items():
        if source.count(needle) != 1:
            fail(f"mutation target가 정확히 하나가 아닙니다: {name}")
        mutant = source.replace(needle, replacement)
        with tempfile.TemporaryDirectory(prefix="mobile-app-mutant-") as temporary:
            directory = Path(temporary)
            (directory / "sync-model.mjs").write_text(mutant)
            (directory / "sync-model.test.mjs").write_text(test_source)
            try:
                result = run_process(
                    ["node", "--test", "--test-reporter=tap", "sync-model.test.mjs"],
                    cwd=directory,
                    timeout_seconds=45,
                    combine_output=False,
                )
            except CommandSpawnError as error:
                fail(str(error))
        if result.timed_out:
            fail(f"mutant behavior suite timeout: {name}")
        if result.returncode == 0:
            fail(f"known-wrong 구현이 contract suite를 통과했습니다: {name}")
        output = result.stdout + "\n" + result.stderr
        infrastructure_errors = ("SyntaxError", "ERR_MODULE_NOT_FOUND", "ERR_UNKNOWN_FILE_EXTENSION")
        if any(error in output for error in infrastructure_errors):
            fail(f"mutant가 behavior assertion이 아닌 infrastructure 오류로 거부됐습니다: {name}")
        evidence = next(
            (line.strip() for line in output.splitlines() if line.strip().startswith("not ok") and expected_test in line),
            None,
        )
        if evidence is None:
            fail(f"지정한 behavior test가 mutant를 거부하지 않았습니다: {name} expected={expected_test}")
        rejected += 1
        print(f"MUTANT REJECTED name={name!r} evidence={evidence!r}")

    print(f"MUTANTS OK rejected={rejected}")


if __name__ == "__main__":
    main()
