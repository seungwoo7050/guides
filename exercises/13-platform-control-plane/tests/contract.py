"""Public behavior contract for the deterministic platform model."""

from __future__ import annotations

import copy
import json
from dataclasses import dataclass
from typing import Any, Callable


class ContractFailure(AssertionError):
    pass


@dataclass(frozen=True)
class Check:
    id: str
    kind: str
    title: str
    run: Callable[[Any], dict[str, Any]]


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ContractFailure(message)


def initial_state(*, quota_a: int = 2, quota_b: int = 3) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "tenants": {
            "tenant-a": {"environment_quota": quota_a},
            "tenant-b": {"environment_quota": quota_b},
        },
        "environments": {},
        "operations": {},
        "idempotency": {},
        "credentials": {},
        "migrations": {},
        "break_glass": [],
        "tombstones": {},
        "audit_events": [],
    }


def environment_request(
    *,
    operation_id: str = "op-a-1",
    idempotency_key: str = "idem-a-1",
    tenant_id: str = "tenant-a",
    service_id: str = "svc-a",
    environment_id: str = "env-a-1",
    artifact_digest: str = "sha256:" + "a" * 64,
    profile_version: str = "stateless-http/v2",
    credential_mode: str = "workload-identity",
) -> dict[str, Any]:
    return {
        "operation_id": operation_id,
        "idempotency_key": idempotency_key,
        "tenant_id": tenant_id,
        "service_id": service_id,
        "environment_id": environment_id,
        "artifact_digest": artifact_digest,
        "profile_version": profile_version,
        "credential_mode": credential_mode,
    }


def call(module: Any, name: str, state: dict[str, Any], request: dict[str, Any]) -> dict[str, Any]:
    before = copy.deepcopy(state)
    value = getattr(module, name)(state, request)
    require(state == before, f"{name} mutated its input state")
    require(isinstance(value, dict), f"{name} must return an object")
    require(set(value) == {"state", "result"}, f"{name} must return state and result")
    require(isinstance(value["state"], dict), f"{name}.state must be an object")
    require(isinstance(value["result"], dict), f"{name}.result must be an object")
    json.dumps(value, ensure_ascii=False, sort_keys=True)
    return value


def requested(module: Any, state: dict[str, Any], request: dict[str, Any] | None = None) -> dict[str, Any]:
    response = call(module, "request_environment", state, request or environment_request())
    require(response["result"].get("status") == "Accepted", "request must be accepted")
    return response["state"]


def ready(module: Any, state: dict[str, Any], operation_id: str = "op-a-1") -> dict[str, Any]:
    response = call(
        module,
        "reconcile",
        state,
        {
            "operation_id": operation_id,
            "outcome": "ready",
            "evidence": [{"kind": "external-smoke", "status": "pass"}],
        },
    )
    require(response["result"].get("status") == "Ready", "evidenced reconcile must become Ready")
    return response["state"]


def pe_001(module: Any) -> dict[str, Any]:
    state = initial_state()
    accepted = call(module, "request_environment", state, environment_request())
    require(accepted["result"].get("status") == "Accepted", "valid request must be accepted")
    progress = accepted["state"]["environments"].get("env-a-1", {})
    require(progress.get("condition") == "Progressing", "accepted request is not Ready yet")
    reconciled = call(
        module,
        "reconcile",
        accepted["state"],
        {
            "operation_id": "op-a-1",
            "outcome": "ready",
            "evidence": [{"kind": "external-smoke", "status": "pass", "revision": "rev-17"}],
        },
    )
    environment = reconciled["state"]["environments"]["env-a-1"]
    require(reconciled["result"].get("status") == "Ready", "normal reconcile must become Ready")
    require(environment.get("observed_artifact_digest") == environment.get("artifact_digest"), "observed digest must match desired")
    require(environment.get("evidence"), "Ready must retain external evidence")
    return {"condition": environment["condition"], "evidence_count": len(environment["evidence"])}


