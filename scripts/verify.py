#!/usr/bin/env python3
"""Verify the distributed-systems curriculum without grading human learning."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
from typing import Any
from urllib.parse import unquote

sys.dont_write_bytecode = True
from source_fingerprint import ROOT, fingerprint, source_files  # noqa: E402

MARKDOWN_LINK_RE = re.compile(r"!?\[[^\]]*\]\(([^)]+)\)")
EXTERNAL_PREFIXES = ("http://", "https://", "mailto:")
MANIFEST = ROOT / "config/repository-files.txt"
SECRET_RULES: tuple[tuple[str, re.Pattern[bytes]], ...] = (
    (
        "private-key",
        re.compile(b"-----BEGIN " + rb"(?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----"),
    ),
    ("aws-access-key", re.compile(rb"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b")),
    (
        "github-token",
        re.compile(rb"\b(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{40,})\b"),
    ),
    ("slack-token", re.compile(rb"\bxox[baprs]-[A-Za-z0-9-]{20,}\b")),
    ("google-api-key", re.compile(rb"\bAIza[0-9A-Za-z_-]{35}\b")),
    ("stripe-live-key", re.compile(rb"\bsk_live_[0-9A-Za-z]{16,}\b")),
    (
        "credential-url",
        re.compile(
            rb"\b(?:postgres(?:ql)?|mysql|mongodb(?:\+srv)?|redis)://"
            rb"[^:\s/@]{1,128}:[^@\s/]{1,256}@",
            flags=re.IGNORECASE,
        ),
    ),
    (
        "assigned-secret",
        re.compile(
            rb"\b(?:api[_-]?key|client[_-]?secret|password|passwd|"
            rb"access[_-]?token|auth[_-]?token)\b\s*[:=]\s*[\"']?"
            rb"(?!(?:<|\$\{|example|dummy|test|redacted|changeme|none|null))"
            rb"[A-Za-z0-9_./+=-]{16,}",
            flags=re.IGNORECASE,
        ),
    ),
)


class VerificationError(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise VerificationError(message)


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise VerificationError(f"JSON parse failed: {path.relative_to(ROOT)}: {exc}") from exc


def run(command: list[str], *, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    merged = os.environ.copy()
    merged["PYTHONDONTWRITEBYTECODE"] = "1"
    if env:
        merged.update(env)
    with tempfile.TemporaryDirectory(prefix="guide-ds-command-cache-") as cache:
        merged["PYTHONPYCACHEPREFIX"] = cache
        completed = subprocess.run(
            command, cwd=ROOT, env=merged, text=True,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=120, check=False,
        )
    if completed.returncode != 0:
        raise VerificationError(
            f"command failed ({completed.returncode}): {' '.join(command)}\n"
            f"stdout:\n{completed.stdout}\nstderr:\n{completed.stderr}"
        )
    return completed


def check_required_structure() -> None:
    required = [
        "README.md", "CONTRIBUTING.md", "LICENSE.md", "LICENSES/CC-BY-4.0.txt",
        "LICENSES/MIT.txt", "Makefile", "prepare.sh", "verify.sh",
        "config/guide.json", "docs/00-roadmap.md", "docs/06-capstone.md",
        "exercises/README.md", "capstone/starter/README.md",
        "capstone/oracle/checks.py", "capstone/model/election_model.py",
        "capstone/scenarios/schedules.json", "capstone/known-wrong/traces.json",
        "reference/primary-sources.md", "reference/lab-safety.md",
        "reference/completion-evidence-rubric.md", "scripts/check_exercises.py",
        "scripts/test_capstone_curriculum.py", "scripts/check-capstone-workspace.py",
    ]
    for relative in required:
        require((ROOT / relative).is_file(), f"required file missing: {relative}")
    core_docs = [path for path in (ROOT / "docs").rglob("*.md") if "90-optional-paths" not in path.parts]
    require(len(core_docs) >= 23, f"too few core documents: {len(core_docs)}")
    exercise_readmes = list((ROOT / "exercises").rglob("README.md"))
    require(len(exercise_readmes) >= 15, f"too few exercise guides including index: {len(exercise_readmes)}")


def check_catalog_contract() -> None:
    guide = load_json(ROOT / "config/guide.json")
    expected = {
        "id": "distributed-systems",
        "kind": "specialization",
        "requires": ["operating-systems", "computer-networks", "database-systems"],
        "recommends": ["algorithms", "distributed-services"],
        "connects": ["data-engineering", "platform-engineering"],
        "continues_to": [],
        "owns": [
            "분산 시간·순서·failure detector",
            "복제와 일관성 모델",
            "leader election·합의·replicated log",
            "snapshot·membership change·sharding",
            "결정적 장애 주입과 history 검증",
        ],
        "excludes": [
            "서비스 업무 saga 재교육", "DBMS 단일 노드 내부 전체",
            "Kubernetes 운영", "특정 클라우드 제품",
        ],
        "exit_capabilities": [
            "복제 상태 기계의 safety·liveness를 설명한다",
            "partition과 leader 교체를 재현한다",
            "작은 분산 저장소를 구현·검증한다",
        ],
    }
    for key, value in expected.items():
        require(guide.get(key) == value, f"main catalog contract mismatch: {key}")
    require(guide.get("capstone", {}).get("reference_implementation_included") is False, "drop-in capstone answer must remain absent")


def check_license_contract() -> None:
    classification = (ROOT / "LICENSE.md").read_text(encoding="utf-8")
    require(
        "Markdown 문서" in classification
        and "LICENSES/CC-BY-4.0.txt" in classification
        and "Creative Commons Attribution 4.0 International" in classification,
        "LICENSE.md must classify documentation as CC BY 4.0",
    )
    require(
        "소스 코드, 셸 스크립트, 설정 예제" in classification
        and "LICENSES/MIT.txt" in classification
        and "MIT License" in classification,
        "LICENSE.md must classify executable source and configuration as MIT",
    )
    mit = (ROOT / "LICENSES/MIT.txt").read_text(encoding="utf-8")
    require(mit.startswith("MIT License\n"), "MIT license text has an invalid heading")
    require("Copyright (c) 2025 Seungwoo Kim" in mit, "MIT license attribution is missing")
    require("Permission is hereby granted, free of charge" in mit, "MIT license grant is incomplete")
    require("THE SOFTWARE IS PROVIDED \"AS IS\"" in mit, "MIT license warranty clause is incomplete")
    require(len(mit.encode("utf-8")) >= 1_000, "MIT license text appears truncated")

    cc = (ROOT / "LICENSES/CC-BY-4.0.txt").read_text(encoding="utf-8")
    require(cc.startswith("Attribution 4.0 International\n"), "CC BY license text has an invalid heading")
    require(
        "Creative Commons Attribution 4.0 International Public License" in cc,
        "CC BY public-license declaration is missing",
    )
    require("Section 1 -- Definitions." in cc, "CC BY definitions are missing")
    require("Section 8 -- Interpretation." in cc, "CC BY interpretation section is missing")
    require(len(cc.encode("utf-8")) >= 15_000, "CC BY license text appears truncated")


def git_tracked_files() -> list[Path]:
    top = subprocess.run(
        ["git", "-C", str(ROOT), "rev-parse", "--show-toplevel"],
        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, check=False,
    )
    if top.returncode != 0:
        return []
    try:
        top_path = Path(top.stdout.decode("utf-8").strip()).resolve(strict=True)
    except (UnicodeDecodeError, OSError):
        return []
    if top_path != ROOT.resolve():
        return []
    listed = subprocess.run(
        ["git", "-C", str(ROOT), "ls-files", "-z"],
        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, check=False,
    )
    require(listed.returncode == 0, "cannot enumerate tracked files for secret scan")
    paths: list[Path] = []
    for encoded in listed.stdout.split(b"\0"):
        if not encoded:
            continue
        try:
            relative = Path(encoded.decode("utf-8"))
        except UnicodeDecodeError as exc:
            raise VerificationError("tracked path is not valid UTF-8") from exc
        candidate = ROOT / relative
        try:
            candidate.relative_to(ROOT)
        except ValueError as exc:
            raise VerificationError("tracked path escapes repository") from exc
        if candidate.is_file() and not candidate.is_symlink():
            paths.append(candidate)
    return paths


def check_secret_patterns() -> None:
    candidates = set(source_files())
    candidates.update(git_tracked_files())
    for path in sorted(candidates, key=lambda item: item.relative_to(ROOT).as_posix()):
        data = path.read_bytes()
        for rule_id, pattern in SECRET_RULES:
            match = pattern.search(data)
            if match is None:
                continue
            line = data.count(b"\n", 0, match.start()) + 1
            relative = path.relative_to(ROOT).as_posix()
            raise VerificationError(
                f"potential secret ({rule_id}) at {relative}:{line}; value suppressed"
            )


def parse_markdown_target(raw: str) -> str:
    target = raw.strip()
    if target.startswith("<") and ">" in target:
        target = target[1:target.index(">")]
    elif " " in target and not target.startswith(EXTERNAL_PREFIXES):
        target = target.split(" ", 1)[0]
    return unquote(target)


def heading_slugs(path: Path) -> set[str]:
    result: set[str] = set()
    counts: dict[str, int] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.startswith("#"):
            continue
        heading = line.lstrip("#").strip().lower()
        slug = re.sub(r"[^\w\- ]", "", heading, flags=re.UNICODE).replace(" ", "-")
        slug = re.sub(r"-+", "-", slug).strip("-")
        if not slug:
            continue
        count = counts.get(slug, 0)
        counts[slug] = count + 1
        result.add(slug if count == 0 else f"{slug}-{count}")
    return result


def check_markdown_links() -> None:
    markdown_files = [path for path in source_files() if path.suffix == ".md"]
    require(markdown_files, "no Markdown files found")
    for path in markdown_files:
        text = path.read_text(encoding="utf-8")
        require(text.startswith("# "), f"Markdown must start with H1: {path.relative_to(ROOT)}")
        for raw in MARKDOWN_LINK_RE.findall(text):
            target = parse_markdown_target(raw)
            if not target or target.startswith(EXTERNAL_PREFIXES):
                continue
            path_part, _, fragment = target.partition("#")
            resolved = path if not path_part else (path.parent / path_part).resolve()
            try:
                resolved.relative_to(ROOT.resolve())
            except ValueError as exc:
                raise VerificationError(f"link escapes repository: {path.relative_to(ROOT)} -> {raw}") from exc
            require(resolved.exists(), f"broken link: {path.relative_to(ROOT)} -> {raw}")
            if fragment and resolved.is_file() and resolved.suffix == ".md":
                require(fragment in heading_slugs(resolved), f"broken heading link: {path.relative_to(ROOT)} -> {raw}")


def check_json_and_python() -> None:
    json_files = [path for path in source_files() if path.suffix == ".json"]
    require(len(json_files) >= 30, f"too few JSON evidence files: {len(json_files)}")
    for path in json_files:
        data = load_json(path)
        if isinstance(data, dict) and "schema_version" in data:
            require(data["schema_version"] == 1, f"unsupported schema_version: {path.relative_to(ROOT)}")
    python_files = [path for path in source_files() if path.suffix == ".py"]
    for path in python_files:
        try:
            compile(path.read_text(encoding="utf-8"), str(path), "exec")
        except SyntaxError as exc:
            raise VerificationError(f"Python syntax failed: {path.relative_to(ROOT)}:{exc.lineno}: {exc.msg}") from exc


def check_shell_and_modes() -> None:
    for path in source_files():
        data = path.read_bytes()
        if data.startswith(b"#!"):
            require(os.access(path, os.X_OK), f"shebang file must be executable: {path.relative_to(ROOT)}")
    for path in source_files():
        if path.suffix == ".sh" or path.name in {"prepare.sh", "verify.sh"}:
            run(["sh", "-n", str(path)])


def check_examples() -> None:
    logical = json.loads(run([
        sys.executable, "examples/logical-clocks/logical_clocks.py",
        "exercises/01-model-and-time/01-causality-trace/trace.json",
    ]).stdout)
    require(logical["cuts"]["cut-1"]["consistent"] is True, "cut-1 must be consistent")
    require(logical["cuts"]["cut-2"]["consistent"] is False, "cut-2 must expose missing causal predecessor")
    network_command = [sys.executable, "examples/deterministic-network/simulation.py", "examples/deterministic-network/schedule.json"]
    first = json.loads(run(network_command).stdout)
    second = json.loads(run(network_command).stdout)
    require(first == second, "deterministic network output changed between identical runs")
    linear = json.loads(run([
        sys.executable, "examples/linearizable-register/checker.py",
        "exercises/05-validation/01-linearizability/histories.json",
    ]).stdout)
    expected = {
        "completed-write-then-read": True, "stale-read-after-completion": False,
        "overlapping-write-and-reads": True, "new-then-old-during-one-write": False,
        "pending-write-observed": True, "two-overlapping-writes": True,
    }
    actual = {item["id"]: item["linearizable"] for item in linear}
    require(actual == expected, "linearizability fixture classification mismatch")


def check_curriculum_evidence() -> None:
    run([sys.executable, "scripts/check_exercises.py"])
    run([sys.executable, "scripts/test_capstone_curriculum.py"])
    run([sys.executable, "scripts/test_workspace_tools.py"])
    if os.environ.get("GUIDE_VALIDATOR_NESTED") != "1":
        run(
            [sys.executable, "scripts/test_validator.py"],
            env={"GUIDE_VALIDATOR_NESTED": "1"},
        )


def expected_manifest_paths() -> list[str]:
    return [
        path.relative_to(ROOT).as_posix() for path in source_files()
        if path.relative_to(ROOT).as_posix() != "config/repository-files.txt"
    ]


def check_manifest() -> None:
    require(MANIFEST.is_file(), "repository manifest missing")
    actual = [
        line.strip() for line in MANIFEST.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.startswith("#")
    ]
    require(actual == expected_manifest_paths(), "config/repository-files.txt does not match exact source tree")


def check_no_unexpected_placeholders() -> None:
    allowed_prefixes = (
        "capstone/starter/design/", "capstone/starter/dskv/node.py",
        "exercises/05-validation/02-simulation-plan/plan-template.json",
    )
    for path in source_files():
        relative = path.relative_to(ROOT).as_posix()
        if relative.startswith(allowed_prefixes) or path.suffix not in {".md", ".py", ".json", ".sh"}:
            continue
        text = path.read_text(encoding="utf-8", errors="strict")
        for token in ("PLACE" + "HOLDER", "TBD" + "_UNRESOLVED"):
            require(token not in text, f"unexpected unfinished token: {relative}")


def check_prepared_fingerprint() -> None:
    marker_path = ROOT / ".guide/distributed-systems/prepared.json"
    require(marker_path.is_file(), "prepare marker missing")
    marker = load_json(marker_path)
    current = fingerprint()
    require(set(marker) >= {"guide", "python", "source_sha256", "file_count"}, "prepare marker schema incomplete")
    require(marker.get("guide") == "distributed-systems", "prepare marker guide mismatch")
    require(marker.get("source_sha256") == current["source_sha256"], "source changed after prepare; rerun make prepare")
    require(marker.get("file_count") == current["file_count"], "prepared file count mismatch")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--quick", action="store_true", help="skip prepared fingerprint check")
    parser.add_argument("--prepared-only", action="store_true")
    parser.add_argument("--policy-only", action="store_true")
    args = parser.parse_args()
    if sys.version_info < (3, 12):
        raise VerificationError("Python 3.12 이상이 필요합니다.")
    if args.prepared_only:
        check_prepared_fingerprint()
        print("OK prepared-fingerprint")
        return 0
    if args.policy_only:
        check_license_contract()
        check_secret_patterns()
        print("OK license-secret-policy")
        return 0
    checks = [
        ("structure", check_required_structure),
        ("catalog-contract", check_catalog_contract),
        ("license-secret-policy", lambda: (check_license_contract(), check_secret_patterns())),
        ("links", check_markdown_links),
        ("json-python", check_json_and_python),
        ("shell-modes", check_shell_and_modes),
        ("examples", check_examples),
        ("curriculum-evidence", check_curriculum_evidence),
        ("manifest", check_manifest),
        ("placeholders", check_no_unexpected_placeholders),
    ]
    if not args.quick:
        checks.append(("prepared-fingerprint", check_prepared_fingerprint))
    for name, check in checks:
        check()
        print(f"OK {name}")
    print(f"CURRICULUM VERIFY OK files={len(source_files())} checks={len(checks)}")
    print("HUMAN REVIEW REQUIRED: technical depth, safety/liveness reasoning, and exit evidence.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except VerificationError as exc:
        print(f"ERROR {exc}", file=sys.stderr)
        raise SystemExit(1)
