#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import py_compile
import re
import subprocess
import sys
import tempfile
import unicodedata
from datetime import datetime
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]
SCENARIO = ROOT / "projects/synthetic-service-security-review/scenario"
MARKDOWN_LINK = re.compile(r"!?\[[^\]]*\]\(([^)]+)\)")
MARKDOWN_HEADING = re.compile(r"^#{1,6}\s+(.+?)(?:\s+#+)?\s*$")
STRUCTURED_ID = re.compile(r"^(AST|POL|CAND|OBS|EVT)-[0-9]{3}$")

REQUIRED_FILES = [
    ".gitignore",
    "README.md",
    "CONTRIBUTING.md",
    "LICENSE.md",
    "Makefile",
    "prepare.sh",
    "verify.sh",
    "scripts/new_workspace.py",
    "scripts/source_fingerprint.py",
    "scripts/verify_repository.py",
    "scripts/verify_capstone.py",
    "scripts/capstone_behavior.py",
    "scripts/capture_capstone_behavior.py",
    "scripts/test_tooling.py",
    "scripts/test_verify_repository.py",
    "scripts/test_verify_capstone.py",
    "reference/safe-lab-policy.md",
    "reference/evidence-checklist.md",
    "reference/assessment-charter-template.md",
    "reference/threat-model-template.md",
    "reference/finding-template.md",
    "reference/security-requirement-template.md",
    "reference/security-test-template.md",
    "reference/incident-timeline-template.md",
    "reference/security-review-checklist.md",
    "reference/project-entry-map.md",
    "reference/manual-review-guide.md",
    "reference/glossary.md",
    "projects/synthetic-service-security-review/README.md",
    "projects/synthetic-service-security-review/scenario/asset-register.json",
    "projects/synthetic-service-security-review/scenario/candidate-findings.json",
    "projects/synthetic-service-security-review/scenario/event-log.jsonl",
    "projects/synthetic-service-security-review/scenario/identity-policy.json",
    "projects/synthetic-service-security-review/scenario/package-proxy-policy.json",
    "projects/synthetic-service-security-review/scenario/release-manifest.json",
    "projects/synthetic-service-security-review/scenario/verification-observations.json",
    "projects/synthetic-service-security-review/templates/findings.json",
    "exercises/07-isolated-attack-path/fixtures/state.json",
    "exercises/07-isolated-attack-path/skeleton/ledgerlab_policy.py",
    "exercises/07-isolated-attack-path/reference/ledgerlab_policy.py",
    "exercises/07-isolated-attack-path/tests/check.py",
    "exercises/07-isolated-attack-path/tests/check_quality.py",
    "exercises/07-isolated-attack-path/tests/mutants/deny_all.py",
    "exercises/07-isolated-attack-path/tests/mutants/cross_owner_allowed.py",
    "exercises/07-isolated-attack-path/tests/mutants/prefix_bypass.py",
    "exercises/07-isolated-attack-path/tests/mutants/no_detection.py",
]
REQUIRED_DOCS = ["docs/00-roadmap.md"] + [
    f"docs/{number:02d}-{name}.md"
    for number, name in [
        (1, "security-state-and-evidence"),
        (2, "assets-trust-boundaries-and-threat-models"),
        (3, "scope-authorization-and-rules-of-engagement"),
        (4, "risk-vulnerability-and-prioritization"),
        (5, "attack-surface-and-paths"),
        (6, "application-boundary-failures"),
        (7, "system-identity-and-secret-boundaries"),
        (8, "supply-chain-and-build-trust"),
        (9, "vulnerability-validation-and-reporting"),
        (10, "security-requirements-and-design-invariants"),
        (11, "security-testing-and-assurance"),
        (12, "remediation-hardening-and-regression"),
        (13, "telemetry-detection-and-investigation"),
        (14, "incident-response-and-recovery"),
        (15, "security-review-and-release-decision"),
        (16, "capstone"),
    ]
] + ["docs/90-standards-map.md"]
EXERCISE_LAYOUT = {
    "01-scope-and-evidence": "assessment-charter.md",
    "02-threat-model": "threat-model.md",
    "03-vulnerability-validation": "findings.json",
    "04-security-requirements": "security-requirements.md",
    "05-detection-engineering": "detection-plan.md",
    "06-incident-timeline": "incident-timeline.md",
}
REQUIRED_EXERCISES = ["exercises/README.md", "exercises/07-isolated-attack-path/README.md"]
for exercise_id, artifact in EXERCISE_LAYOUT.items():
    REQUIRED_EXERCISES.extend(
        [
            f"exercises/{exercise_id}/README.md",
            f"exercises/{exercise_id}/template/{artifact}",
        ]
    )


