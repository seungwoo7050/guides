#!/usr/bin/env python3
from __future__ import annotations

import copy
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VERIFIER = ROOT / "scripts/verify_capstone.py"
VALID = ROOT / "scripts/fixtures/capstone-valid"
SCENARIO = ROOT / "scripts/fixtures/scenario/candidate-findings.json"


def run(work: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(VERIFIER), str(work), "--scenario-candidates", str(SCENARIO)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
        timeout=20,
    )


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def expect_failure(name: str, work: Path, code: str) -> None:
    result = run(work)
    output = result.stdout + result.stderr
    if result.returncode == 0 or f"[{code}]" not in output:
        raise AssertionError(f"{name}: expected {code}, exit={result.returncode}\n{output}")
    print(f"[PASS] {name} code={code}")


def main() -> int:
    result = run(VALID)
    if result.returncode != 0 or "CAPSTONE OK" not in result.stdout:
        raise AssertionError(f"valid fixture rejection\n{result.stdout}{result.stderr}")
    print("[PASS] valid-complete")

    with tempfile.TemporaryDirectory(prefix="capstone-meta-") as directory:
        temporary = Path(directory)

        missing = temporary / "missing-candidate"
        shutil.copytree(VALID, missing)
        data = json.loads((missing / "findings.json").read_text(encoding="utf-8"))
        data["findings"].pop()
        write_json(missing / "findings.json", data)
        expect_failure("missing-candidate", missing, "E_CANDIDATE_COVERAGE")

        bad_trace = temporary / "bad-trace"
        shutil.copytree(VALID, bad_trace)
        final = (bad_trace / "final-report.md").read_text(encoding="utf-8")
        (bad_trace / "final-report.md").write_text(final.replace("DET-001", "DET-999"), encoding="utf-8")
        expect_failure("bad-trace", bad_trace, "E_TRACE")

        tampered = temporary / "tampered-evidence"
        shutil.copytree(VALID, tampered)
        evidence = json.loads((tampered / "behavior-evidence.json").read_text(encoding="utf-8"))
        evidence["checks"][0]["passed"] = False
        write_json(tampered / "behavior-evidence.json", evidence)
        expect_failure("tampered-evidence", tampered, "E_BEHAVIOR_EVIDENCE")

        bad_date = temporary / "bad-date"
        shutil.copytree(VALID, bad_date)
        report = (bad_date / "final-report.md").read_text(encoding="utf-8")
        (bad_date / "final-report.md").write_text(report.replace("2027-01-01", "2027-02-30"), encoding="utf-8")
        expect_failure("bad-date", bad_date, "E_DATE")

        duplicate = temporary / "case-duplicate-id"
        shutil.copytree(VALID, duplicate)
        findings = json.loads((duplicate / "findings.json").read_text(encoding="utf-8"))
        duplicate_row = copy.deepcopy(findings["findings"][0])
        duplicate_row["id"] = "fnd-001"
        duplicate_row["candidate_id"] = "CAND-META-007"
        findings["findings"].append(duplicate_row)
        write_json(duplicate / "findings.json", findings)
        expect_failure("case-duplicate-id", duplicate, "E_DUPLICATE_ID")

        acceptance = temporary / "invalid-acceptance"
        shutil.copytree(VALID, acceptance)
        acceptance_findings = json.loads((acceptance / "findings.json").read_text(encoding="utf-8"))
        acceptance_findings["findings"][0]["treatment"] = "accept"
        write_json(acceptance / "findings.json", acceptance_findings)
        expect_failure("invalid-acceptance", acceptance, "E_FINDING_STATE")

        template = temporary / "template-unfilled"
        shutil.copytree(ROOT / "projects/synthetic-service-security-review/templates", template)
        expect_failure("template-unfilled", template, "E_UNFILLED")

    markers = "missing-candidate bad-trace tampered-evidence bad-date case-duplicate-id invalid-acceptance template-unfilled"
    print(f"CAPSTONE META OK {markers}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