def pe_002(module: Any) -> dict[str, Any]:
    state = initial_state()
    first = call(module, "request_environment", state, environment_request())
    repeated = call(module, "request_environment", first["state"], environment_request())
    require(repeated["result"].get("reused") is True, "same request must reuse the operation")
    require(len(repeated["state"]["environments"]) == 1, "retry must not create a duplicate environment")
    conflicting = environment_request(artifact_digest="sha256:" + "b" * 64)
    before = copy.deepcopy(repeated["state"])
    conflict = call(module, "request_environment", repeated["state"], conflicting)
    require(conflict["result"].get("code") == "IDEMPOTENCY_CONFLICT", "changed payload must conflict")
    require(conflict["state"] == before, "idempotency conflict must be atomic")
    return {"environment_count": 1, "conflict": conflict["result"]["code"]}


def pe_003(module: Any) -> dict[str, Any]:
    state = requested(module, initial_state())
    no_evidence = call(module, "reconcile", state, {"operation_id": "op-a-1", "outcome": "ready", "evidence": []})
    require(no_evidence["state"]["environments"]["env-a-1"]["condition"] != "Ready", "evidence-free Ready must be rejected")
    partial = call(
        module,
        "reconcile",
        state,
        {
            "operation_id": "op-a-1",
            "outcome": "partial",
            "external_resource_id": "db/tenant-a/svc-a",
            "evidence": [{"kind": "provider-operation", "id": "provider-91"}],
        },
    )
    environment = partial["state"]["environments"]["env-a-1"]
    require(environment.get("condition") == "Degraded", "partial effect must be visible")
    require(environment.get("cleanup_required") is True, "partial effect must require a decision or cleanup")
    require(environment.get("external_effects") == ["db/tenant-a/svc-a"], "external effect identity must be retained")
    repeated = call(
        module,
        "reconcile",
        partial["state"],
        {
            "operation_id": "op-a-1",
            "outcome": "partial",
            "external_resource_id": "db/tenant-a/svc-a",
            "evidence": [{"kind": "provider-operation", "id": "provider-91"}],
        },
    )
    require(repeated["state"]["environments"]["env-a-1"]["external_effects"] == ["db/tenant-a/svc-a"], "retry must not duplicate the external effect")
    return {"condition": "Degraded", "external_effect_count": 1}


def pe_004(module: Any) -> dict[str, Any]:
    state = initial_state(quota_a=1, quota_b=2)
    a_state = requested(module, state)
    over_quota = environment_request(
        operation_id="op-a-2",
        idempotency_key="idem-a-2",
        environment_id="env-a-2",
    )
    before = copy.deepcopy(a_state)
    rejected = call(module, "request_environment", a_state, over_quota)
    require(rejected["result"].get("code") == "TENANT_QUOTA_EXCEEDED", "tenant quota must reject excess work")
    require(rejected["state"] == before, "quota rejection must be atomic")
    b_request = environment_request(
        operation_id="op-b-1",
        idempotency_key="idem-b-1",
        tenant_id="tenant-b",
        service_id="svc-b",
        environment_id="env-b-1",
    )
    b_state = requested(module, rejected["state"], b_request)
    b_ready = ready(module, b_state, "op-b-1")
    require(b_ready["environments"]["env-b-1"]["condition"] == "Ready", "tenant-b must progress independently")
    require(b_ready["environments"]["env-a-1"]["condition"] == "Progressing", "tenant-a work remains independently observable")
    return {"tenant_a": "Progressing", "tenant_b": "Ready", "quota_rejected": True}