def fail(message: str) -> None:
    raise AssertionError(message)


def is_generated(path: Path) -> bool:
    try:
        relative = path.relative_to(ROOT)
    except ValueError:
        return False
    if any(part in {".git", ".guide", "__pycache__"} for part in relative.parts):
        return True
    if path.name == ".DS_Store":
        return True
    if relative.parts[:3] == ("projects", "synthetic-service-security-review", "work"):
        return True
    return len(relative.parts) >= 3 and relative.parts[0] == "exercises" and relative.parts[2] == "work"


def check_required() -> None:
    for relative in REQUIRED_FILES + REQUIRED_DOCS + REQUIRED_EXERCISES:
        path = ROOT / relative
        if path.is_symlink() or not path.is_file():
            fail(f"필수 일반 파일이 없습니다: {relative}")


def split_markdown_target(raw: str) -> tuple[str, str]:
    target = raw.strip()
    if target.startswith("<") and target.endswith(">"):
        target = target[1:-1]
    if " \"" in target:
        target = target.split(" \"", 1)[0]
    path, separator, fragment = target.partition("#")
    return unquote(path.strip()), unquote(fragment.strip()) if separator else ""


def heading_slug(text: str) -> str:
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    text = re.sub(r"<[^>]+>", "", text)
    text = text.replace("`", "").strip().lower()
    characters: list[str] = []
    for character in text:
        category = unicodedata.category(character)
        if category.startswith(("L", "N")) or character in {" ", "-", "_"}:
            characters.append(character)
    return re.sub(r"\s+", "-", "".join(characters).strip())


def markdown_anchors(path: Path) -> set[str]:
    anchors: set[str] = set()
    occurrences: dict[str, int] = {}
    in_fence = False
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.lstrip().startswith(("```", "~~~")):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        match = MARKDOWN_HEADING.match(line)
        if match is None:
            continue
        base = heading_slug(match.group(1))
        count = occurrences.get(base, 0)
        occurrences[base] = count + 1
        anchors.add(base if count == 0 else f"{base}-{count}")
    return anchors


def check_links() -> tuple[int, int]:
    link_count = 0
    anchor_count = 0
    anchor_cache: dict[Path, set[str]] = {}
    for path in sorted(ROOT.rglob("*.md")):
        if is_generated(path):
            continue
        text = path.read_text(encoding="utf-8")
        for raw in MARKDOWN_LINK.findall(text):
            target, fragment = split_markdown_target(raw)
            if target.startswith(("http://", "https://", "mailto:", "data:")):
                continue
            resolved = path if not target else (path.parent / target).resolve()
            try:
                resolved.relative_to(ROOT.resolve())
            except ValueError:
                fail(f"{path.relative_to(ROOT)}: 저장소 밖 링크 {raw}")
            if not resolved.exists():
                fail(f"{path.relative_to(ROOT)}: 깨진 링크 {raw}")
            link_count += 1
            if fragment and resolved.suffix.lower() == ".md":
                anchors = anchor_cache.setdefault(resolved, markdown_anchors(resolved))
                if fragment not in anchors:
                    fail(f"{path.relative_to(ROOT)}: 깨진 anchor #{fragment} -> {resolved.relative_to(ROOT)}")
                anchor_count += 1
    return link_count, anchor_count


def check_structured_data() -> tuple[int, int]:
    json_count = 0
    jsonl_count = 0
    for path in sorted(ROOT.rglob("*.json")):
        if is_generated(path):
            continue
        try:
            json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            fail(f"{path.relative_to(ROOT)}: JSON 오류: {exc}")
        json_count += 1
    for path in sorted(ROOT.rglob("*.jsonl")):
        if is_generated(path):
            continue
        rows = 0
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if not line.strip():
                continue
            try:
                value = json.loads(line)
            except Exception as exc:
                fail(f"{path.relative_to(ROOT)}:{number}: JSONL 오류: {exc}")
            if not isinstance(value, dict):
                fail(f"{path.relative_to(ROOT)}:{number}: 각 줄은 object여야 합니다.")
            rows += 1
        if rows == 0:
            fail(f"{path.relative_to(ROOT)}: JSONL이 비어 있습니다.")
        jsonl_count += 1
    return json_count, jsonl_count


