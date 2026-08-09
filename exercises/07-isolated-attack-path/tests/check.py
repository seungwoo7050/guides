#!/usr/bin/env python3
from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.util
import json
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REQUIRED_EVENT_FIELDS = {
    "event_id", "event_type", "actor_id", "effective_actor_id", "credential_id",
    "tenant_id", "job_id", "action", "resource_id", "decision", "reason",
    "correlation_id", "policy_version",
}


def load_module(path: Path):
    spec = importlib.util.spec_from_file_location("learner_ledgerlab_policy", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"implementation을 불러올 수 없습니다: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(path.parent))
    try:
        spec.loader.exec_module(module)
    finally:
        sys.path.pop(0)
    return module


def request(**values: object) -> dict:
    base = {
        "event_id": "EV-LAB-000",
        "actor_id": None,
        "effective_actor_id": None,
        "credential_id": None,
        "tenant_id": "tenant-42",
        "job_id": None,
        "action": None,
        "resource_id": None,
        "correlation_id": "CORR-LAB-1",
    }
    base.update(values)
    return base


def state_hash(state: dict) -> str:
    data = json.dumps(state, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(data).hexdigest()


def implementation_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check_event(result: object, req: dict) -> list[str]:
    failures: list[str] = []
    if not isinstance(result, dict):
        return ["result-not-object"]
    if result.get("decision") not in {"allow", "deny"}:
        failures.append("decision-domain")
    event = result.get("event")
    if not isinstance(event, dict):
        return failures + ["event-not-object"]
    missing = REQUIRED_EVENT_FIELDS - set(event)
    if missing:
        failures.append("event-fields")
    if not isinstance(result.get("reason"), str) or not result.get("reason"):
        failures.append("reason-missing")
    if isinstance(event, dict):
        for field in REQUIRED_EVENT_FIELDS - {"event_type", "decision", "reason", "policy_version"}:
            if event.get(field) != req.get(field):
                failures.append(f"event-value-{field}")
        if event.get("event_type") != "authorization.decision":
            failures.append("event-type")
        if event.get("decision") != result.get("decision"):
            failures.append("event-decision")
        if event.get("reason") != result.get("reason"):
            failures.append("event-reason")
        if not isinstance(event.get("policy_version"), str) or not event.get("policy_version"):
            failures.append("event-policy-version")
    return failures


def run_secure(module, state: dict) -> tuple[list[dict], list[dict]]:
    checks: list[dict] = []
    emitted: list[dict] = []

    def execute(check_id: str, function_name: str, expected: str, req: dict, altered_state: dict | None = None):
        current = copy.deepcopy(altered_state if altered_state is not None else state)
        before = state_hash(current)
        result = getattr(module, function_name)(current, req)
        after = state_hash(current)
        errors = check_event(result, req)
        if not isinstance(result, dict) or result.get("decision") != expected:
            errors.append(f"expected-{expected}")
        if before != after:
            errors.append("state-mutated")
        event = result.get("event") if isinstance(result, dict) else None
        if isinstance(event, dict):
            emitted.append(event)
        checks.append({"id": check_id, "passed": not errors, "errors": errors, "observed": result.get("decision") if isinstance(result, dict) else None})
        return result

    owner = execute("LAB-NORMAL-OWNER", "authorize_report", "allow", request(
        event_id="EV-LAB-001", actor_id="user-a", effective_actor_id="user-a",
        action="report.read", resource_id="report-a",
    ))
    foreign = execute("LAB-DENY-CROSS-OWNER", "authorize_report", "deny", request(
        event_id="EV-LAB-002", actor_id="user-b", effective_actor_id="user-b",
        action="report.read", resource_id="report-a",
    ))
    execute("LAB-DENY-PENDING", "authorize_report", "deny", request(
        event_id="EV-LAB-003", actor_id="user-a", effective_actor_id="user-a",
        action="report.read", resource_id="report-pending",
    ))
    execute("LAB-DENY-UNKNOWN-REPORT", "authorize_report", "deny", request(
        event_id="EV-LAB-016", actor_id="user-a", effective_actor_id="user-a",
        action="report.read", resource_id="report-missing",
    ))
    execute("LAB-DENY-FOREIGN-TENANT", "authorize_report", "deny", request(
        event_id="EV-LAB-017", actor_id="user-c", effective_actor_id="user-c",
        tenant_id="tenant-42", action="report.read", resource_id="report-a",
    ))
    report_tenant_drift = copy.deepcopy(state)
    report_tenant_drift["reports"]["report-a"]["tenant_id"] = "tenant-99"
    execute("LAB-DENY-REPORT-STATE-TENANT", "authorize_report", "deny", request(
        event_id="EV-LAB-018", actor_id="user-a", effective_actor_id="user-a",
        tenant_id="tenant-42", action="report.read", resource_id="report-a",
    ), report_tenant_drift)
    execute("LAB-DENY-DELEGATED-REPORT-ACTOR", "authorize_report", "deny", request(
        event_id="EV-LAB-019", actor_id="user-a", effective_actor_id="user-b",
        action="report.read", resource_id="report-a",
    ))
    policy_down = copy.deepcopy(state)
    policy_down["policy_available"] = False
    execute("LAB-DENY-POLICY-UNAVAILABLE", "authorize_report", "deny", request(
        event_id="EV-LAB-004", actor_id="user-a", effective_actor_id="user-a",
        action="report.read", resource_id="report-a",
    ), policy_down)
    execute("LAB-DENY-MISSING-REPORT-CONTEXT", "authorize_report", "deny", request(
        event_id="EV-LAB-010", actor_id="user-a", effective_actor_id="user-a",
        tenant_id=None, action="report.read", resource_id="report-a",
    ))
    execute("LAB-DENY-REPORT-ACTION", "authorize_report", "deny", request(
        event_id="EV-LAB-011", actor_id="user-a", effective_actor_id="user-a",
        action=None, resource_id="report-a",
    ))
    normal_object = execute("LAB-NORMAL-JOB", "authorize_object", "allow", request(
        event_id="EV-LAB-005", actor_id="id-report-worker", effective_actor_id="id-report-worker",
        credential_id="cred-job-81", job_id="job-81", action="object.read",
        resource_id="synthetic/tenant-42/job-81/input.json",
    ))
    execute("LAB-DENY-OBJECT-POLICY-UNAVAILABLE", "authorize_object", "deny", request(
        event_id="EV-LAB-020", actor_id="id-report-worker", effective_actor_id="id-report-worker",
        credential_id="cred-job-81", job_id="job-81", action="object.read",
        resource_id="synthetic/tenant-42/job-81/input.json",
    ), policy_down)
    credential_tenant_drift = copy.deepcopy(state)
    credential_tenant_drift["credentials"]["cred-job-81"]["tenant_id"] = "tenant-99"
    execute("LAB-DENY-CREDENTIAL-STATE-TENANT", "authorize_object", "deny", request(
        event_id="EV-LAB-021", actor_id="id-report-worker", effective_actor_id="id-report-worker",
        credential_id="cred-job-81", tenant_id="tenant-42", job_id="job-81", action="object.read",
        resource_id="synthetic/tenant-42/job-81/input.json",
    ), credential_tenant_drift)
    execute("LAB-DENY-DELEGATED-OBJECT-ACTOR", "authorize_object", "deny", request(
        event_id="EV-LAB-022", actor_id="id-report-worker", effective_actor_id="id-other-worker",
        credential_id="cred-job-81", job_id="job-81", action="object.read",
        resource_id="synthetic/tenant-42/job-81/input.json",
    ))
    cross_job = execute("LAB-DENY-CROSS-JOB", "authorize_object", "deny", request(
        event_id="EV-LAB-006", actor_id="id-report-worker", effective_actor_id="id-report-worker",
        credential_id="cred-job-81", job_id="job-9", action="object.read",
        resource_id="synthetic/tenant-42/job-9/input.json",
    ))
    execute("LAB-DENY-PREFIX-CONFUSION", "authorize_object", "deny", request(
        event_id="EV-LAB-007", actor_id="id-report-worker", effective_actor_id="id-report-worker",
        credential_id="cred-job-81", job_id="job-81", action="object.read",
        resource_id="synthetic/tenant-42/job-81x/input.json",
    ))
    execute("LAB-DENY-EXPIRED", "authorize_object", "deny", request(
        event_id="EV-LAB-008", actor_id="id-report-worker", effective_actor_id="id-report-worker",
        credential_id="cred-expired", job_id="job-81", action="object.read",
        resource_id="synthetic/tenant-42/job-81/input.json",
    ))
    execute("LAB-DENY-REVOKED", "authorize_object", "deny", request(
        event_id="EV-LAB-009", actor_id="id-report-worker", effective_actor_id="id-report-worker",
        credential_id="cred-revoked", job_id="job-81", action="object.read",
        resource_id="synthetic/tenant-42/job-81/input.json",
    ))
    execute("LAB-DENY-AT-EXPIRY", "authorize_object", "deny", request(
        event_id="EV-LAB-012", actor_id="id-report-worker", effective_actor_id="id-report-worker",
        credential_id="cred-at-expiry", job_id="job-81", action="object.read",
        resource_id="synthetic/tenant-42/job-81/input.json",
    ))
    execute("LAB-DENY-CREDENTIAL-ACTOR", "authorize_object", "deny", request(
        event_id="EV-LAB-013", actor_id="id-other-worker", effective_actor_id="id-other-worker",
        credential_id="cred-job-81", job_id="job-81", action="object.read",
        resource_id="synthetic/tenant-42/job-81/input.json",
    ))
    execute("LAB-DENY-MISSING-JOB-CONTEXT", "authorize_object", "deny", request(
        event_id="EV-LAB-014", actor_id="id-report-worker", effective_actor_id="id-report-worker",
        credential_id="cred-job-81", job_id=None, action="object.read",
        resource_id="synthetic/tenant-42/job-81/input.json",
    ))

    def result_event(result: object) -> dict | None:
        event = result.get("event") if isinstance(result, dict) else None
        return event if isinstance(event, dict) else None

    owner_event = result_event(owner)
    normal_event = result_event(normal_object)
    foreign_event = result_event(foreign)
    cross_job_event = result_event(cross_job)
    benign = [event for event in (owner_event, normal_event, copy.deepcopy(owner_event)) if event is not None]
    positive = [event for event in (cross_job_event, foreign_event, copy.deepcopy(cross_job_event)) if event is not None]
    positive.reverse()
    benign_alerts = module.detect(benign)
    positive_alerts = module.detect(positive)
    benign_ok = isinstance(benign_alerts, list) and benign_alerts == []
    checks.append({
        "id": "LAB-DETECT-BENIGN",
        "passed": benign_ok,
        "errors": [] if benign_ok else ["unexpected-alert"],
        "observed": len(benign_alerts) if isinstance(benign_alerts, list) else None,
    })
    alert_errors: list[str] = []
    if not isinstance(positive_alerts, list) or len(positive_alerts) != 1 or not isinstance(positive_alerts[0], dict):
        alert_errors.append("alert-count")
    else:
        alert = positive_alerts[0]
        evidence_ids = alert.get("evidence_event_ids", [])
        if set(evidence_ids) != {"EV-LAB-002", "EV-LAB-006"}:
            alert_errors.append("alert-evidence")
        if alert.get("correlation_id") != "CORR-LAB-1":
            alert_errors.append("alert-correlation")
        if set(alert.get("actor_ids", [])) != {"user-b", "id-report-worker"}:
            alert_errors.append("alert-actors")
        if set(alert.get("credential_ids", [])) != {"cred-job-81"}:
            alert_errors.append("alert-credentials")
    checks.append({"id": "LAB-DETECT-POSITIVE", "passed": not alert_errors, "errors": alert_errors, "observed": len(positive_alerts) if isinstance(positive_alerts, list) else None})
    unrelated = copy.deepcopy(foreign_event) if foreign_event is not None else None
    if unrelated is not None:
        unrelated["event_id"] = "EV-LAB-015"
        unrelated["correlation_id"] = "CORR-OTHER"
    separated = module.detect(positive + ([unrelated] if unrelated is not None else []))
    separated_ids = {
        alert.get("correlation_id"): set(alert.get("evidence_event_ids", []))
        for alert in separated if isinstance(alert, dict)
    } if isinstance(separated, list) else {}
    correlation_ok = (
        len(separated_ids) == 2
        and separated_ids.get("CORR-LAB-1") == {"EV-LAB-002", "EV-LAB-006"}
        and separated_ids.get("CORR-OTHER") == {"EV-LAB-015"}
    )
    checks.append({
        "id": "LAB-DETECT-CORRELATION",
        "passed": correlation_ok,
        "errors": [] if correlation_ok else ["unrelated-events-merged"],
        "observed": len(separated_ids),
    })
    return checks, emitted


def run_vulnerable(module, state: dict) -> list[dict]:
    cross_owner = module.authorize_report(state, request(
        event_id="EV-LAB-V01", actor_id="user-b", effective_actor_id="user-b",
        action="report.read", resource_id="report-a",
    ))
    cross_job = module.authorize_object(state, request(
        event_id="EV-LAB-V02", actor_id="id-report-worker", effective_actor_id="id-report-worker",
        credential_id="cred-job-81", job_id="job-9", action="object.read",
        resource_id="synthetic/tenant-42/job-9/input.json",
    ))
    return [
        {"id": "LAB-VULN-CROSS-OWNER", "passed": isinstance(cross_owner, dict) and cross_owner.get("decision") == "allow", "observed": cross_owner.get("decision") if isinstance(cross_owner, dict) else None},
        {"id": "LAB-VULN-CROSS-JOB", "passed": isinstance(cross_job, dict) and cross_job.get("decision") == "allow", "observed": cross_job.get("decision") if isinstance(cross_job, dict) else None},
    ]


def atomic_write(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.is_symlink():
        raise RuntimeError(f"evidence path가 symlink입니다: {path}")
    fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
        os.replace(temp_name, path)
    finally:
        if os.path.exists(temp_name):
            os.unlink(temp_name)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--implementation", required=True, type=Path)
    parser.add_argument("--expect", required=True, choices=("secure", "vulnerable"))
    parser.add_argument("--evidence", type=Path)
    args = parser.parse_args()

    implementation = args.implementation.resolve()
    state = json.loads((ROOT / "fixtures/state.json").read_text(encoding="utf-8"))
    module = load_module(implementation)
    before = state_hash(state)
    if args.expect == "secure":
        checks, events = run_secure(module, state)
    else:
        checks = run_vulnerable(module, state)
        events = []
    after = state_hash(state)
    if before != after:
        checks.append({"id": "LAB-GLOBAL-STATE", "passed": False, "errors": ["state-mutated"]})
    failures = [check for check in checks if not check.get("passed")]
    evidence = {
        "schema_version": 1,
        "profile": args.expect,
        "implementation_sha256": implementation_hash(implementation),
        "state_before_sha256": before,
        "state_after_sha256": after,
        "checks": checks,
        "events": events,
        "limitations": [
            "합성 in-memory policy model만 검사합니다.",
            "checker는 learner Python module을 현재 process에 import하며 OS sandbox를 제공하지 않습니다.",
            "실제 cloud IAM, OS isolation, network path와 production telemetry를 보장하지 않습니다."
        ],
    }
    if args.evidence:
        atomic_write(args.evidence.resolve(), evidence)
    for check in checks:
        label = "PASS" if check.get("passed") else "FAIL"
        print(f"[{label}] {check['id']} observed={check.get('observed')} errors={check.get('errors', [])}")
    print(f"LAB RESULT {'PASS' if not failures else 'FAIL'} checks={len(checks)} failed={len(failures)}")
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