def pe_005(module: Any) -> dict[str, Any]:
    state = ready(module, requested(module, initial_state()))
    drifted = call(
        module,
        "observe_drift",
        state,
        {"environment_id": "env-a-1", "observed_artifact_digest": "sha256:" + "d" * 64, "break_glass": False},
    )
    environment = drifted["state"]["environments"]["env-a-1"]
    require(drifted["result"].get("code") == "DRIFT_REVERTED", "ordinary drift must reconcile")
    require(environment["observed_artifact_digest"] == environment["artifact_digest"], "observed state must converge to desired")
    require(any(item.get("event") == "drift.reconciled" for item in drifted["state"]["audit_events"]), "drift evidence is required")
    return {"status": drifted["result"]["status"], "converged": True}


def pe_006(module: Any) -> dict[str, Any]:
    state = ready(module, requested(module, initial_state()))
    unbounded = call(
        module,
        "observe_drift",
        state,
        {"environment_id": "env-a-1", "observed_artifact_digest": "sha256:" + "e" * 64, "break_glass": True},
    )
    require(unbounded["result"].get("code") == "UNBOUNDED_BREAK_GLASS", "unbounded emergency change must be rejected")
    require(unbounded["state"] == state, "rejected break-glass must not change state")
    bounded = call(
        module,
        "observe_drift",
        state,
        {
            "environment_id": "env-a-1",
            "observed_artifact_digest": "sha256:" + "e" * 64,
            "break_glass": True,
            "approved_by": "incident-commander",
            "expires_at": "2026-08-11T03:00:00Z",
            "reason": "containment",
            "evidence": "INC-42",
        },
    )
    require(bounded["result"].get("code") == "BOUNDED_BREAK_GLASS", "bounded change must be recorded")
    exception = bounded["state"].get("break_glass", [])[0]
    require(exception.get("approved_by") and exception.get("expires_at") and exception.get("evidence"), "exception needs owner, expiry and evidence")
    return {"rejected_unbounded": True, "exception_status": exception["status"]}


def pe_007(module: Any) -> dict[str, Any]:
    state = initial_state()
    request = environment_request(credential_mode="static-fallback")
    rejected = call(module, "request_environment", state, request)
    require(rejected["result"].get("code") == "STATIC_CREDENTIAL_FALLBACK", "static fallback must be denied")
    require(rejected["state"] == state, "credential denial must be atomic")
    accepted = call(module, "request_environment", state, environment_request())
    credential = accepted["state"]["credentials"]["env-a-1"]
    require(credential.get("mode") == "workload-identity" and credential.get("static_secret") is False, "accepted path must use workload identity")
    return {"static_denied": True, "mode": credential["mode"]}


def pe_008(module: Any) -> dict[str, Any]:
    state = initial_state()
    for index in range(1, 4):
        request = environment_request(
            operation_id=f"op-b-{index}",
            idempotency_key=f"idem-b-{index}",
            tenant_id="tenant-b",
            service_id=f"svc-{index}",
            environment_id=f"env-b-{index}",
        )
        state = requested(module, state, request)
    migration = call(
        module,
        "request_migration",
        state,
        {
            "migration_id": "mig-v3",
            "profile_from": "stateless-http/v2",
            "profile_to": "stateless-http/v3",
            "fail_wave": "wave-2",
            "abort_evidence": "p99 regression",
            "waves": [
                {"name": "wave-1", "targets": ["env-b-1"]},
                {"name": "wave-2", "targets": ["env-b-2"]},
                {"name": "wave-3", "targets": ["env-b-3"]},
            ],
        },
    )
    record = migration["state"]["migrations"]["mig-v3"]
    require(record.get("status") == "Aborted", "failed wave must abort migration")
    require([item["status"] for item in record["waves"]] == ["Completed", "Failed", "Pending"], "later waves must remain pending")
    require(migration["state"]["environments"]["env-b-1"]["profile_version"] == "stateless-http/v3", "completed wave must be visible")
    require(migration["state"]["environments"]["env-b-2"]["profile_version"] == "stateless-http/v2", "failed wave must not be promoted")
    require(migration["state"]["environments"]["env-b-3"]["profile_version"] == "stateless-http/v2", "pending wave must not run")
    return {"statuses": [item["status"] for item in record["waves"]], "aborted": True}