def check_python() -> int:
    python_files = [path for path in sorted(ROOT.rglob("*.py")) if not is_generated(path)]
    with tempfile.TemporaryDirectory(prefix="cybersecurity-pyc-") as temporary:
        for index, script in enumerate(python_files):
            try:
                py_compile.compile(
                    str(script),
                    cfile=str(Path(temporary) / f"{index}-{script.stem}.pyc"),
                    doraise=True,
                )
            except py_compile.PyCompileError as exc:
                fail(f"{script.relative_to(ROOT)}: Python 문법 오류: {exc}")
    return len(python_files)


def load_json(name: str) -> object:
    return json.loads((SCENARIO / name).read_text(encoding="utf-8"))


def load_jsonl(name: str) -> list[dict]:
    rows: list[dict] = []
    for line in (SCENARIO / name).read_text(encoding="utf-8").splitlines():
        if line.strip():
            value = json.loads(line)
            if not isinstance(value, dict):
                fail(f"scenario/{name}: row는 object여야 합니다.")
            rows.append(value)
    return rows


def parse_timestamp(value: object, context: str) -> datetime:
    if not isinstance(value, str) or not value:
        fail(f"{context}: ISO timestamp가 없습니다.")
    candidate = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(candidate)
    except ValueError as exc:
        fail(f"{context}: 잘못된 ISO timestamp {value!r}: {exc}")
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        fail(f"{context}: timezone이 있는 ISO timestamp여야 합니다: {value!r}")
    return parsed


def collect_ids(rows: object, field: str, prefix: str, context: str) -> set[str]:
    if not isinstance(rows, list) or not rows:
        fail(f"{context}: 비어 있지 않은 배열이어야 합니다.")
    ids: list[str] = []
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            fail(f"{context}[{index}]: object여야 합니다.")
        value = row.get(field)
        if not isinstance(value, str) or not STRUCTURED_ID.fullmatch(value) or not value.startswith(f"{prefix}-"):
            fail(f"{context}[{index}]: 잘못된 {prefix} ID {value!r}")
        ids.append(value)
    canonical = [value.casefold() for value in ids]
    if len(canonical) != len(set(canonical)):
        fail(f"{context}: 대소문자를 무시하면 중복 ID가 있습니다.")
    return set(ids)


