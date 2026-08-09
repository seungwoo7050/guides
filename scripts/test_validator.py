#!/usr/bin/env python3
"""Prove that the structural validator rejects representative mutations."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def copy_source(destination: Path) -> None:
    shutil.copytree(
        ROOT,
        destination,
        symlinks=True,
        ignore=shutil.ignore_patterns(
            ".git",
            ".guide",
            ".mypy_cache",
            ".pytest_cache",
            ".ruff_cache",
            ".venv",
            "__pycache__",
            "workspace",
            "*.pyc",
            "*.pyo",
        ),
    )


def validate(root: Path) -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy()
    environment["GUIDE_ROOT"] = str(root)
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    return subprocess.run(
        [sys.executable, "-B", str(root / "scripts/validate.py")],
        cwd=root,
        env=environment,
        text=True,
        capture_output=True,
        timeout=30,
        check=False,
    )


def expect_rejection(name: str, mutate, expected: str) -> None:
    with tempfile.TemporaryDirectory(prefix=f"guide-data-validator-{name}-") as temporary:
        root = Path(temporary) / "repository"
        copy_source(root)
        mutate(root)
        result = validate(root)
        output = result.stdout + result.stderr
        if result.returncode == 0 or expected not in output:
            raise AssertionError(f"validator accepted {name}: status={result.returncode}\n{output}")
        print(f"[PASS] validator mutant: {name}")


def main() -> int:
    baseline = validate(ROOT)
    if baseline.returncode != 0:
        raise AssertionError(baseline.stdout + baseline.stderr)

    expect_rejection(
        "missing-required-file",
        lambda root: (root / "LICENSE.md").unlink(),
        "필수 일반 파일 누락",
    )

    def break_link(root: Path) -> None:
        path = root / "README.md"
        path.write_text(path.read_text(encoding="utf-8") + "\n[broken](docs/not-present.md)\n", encoding="utf-8")

    expect_rejection("broken-link", break_link, "깨진 링크")

    def remove_heading(root: Path) -> None:
        path = sorted((root / "docs/01-contracts-and-records").glob("*.md"))[0]
        path.write_text(path.read_text(encoding="utf-8").replace("## 실패 모드", "## 장애 메모", 1), encoding="utf-8")

    expect_rejection("missing-concept-role", remove_heading, "## 실패 모드")

    def syntax_error(root: Path) -> None:
        path = root / "scripts/fingerprint.py"
        path.write_text(path.read_text(encoding="utf-8") + "\nif (\n", encoding="utf-8")

    expect_rejection("python-syntax", syntax_error, "Python syntax 오류")

    def required_symlink(root: Path) -> None:
        target = root.parent / "outside-readme"
        target.write_text("# outside\n", encoding="utf-8")
        (root / "README.md").unlink()
        (root / "README.md").symlink_to(target)

    expect_rejection("required-symlink", required_symlink, "필수 일반 파일 누락")
    expect_rejection(
        "secret-path",
        lambda root: (root / ".env").write_text("TOKEN=sentinel\n", encoding="utf-8"),
        "비밀정보 가능성이 있는 파일",
    )

    def non_normalized_checker(root: Path) -> None:
        path = root / "exercises/manifest.json"
        manifest = json.loads(path.read_text(encoding="utf-8"))
        manifest["exercises"][0]["checker"] = "tests//check.py"
        path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    expect_rejection("non-normalized-checker", non_normalized_checker, "정규화되지 않은 상대 경로")

    def duplicate_known_bad(root: Path) -> None:
        path = root / "exercises/manifest.json"
        manifest = json.loads(path.read_text(encoding="utf-8"))
        fixture = manifest["exercises"][0]["known_bad"][0]
        manifest["exercises"][0]["known_bad"].append(fixture)
        path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    expect_rejection("duplicate-known-bad", duplicate_known_bad, "known_bad 경로가 중복")

    def duplicate_success_marker(root: Path) -> None:
        path = root / "exercises/manifest.json"
        manifest = json.loads(path.read_text(encoding="utf-8"))
        code_items = [item for item in manifest["exercises"] if item["kind"] in {"code", "design"}]
        code_items[1]["success_marker"] = code_items[0]["success_marker"]
        path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    expect_rejection("duplicate-success-marker", duplicate_success_marker, "success_marker가 중복")

    batch_capstone = Path("exercises/06-capstones/01-batch-data-product")

    def rubric_root_array(root: Path) -> None:
        (root / batch_capstone / "rubric.json").write_text("[]\n", encoding="utf-8")

    expect_rejection("capstone-rubric-root", rubric_root_array, "rubric root는 object")

    def invalid_criteria(root: Path) -> None:
        path = root / batch_capstone / "rubric.json"
        rubric = json.loads(path.read_text(encoding="utf-8"))
        rubric["criteria"] = [42]
        path.write_text(json.dumps(rubric, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    expect_rejection("capstone-criteria-type", invalid_criteria, "criteria 누락")

    def missing_required_json_path(root: Path) -> None:
        path = root / batch_capstone / "rubric.json"
        rubric = json.loads(path.read_text(encoding="utf-8"))
        rubric["required_nonempty_json"]["input-manifest.json"].append("does.not.exist")
        path.write_text(json.dumps(rubric, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    expect_rejection(
        "capstone-required-json-path",
        missing_required_json_path,
        "template에 JSON path가 없습니다",
    )

    def non_normalized_required_json_path(root: Path) -> None:
        path = root / batch_capstone / "rubric.json"
        rubric = json.loads(path.read_text(encoding="utf-8"))
        rubric["required_nonempty_json"]["input-manifest.json"].append("sources..uri")
        path.write_text(json.dumps(rubric, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    expect_rejection(
        "capstone-required-json-path-spelling",
        non_normalized_required_json_path,
        "잘못된 JSON path",
    )

    def wrong_evidence_identity(root: Path) -> None:
        path = root / batch_capstone / "skeleton/evidence.json"
        evidence = json.loads(path.read_text(encoding="utf-8"))
        evidence["capstone_id"] = "wrong-capstone"
        path.write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    expect_rejection("capstone-evidence-identity", wrong_evidence_identity, "evidence template identity 오류")

    def boolean_evidence_schema(root: Path) -> None:
        path = root / batch_capstone / "skeleton/evidence.json"
        evidence = json.loads(path.read_text(encoding="utf-8"))
        evidence["schema_version"] = True
        path.write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    expect_rejection("capstone-evidence-schema-type", boolean_evidence_schema, "evidence template identity 오류")

    def missing_submission_identity(root: Path) -> None:
        path = root / batch_capstone / "skeleton/submission.json"
        submission = json.loads(path.read_text(encoding="utf-8"))
        submission.pop("run_id")
        path.write_text(json.dumps(submission, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    expect_rejection("capstone-submission-field", missing_submission_identity, "submission template field 오류 run_id")

    def completed_evidence_template_field(root: Path) -> None:
        path = root / batch_capstone / "skeleton/evidence.json"
        evidence = json.loads(path.read_text(encoding="utf-8"))
        evidence["scenarios"][0]["status"] = "pass"
        path.write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    expect_rejection(
        "capstone-evidence-template-field",
        completed_evidence_template_field,
        "evidence template scenario field 오류 normal.status",
    )
    print("VALIDATOR MUTANTS: PASS (17/17)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