def pe_009(module: Any) -> dict[str, Any]:
    state = requested(module, initial_state(), environment_request())
    state = requested(
        module,
        state,
        environment_request(
            operation_id="op-b-1",
            idempotency_key="idem-b-1",
            tenant_id="tenant-b",
            service_id="svc-b",
            environment_id="env-b-1",
        ),
    )
    retired = call(
        module,
        "retire_service",
        state,
        {"operation_id": "retire-svc-a", "service_id": "svc-a", "approved_by": "owner-a", "evidence": "RET-7"},
    )
    final = retired["state"]
    require("env-a-1" not in final["environments"], "retired runtime state must be removed")
    require("env-a-1" not in final["credentials"], "retired credential must be removed")
    require("op-a-1" not in final["operations"], "retired queue/operation state must be removed")
    require("svc-a" in final["tombstones"], "retirement tombstone must remain")
    require("env-b-1" in final["environments"], "another tenant/service must remain")
    repeated = call(
        module,
        "retire_service",
        final,
        {"operation_id": "retire-svc-a", "service_id": "svc-a", "approved_by": "owner-a", "evidence": "RET-7"},
    )
    require(repeated["result"].get("reused") is True, "retirement retry must be idempotent")
    require(repeated["state"] == final, "retirement retry must not change evidence")
    return {"retired": "svc-a", "other_environment_retained": True}


def pe_010(module: Any) -> dict[str, Any]:
    state = initial_state()
    state["credentials"]["synthetic"] = {
        "mode": "fixture",
        "secret_value": "must-not-appear",
        "private_key": "must-not-appear-either",
    }
    before = copy.deepcopy(state)
    first = module.snapshot(state)
    require(state == before, "snapshot must not mutate state")
    require(isinstance(first, dict), "snapshot must return an object")
    serialized = json.dumps(first, ensure_ascii=False, sort_keys=True)
    require("must-not-appear" not in serialized, "snapshot must redact secret material")
    first["tenants"]["tenant-a"]["environment_quota"] = 999
    second = module.snapshot(state)
    require(second["tenants"]["tenant-a"]["environment_quota"] != 999, "snapshot must be a deep copy")
    require(second == module.snapshot(state), "snapshot must be deterministic")
    return {"redacted": True, "deep_copy": True, "deterministic": True}


CHECKS = (
    Check("PE-001", "normal", "request and evidenced reconcile reach Ready", pe_001),
    Check("PE-002", "boundary", "idempotency retry reuses and changed payload conflicts", pe_002),
    Check("PE-003", "failure", "evidence-free Ready is denied and partial effects stay visible", pe_003),
    Check("PE-004", "isolation", "tenant quota and queue progress are isolated", pe_004),
    Check("PE-005", "drift", "ordinary drift converges to desired state", pe_005),
    Check("PE-006", "break-glass", "emergency drift requires owner expiry and evidence", pe_006),
    Check("PE-007", "identity", "static credential fallback is prohibited", pe_007),
    Check("PE-008", "migration", "failed migration wave aborts later waves", pe_008),
    Check("PE-009", "retirement", "retirement cleans active state and retains evidence", pe_009),
    Check("PE-010", "evidence", "snapshot is deterministic private and detached", pe_010),
)


def run_contract(module: Any) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for check in CHECKS:
        record: dict[str, Any] = {
            "id": check.id,
            "kind": check.kind,
            "title": check.title,
            "status": "pass",
            "message": "contract satisfied",
            "observed": {},
        }
        try:
            record["observed"] = check.run(module)
        except ContractFailure as error:
            record["status"] = "fail"
            record["message"] = str(error)
        except Exception as error:  # learner public API failures are reported, not hidden
            record["status"] = "error"
            record["message"] = f"{type(error).__name__}: {error}"
        records.append(record)
    return records