def check_scenario_integrity() -> dict[str, int]:
    assets = load_json("asset-register.json")
    identity = load_json("identity-policy.json")
    candidates = load_json("candidate-findings.json")
    observations = load_json("verification-observations.json")
    manifest = load_json("release-manifest.json")
    events = load_jsonl("event-log.jsonl")
    if not all(isinstance(value, dict) for value in [assets, identity, candidates, observations, manifest]):
        fail("scenario top-level JSON은 object여야 합니다.")

    asset_ids = collect_ids(assets.get("assets"), "id", "AST", "asset-register.assets")
    policy_ids = collect_ids(identity.get("policies"), "policy_id", "POL", "identity-policy.policies")
    candidate_rows = candidates.get("candidates")
    candidate_ids = collect_ids(candidate_rows, "id", "CAND", "candidate-findings.candidates")
    observation_ids = collect_ids(observations.get("observations"), "id", "OBS", "verification-observations.observations")
    event_ids = collect_ids(events, "event_id", "EVT", "event-log")

    parse_timestamp(assets.get("as_of"), "asset-register.as_of")
    parse_timestamp(identity.get("snapshot_time"), "identity-policy.snapshot_time")
    parse_timestamp(candidates.get("as_of"), "candidate-findings.as_of")
    for observation in observations["observations"]:
        parse_timestamp(observation.get("observed_at"), f"{observation['id']}.observed_at")

    known_evidence_ids = asset_ids | policy_ids | observation_ids | event_ids
    for candidate in candidate_rows:
        candidate_id = candidate["id"]
        affected = candidate.get("affected_assets")
        evidence = candidate.get("evidence_refs")
        for field in ["title", "source", "claim", "safe_validation"]:
            if not isinstance(candidate.get(field), str) or not candidate[field].strip():
                fail(f"{candidate_id}: 필드 누락 {field}")
        if not isinstance(affected, list) or not affected:
            fail(f"{candidate_id}: affected_assets가 비었습니다.")
        unknown_assets = set(affected) - asset_ids
        if unknown_assets:
            fail(f"{candidate_id}: 알 수 없는 asset 참조 {sorted(unknown_assets)}")
        if not isinstance(evidence, list) or not evidence:
            fail(f"{candidate_id}: evidence_refs가 비었습니다.")
        for reference in evidence:
            if not isinstance(reference, str) or not reference:
                fail(f"{candidate_id}: 빈 evidence reference")
            if STRUCTURED_ID.fullmatch(reference):
                if reference not in known_evidence_ids:
                    fail(f"{candidate_id}: 알 수 없는 evidence ID {reference}")
            elif not (SCENARIO / reference).is_file():
                fail(f"{candidate_id}: 알 수 없는 evidence file {reference}")

    event_by_id = {event["event_id"]: event for event in events}
    event_position = {event["event_id"]: index for index, event in enumerate(events)}
    for event in events:
        event_id = event["event_id"]
        event_time = parse_timestamp(event.get("event_time"), f"{event_id}.event_time")
        ingest_time = parse_timestamp(event.get("ingest_time"), f"{event_id}.ingest_time")
        if event_time > ingest_time:
            fail(f"{event_id}: event_time이 ingest_time보다 늦습니다.")
        details = event.get("details")
        if not isinstance(details, dict):
            fail(f"{event_id}: details는 object여야 합니다.")
        duplicate_of = details.get("delivery_duplicate_of")
        if duplicate_of is None:
            continue
        if duplicate_of not in event_by_id or event_position[duplicate_of] >= event_position[event_id]:
            fail(f"{event_id}: delivery_duplicate_of가 앞선 event를 가리키지 않습니다: {duplicate_of}")
        original = event_by_id[duplicate_of]
        if event.get("event_type") != original.get("event_type") or event.get("event_time") != original.get("event_time"):
            fail(f"{event_id}: duplicate의 type/time이 원본 {duplicate_of}와 다릅니다.")
        duplicate_details = dict(details)
        duplicate_details.pop("delivery_duplicate_of", None)
        if duplicate_details != original.get("details"):
            fail(f"{event_id}: duplicate payload가 원본 {duplicate_of}와 다릅니다.")

    created_at = parse_timestamp(manifest.get("created_at"), "release-manifest.created_at")
    approval = manifest.get("approval")
    artifact = manifest.get("artifact")
    deployment = manifest.get("deployment")
    rollback = manifest.get("rollback")
    build = manifest.get("build")
    if not all(isinstance(value, dict) for value in [approval, artifact, deployment, rollback, build]):
        fail("release-manifest의 build/artifact/deployment/approval/rollback이 object가 아닙니다.")
    approved_at = parse_timestamp(approval.get("approved_at"), "release-manifest.approval.approved_at")
    if approved_at < created_at:
        fail("release approval이 manifest 생성보다 빠릅니다.")

    release_id = manifest.get("release_id")
    started = [event for event in events if event.get("event_type") == "deployment.started" and event["details"].get("release_id") == release_id]
    ready = [event for event in events if event.get("event_type") == "deployment.ready" and event["details"].get("release_id") == release_id]
    if len(started) != 1 or len(ready) != 1:
        fail("manifest release_id와 연결된 deployment.started/ready가 각각 하나여야 합니다.")
    if started[0]["details"].get("requested_reference") != deployment.get("requested_reference"):
        fail("manifest와 deployment.started의 requested_reference가 다릅니다.")
    if parse_timestamp(started[0]["event_time"], "deployment.started") < approved_at:
        fail("deployment.started가 release approval보다 빠릅니다.")

    tag = str(deployment.get("requested_reference", "")).partition(":")[2]
    tag_events = [
        event
        for event in events
        if event.get("event_type") == "tag.updated"
        and event["details"].get("tag") == tag
        and event["details"].get("new_digest") == artifact.get("declared_digest")
    ]
    if len(tag_events) != 1:
        fail("manifest artifact digest/tag와 연결되는 tag.updated가 하나여야 합니다.")
    package_events = [
        event
        for event in events
        if event.get("event_type") == "package.resolved"
        and event["details"].get("build_id") == build.get("run_id")
    ]
    if len(package_events) != 1:
        fail("manifest build.run_id와 연결되는 package.resolved가 하나여야 합니다.")

    previous = deployment.get("previous_known_digest")
    target = rollback.get("target_digest")
    if not previous or previous != target:
        fail("deployment previous_known_digest와 rollback target_digest가 연결되지 않습니다.")
    rollback_events = [
        event
        for event in events
        if event.get("event_type") == "incident.action"
        and event["details"].get("action") == "deployment rollback"
        and str(event["details"].get("target", "")).endswith(f"@{target}")
    ]
    if len(rollback_events) != 1:
        fail("rollback target digest와 연결되는 incident.action이 하나여야 합니다.")
    rollback_time = parse_timestamp(rollback_events[0]["event_time"], "rollback incident.action")
    rollback_ready = [
        event
        for event in events
        if event.get("event_type") == "deployment.ready"
        and str(event["details"].get("release_id", "")).startswith("rollback-")
        and parse_timestamp(event["event_time"], f"{event['event_id']}.event_time") >= rollback_time
    ]
    if len(rollback_ready) != 1:
        fail("rollback action 이후의 rollback deployment.ready가 하나여야 합니다.")

    return {
        "assets": len(asset_ids),
        "policies": len(policy_ids),
        "candidates": len(candidate_ids),
        "observations": len(observation_ids),
        "events": len(event_ids),
        "duplicates": sum("delivery_duplicate_of" in event["details"] for event in events),
    }


def run_checked(command: list[str], label: str, expected_text: str | tuple[str, ...]) -> None:
    result = subprocess.run(
        command,
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
        timeout=120,
    )
    output = result.stdout + result.stderr
    if result.returncode != 0:
        fail(f"{label} 실패(exit={result.returncode}):\n{output}")
    expected = (expected_text,) if isinstance(expected_text, str) else expected_text
    missing = [token for token in expected if token not in output]
    if missing:
        fail(f"{label}: 성공 marker가 없습니다 {missing!r}:\n{output}")
    print(output.rstrip())


def check_behavior_meta() -> None:
    run_checked(
        [sys.executable, "exercises/07-isolated-attack-path/tests/check_quality.py"],
        "격리 행동 실습 meta-test",
        "LAB QUALITY OK reference=pass skeleton=reject mutants=4",
    )


def check_scenario_meta() -> None:
    run_checked(
        [sys.executable, "scripts/test_verify_repository.py"],
        "scenario integrity meta-test",
        (
            "REPOSITORY META OK cases=7",
            "duplicate-id",
            "broken-reference",
            "bad-timestamp",
            "event-after-ingest",
            "broken-duplicate",
            "broken-deployment-digest",
            "broken-rollback-digest",
        ),
    )


def check_capstone_meta() -> None:
    run_checked(
        [sys.executable, "scripts/test_verify_capstone.py"],
        "Capstone verifier meta-test",
        (
            "CAPSTONE META OK",
            "missing-candidate",
            "bad-trace",
            "tampered-evidence",
            "bad-date",
            "case-duplicate-id",
            "template-unfilled",
        ),
    )


def check_safety_contract() -> None:
    policy = (ROOT / "reference/safe-lab-policy.md").read_text(encoding="utf-8").lower()
    readme = (ROOT / "README.md").read_text(encoding="utf-8").lower()
    for term in ["허가", "금지 행동", "중단 조건", "최소 영향", "합성 데이터", "cleanup"]:
        if term.lower() not in policy:
            fail(f"safe-lab-policy에 필수 경계가 없습니다: {term}")
    for term in ["외부 주소 scan", "실제 credential", "제3자", "scope"]:
        if term.lower() not in readme:
            fail(f"README 안전 범위에 필수 표현이 없습니다: {term}")


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check_workspaces() -> int:
    checked = 0
    for exercise_id, artifact in EXERCISE_LAYOUT.items():
        exercise = ROOT / "exercises" / exercise_id
        work = exercise / "work"
        output = work / artifact
        template = exercise / "template" / artifact
        if work.is_symlink() or not work.is_dir():
            fail(f"learner workspace가 없습니다: {work.relative_to(ROOT)}")
        if output.is_symlink() or not output.is_file() or output.stat().st_size == 0:
            fail(f"learner 제출 파일이 없습니다: {output.relative_to(ROOT)}")
        if output.read_bytes() == template.read_bytes():
            fail(f"learner 제출 파일이 미완성 template와 같습니다: {output.relative_to(ROOT)}")
        if output.suffix == ".json":
            try:
                json.loads(output.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                fail(f"{output.relative_to(ROOT)}: JSON 오류: {exc}")
        checked += 1

    lab = ROOT / "exercises/07-isolated-attack-path/work"
    implementation = lab / "ledgerlab_policy.py"
    evidence_path = lab / "behavior-evidence.json"
    if lab.is_symlink() or not lab.is_dir() or implementation.is_symlink() or not implementation.is_file():
        fail("07 격리 행동 실습 learner implementation이 없습니다.")
    if evidence_path.is_symlink() or not evidence_path.is_file():
        fail("07 격리 행동 실습 behavior-evidence.json이 없습니다.")
    try:
        evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        fail(f"07 behavior evidence JSON 오류: {exc}")
    if evidence.get("profile") != "secure" or evidence.get("implementation_sha256") != file_sha256(implementation):
        fail("07 behavior evidence의 profile 또는 implementation fingerprint가 현재 work와 다릅니다.")
    checks = evidence.get("checks")
    if (
        not isinstance(checks, list)
        or not checks
        or any(not isinstance(check, dict) or check.get("passed") is not True for check in checks)
    ):
        fail("07 behavior evidence에 통과하지 않은 검사 또는 빈 검사 목록이 있습니다.")
    with tempfile.TemporaryDirectory(prefix="cybersecurity-work-evidence-") as temporary:
        rerun_path = Path(temporary) / "behavior-evidence.json"
        command = [
            sys.executable,
            "exercises/07-isolated-attack-path/tests/check.py",
            "--implementation",
            str(implementation),
            "--expect",
            "secure",
            "--evidence",
            str(rerun_path),
        ]
        result = subprocess.run(
            command,
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
            timeout=60,
        )
        rerun_output = result.stdout + result.stderr
        if result.returncode != 0 or "LAB RESULT PASS" not in rerun_output:
            fail(f"07 learner behavior 재실행 실패(exit={result.returncode}):\n{rerun_output}")
        rerun = json.loads(rerun_path.read_text(encoding="utf-8"))
        for field in [
            "profile",
            "implementation_sha256",
            "state_before_sha256",
            "state_after_sha256",
            "checks",
            "events",
        ]:
            if evidence.get(field) != rerun.get(field):
                fail(f"07 behavior evidence가 재실행 결과와 다릅니다: {field}")
        print(rerun_output.rstrip())
    return checked + 1


def verify_repository(quick: bool) -> None:
    check_required()
    link_count, anchor_count = check_links()
    json_count, jsonl_count = check_structured_data()
    python_count = check_python()
    check_safety_contract()
    scenario = check_scenario_integrity()
    if not quick:
        check_scenario_meta()
        check_behavior_meta()
        check_capstone_meta()

    print(
        "REPOSITORY OK "
        f"markdown_links={link_count} anchors={anchor_count} json={json_count} jsonl={jsonl_count} "
        f"python={python_count} assets={scenario['assets']} policies={scenario['policies']} "
        f"candidates={scenario['candidates']} observations={scenario['observations']} "
        f"events={scenario['events']} duplicates={scenario['duplicates']} "
        f"meta={'skipped' if quick else 'passed'}"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="cybersecurity 가이드 저장소 계약을 검사합니다.")
    parser.add_argument("--quick", action="store_true", help="기준 행동·Capstone meta-test를 생략합니다.")
    parser.add_argument("--workspaces-only", action="store_true", help="명시적으로 생성한 learner work만 검사합니다.")
    args = parser.parse_args()
    if args.quick and args.workspaces_only:
        parser.error("--quick과 --workspaces-only를 함께 사용할 수 없습니다.")
    if args.workspaces_only:
        count = check_workspaces()
        print(f"LEARNER WORK OK exercises={count}; 의미·판단의 타당성은 자동 검증하지 않습니다.")
    else:
        verify_repository(args.quick)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (AssertionError, OSError, subprocess.TimeoutExpired) as exc:
        print(f"REPOSITORY ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)
