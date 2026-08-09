"""Public behavior contract for the deterministic platform model."""

from __future__ import annotations

import copy
import json
from dataclasses import dataclass
from typing import Any, Callable


class ContractFailure(AssertionError):
    pass


CANONICAL_IDENTIFIERS = {
    "service_id": "svc-payments",
    "resource_id": "env-payments-staging",
    "operation_id": "op-payments-staging-v3",
    "tenant_id": "tenant-checkout",
    "artifact_id": "sha256:" + "a" * 64,
    "profile_id": "stateless-http/v3",
}

OTHER_TENANT = "tenant-observability"
OTHER_SERVICE = "svc-observability"
OTHER_ENVIRONMENT = "env-observability"


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
            CANONICAL_IDENTIFIERS["tenant_id"]: {"environment_quota": quota_a},
            OTHER_TENANT: {"environment_quota": quota_b},
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
    operation_id: str = CANONICAL_IDENTIFIERS["operation_id"],
    idempotency_key: str = "idem-payments-staging-v3",
    tenant_id: str = CANONICAL_IDENTIFIERS["tenant_id"],
    service_id: str = CANONICAL_IDENTIFIERS["service_id"],
    environment_id: str = CANONICAL_IDENTIFIERS["resource_id"],
    artifact_digest: str = CANONICAL_IDENTIFIERS["artifact_id"],
    profile_version: str = CANONICAL_IDENTIFIERS["profile_id"],
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


def ready(
    module: Any,
    state: dict[str, Any],
    operation_id: str = CANONICAL_IDENTIFIERS["operation_id"],
) -> dict[str, Any]:
    response = call(
        module,
        "reconcile",
        state,
        {
            "operation_id": operation_id,
            "outcome": "ready",
            "observed_generation": 1,
            "evidence": [
                {
                    "kind": "external-smoke",
                    "status": "pass",
                    "revision": "rev-17",
                    "observed_generation": 1,
                }
            ],
        },
    )
    require(response["result"].get("status") == "Ready", "evidenced reconcile must become Ready")
    return response["state"]


def pe_001(module: Any) -> dict[str, Any]:
    state = initial_state()
    accepted = call(module, "request_environment", state, environment_request())
    require(accepted["result"].get("status") == "Accepted", "valid request must be accepted")
    progress = accepted["state"]["environments"].get(CANONICAL_IDENTIFIERS["resource_id"], {})
    require(progress.get("condition") == "Progressing", "accepted request is not Ready yet")
    require(progress.get("generation") == 1, "accepted request needs a positive desired generation")
    require(progress.get("observed_generation") == 0, "new work must not claim the desired generation is observed")
    stale = call(
        module,
        "reconcile",
        accepted["state"],
        {
            "operation_id": CANONICAL_IDENTIFIERS["operation_id"],
            "outcome": "ready",
            "observed_generation": 0,
            "evidence": [
                {
                    "kind": "external-smoke",
                    "status": "pass",
                    "revision": "rev-stale",
                    "observed_generation": 0,
                }
            ],
        },
    )
    require(stale["result"].get("code") == "STALE_GENERATION", "stale observedGeneration must block Ready")
    require(stale["state"] == accepted["state"], "stale Ready attempt must be atomic")
    unstructured = call(
        module,
        "reconcile",
        accepted["state"],
        {
            "operation_id": CANONICAL_IDENTIFIERS["operation_id"],
            "outcome": "ready",
            "observed_generation": 1,
            "evidence": [{"kind": "external-smoke", "status": "pass"}],
        },
    )
    require(
        unstructured["result"].get("code") == "READY_EVIDENCE_REQUIRED",
        "Ready needs structured external smoke evidence bound to the generation",
    )
    require(unstructured["state"] == accepted["state"], "invalid Ready evidence must be atomic")
    reconciled = call(
        module,
        "reconcile",
        accepted["state"],
        {
            "operation_id": CANONICAL_IDENTIFIERS["operation_id"],
            "outcome": "ready",
            "observed_generation": 1,
            "evidence": [
                {
                    "kind": "external-smoke",
                    "status": "pass",
                    "revision": "rev-17",
                    "observed_generation": 1,
                }
            ],
        },
    )
    environment = reconciled["state"]["environments"][CANONICAL_IDENTIFIERS["resource_id"]]
    require(reconciled["result"].get("status") == "Ready", "normal reconcile must become Ready")
    require(environment.get("observed_artifact_digest") == environment.get("artifact_digest"), "observed digest must match desired")
    require(
        environment.get("observed_generation") == environment.get("generation") == 1,
        "Ready requires current generation and observedGeneration",
    )
    require(
        environment.get("evidence") == [
            {
                "kind": "external-smoke",
                "status": "pass",
                "revision": "rev-17",
                "observed_generation": 1,
            }
        ],
        "Ready must retain structured external smoke evidence",
    )
    return {
        "condition": environment["condition"],
        "evidence_count": len(environment["evidence"]),
        "generation": environment["generation"],
        "observed_generation": environment["observed_generation"],
        "smoke_revision": environment["evidence"][0]["revision"],
        "identifiers": dict(CANONICAL_IDENTIFIERS),
    }


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
    no_evidence = call(
        module,
        "reconcile",
        state,
        {
            "operation_id": CANONICAL_IDENTIFIERS["operation_id"],
            "outcome": "ready",
            "observed_generation": 1,
            "evidence": [],
        },
    )
    require(
        no_evidence["state"]["environments"][CANONICAL_IDENTIFIERS["resource_id"]]["condition"] != "Ready",
        "evidence-free Ready must be rejected",
    )
    partial = call(
        module,
        "reconcile",
        state,
        {
            "operation_id": CANONICAL_IDENTIFIERS["operation_id"],
            "outcome": "partial",
            "external_resource_id": "db/tenant-checkout/svc-payments",
            "evidence": [{"kind": "provider-operation", "id": "provider-91"}],
        },
    )
    environment = partial["state"]["environments"][CANONICAL_IDENTIFIERS["resource_id"]]
    require(environment.get("condition") == "Degraded", "partial effect must be visible")
    require(environment.get("cleanup_required") is True, "partial effect must require a decision or cleanup")
    require(
        environment.get("external_effects") == ["db/tenant-checkout/svc-payments"],
        "external effect identity must be retained",
    )
    repeated = call(
        module,
        "reconcile",
        partial["state"],
        {
            "operation_id": CANONICAL_IDENTIFIERS["operation_id"],
            "outcome": "partial",
            "external_resource_id": "db/tenant-checkout/svc-payments",
            "evidence": [{"kind": "provider-operation", "id": "provider-91"}],
        },
    )
    require(
        repeated["state"]["environments"][CANONICAL_IDENTIFIERS["resource_id"]]["external_effects"]
        == ["db/tenant-checkout/svc-payments"],
        "retry must not duplicate the external effect",
    )
    return {"condition": "Degraded", "external_effect_count": 1}


def pe_004(module: Any) -> dict[str, Any]:
    state = initial_state(quota_a=1, quota_b=2)
    a_state = requested(module, state)
    over_quota = environment_request(
        operation_id="op-payments-preview-v3",
        idempotency_key="idem-payments-preview-v3",
        environment_id="env-payments-preview",
    )
    before = copy.deepcopy(a_state)
    rejected = call(module, "request_environment", a_state, over_quota)
    require(rejected["result"].get("code") == "TENANT_QUOTA_EXCEEDED", "tenant quota must reject excess work")
    require(rejected["state"] == before, "quota rejection must be atomic")
    b_request = environment_request(
        operation_id="op-observability-1",
        idempotency_key="idem-observability-1",
        tenant_id=OTHER_TENANT,
        service_id=OTHER_SERVICE,
        environment_id=f"{OTHER_ENVIRONMENT}-1",
    )
    b_state = requested(module, rejected["state"], b_request)
    b_ready = ready(module, b_state, "op-observability-1")
    require(
        b_ready["environments"][f"{OTHER_ENVIRONMENT}-1"]["condition"] == "Ready",
        "the other tenant must progress independently",
    )
    require(
        b_ready["environments"][CANONICAL_IDENTIFIERS["resource_id"]]["condition"] == "Progressing",
        "the canonical tenant work remains independently observable",
    )
    return {"tenant_a": "Progressing", "tenant_b": "Ready", "quota_rejected": True}


def pe_005(module: Any) -> dict[str, Any]:
    state = ready(module, requested(module, initial_state()))
    observed_before = "sha256:" + "d" * 64
    drifted = call(
        module,
        "observe_drift",
        state,
        {
            "environment_id": CANONICAL_IDENTIFIERS["resource_id"],
            "observed_artifact_digest": observed_before,
            "break_glass": False,
        },
    )
    environment = drifted["state"]["environments"][CANONICAL_IDENTIFIERS["resource_id"]]
    require(drifted["result"].get("code") == "DRIFT_REVERTED", "ordinary drift must reconcile")
    require(environment["observed_artifact_digest"] == environment["artifact_digest"], "observed state must converge to desired")
    expected_evidence = {
        "event": "drift.reconciled",
        "environment_id": CANONICAL_IDENTIFIERS["resource_id"],
        "desired": environment["artifact_digest"],
        "observed_before": observed_before,
        "observed_after": environment["artifact_digest"],
    }
    require(expected_evidence in environment.get("evidence", []), "environment needs desired and before/after drift evidence")
    require(expected_evidence in drifted["state"]["audit_events"], "audit needs desired and before/after drift evidence")
    return {
        "status": drifted["result"]["status"],
        "converged": True,
        "observed_before": observed_before,
        "observed_after": environment["artifact_digest"],
    }


def pe_006(module: Any) -> dict[str, Any]:
    state = ready(module, requested(module, initial_state()))
    unbounded = call(
        module,
        "observe_drift",
        state,
        {
            "environment_id": CANONICAL_IDENTIFIERS["resource_id"],
            "observed_artifact_digest": "sha256:" + "e" * 64,
            "break_glass": True,
        },
    )
    require(unbounded["result"].get("code") == "UNBOUNDED_BREAK_GLASS", "unbounded emergency change must be rejected")
    require(unbounded["state"] == state, "rejected break-glass must not change state")
    bounded = call(
        module,
        "observe_drift",
        state,
        {
            "environment_id": CANONICAL_IDENTIFIERS["resource_id"],
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
    require(
        exception.get("approved_by")
        and exception.get("expires_at")
        and exception.get("reason") == "containment"
        and exception.get("evidence"),
        "exception needs owner, expiry, reason and evidence",
    )
    return {
        "rejected_unbounded": True,
        "exception_status": exception["status"],
        "reason": exception["reason"],
    }


def pe_007(module: Any) -> dict[str, Any]:
    state = initial_state()
    request = environment_request(credential_mode="static-fallback")
    rejected = call(module, "request_environment", state, request)
    require(rejected["result"].get("code") == "STATIC_CREDENTIAL_FALLBACK", "static fallback must be denied")
    require(rejected["state"] == state, "credential denial must be atomic")
    accepted = call(module, "request_environment", state, environment_request())
    credential = accepted["state"]["credentials"][CANONICAL_IDENTIFIERS["resource_id"]]
    require(credential.get("mode") == "workload-identity" and credential.get("static_secret") is False, "accepted path must use workload identity")
    return {"static_denied": True, "mode": credential["mode"]}


def pe_008(module: Any) -> dict[str, Any]:
    state = initial_state()
    for index in range(1, 4):
        request = environment_request(
            operation_id=f"op-observability-{index}",
            idempotency_key=f"idem-observability-{index}",
            tenant_id=OTHER_TENANT,
            service_id=f"{OTHER_SERVICE}-{index}",
            environment_id=f"{OTHER_ENVIRONMENT}-{index}",
            profile_version="stateless-http/v2",
        )
        state = requested(module, state, request)
    migration_request = {
        "migration_id": "mig-v3",
        "profile_from": "stateless-http/v2",
        "profile_to": "stateless-http/v3",
        "fail_wave": "wave-2",
        "abort_evidence": {
            "kind": "slo-regression",
            "metric": "p99_latency_ms",
            "observed": 420,
            "threshold": 250,
            "decision": "abort",
        },
        "waves": [
            {"name": "wave-1", "targets": [f"{OTHER_ENVIRONMENT}-1"]},
            {"name": "wave-2", "targets": [f"{OTHER_ENVIRONMENT}-2"]},
            {"name": "wave-3", "targets": [f"{OTHER_ENVIRONMENT}-3"]},
        ],
    }
    missing_evidence = copy.deepcopy(migration_request)
    missing_evidence.pop("abort_evidence")
    rejected = call(module, "request_migration", state, missing_evidence)
    require(
        rejected["result"].get("code") == "MIGRATION_ABORT_EVIDENCE_REQUIRED",
        "failed wave must not abort without structured evidence",
    )
    require(rejected["state"] == state, "missing abort evidence must be atomic")
    migration = call(
        module,
        "request_migration",
        state,
        migration_request,
    )
    record = migration["state"]["migrations"]["mig-v3"]
    require(record.get("status") == "Aborted", "failed wave must abort migration")
    require(record.get("abort_evidence") == migration_request["abort_evidence"], "abort must retain structured evidence")
    require([item["status"] for item in record["waves"]] == ["Completed", "Failed", "Pending"], "later waves must remain pending")
    require(
        migration["state"]["environments"][f"{OTHER_ENVIRONMENT}-1"]["profile_version"] == "stateless-http/v3",
        "completed wave must be visible",
    )
    require(
        migration["state"]["environments"][f"{OTHER_ENVIRONMENT}-2"]["profile_version"] == "stateless-http/v2",
        "failed wave must not be promoted",
    )
    require(
        migration["state"]["environments"][f"{OTHER_ENVIRONMENT}-3"]["profile_version"] == "stateless-http/v2",
        "pending wave must not run",
    )
    return {
        "statuses": [item["status"] for item in record["waves"]],
        "aborted": True,
        "abort_metric": record["abort_evidence"]["metric"],
    }


def pe_009(module: Any) -> dict[str, Any]:
    state = ready(module, requested(module, initial_state(), environment_request()))
    exception_state = call(
        module,
        "observe_drift",
        state,
        {
            "environment_id": CANONICAL_IDENTIFIERS["resource_id"],
            "observed_artifact_digest": "sha256:" + "e" * 64,
            "break_glass": True,
            "approved_by": "incident-commander",
            "expires_at": "2026-08-11T03:00:00Z",
            "reason": "retirement containment",
            "evidence": "INC-RET-7",
        },
    )
    require(len(exception_state["state"].get("break_glass", [])) == 1, "retirement fixture must begin with an exception")
    state = exception_state["state"]
    state = requested(
        module,
        state,
        environment_request(
            operation_id="op-observability-1",
            idempotency_key="idem-observability-1",
            tenant_id=OTHER_TENANT,
            service_id=OTHER_SERVICE,
            environment_id=f"{OTHER_ENVIRONMENT}-1",
        ),
    )
    retired = call(
        module,
        "retire_service",
        state,
        {
            "operation_id": "retire-svc-payments",
            "service_id": CANONICAL_IDENTIFIERS["service_id"],
            "approved_by": "owner-payments",
            "evidence": "RET-7",
        },
    )
    final = retired["state"]
    require(CANONICAL_IDENTIFIERS["resource_id"] not in final["environments"], "retired runtime state must be removed")
    require(CANONICAL_IDENTIFIERS["resource_id"] not in final["credentials"], "retired credential must be removed")
    require(CANONICAL_IDENTIFIERS["operation_id"] not in final["operations"], "retired queue/operation state must be removed")
    require(
        not any(item.get("environment_id") == CANONICAL_IDENTIFIERS["resource_id"] for item in final.get("break_glass", [])),
        "retired environment exceptions must be removed",
    )
    require(CANONICAL_IDENTIFIERS["service_id"] in final["tombstones"], "retirement tombstone must remain")
    require(f"{OTHER_ENVIRONMENT}-1" in final["environments"], "another tenant/service must remain")
    repeated = call(
        module,
        "retire_service",
        final,
        {
            "operation_id": "retire-svc-payments",
            "service_id": CANONICAL_IDENTIFIERS["service_id"],
            "approved_by": "owner-payments",
            "evidence": "RET-7",
        },
    )
    require(repeated["result"].get("reused") is True, "retirement retry must be idempotent")
    require(repeated["state"] == final, "retirement retry must not change evidence")
    return {
        "retired": CANONICAL_IDENTIFIERS["service_id"],
        "other_environment_retained": True,
        "exceptions_removed": 1,
    }


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
    first["tenants"][CANONICAL_IDENTIFIERS["tenant_id"]]["environment_quota"] = 999
    second = module.snapshot(state)
    require(
        second["tenants"][CANONICAL_IDENTIFIERS["tenant_id"]]["environment_quota"] != 999,
        "snapshot must be a deep copy",
    )
    require(second == module.snapshot(state), "snapshot must be deterministic")
    return {"redacted": True, "deep_copy": True, "deterministic": True}


CHECKS = (
    Check("PE-001", "normal", "current observed generation and structured smoke reach Ready", pe_001),
    Check("PE-002", "boundary", "idempotency retry reuses and changed payload conflicts", pe_002),
    Check("PE-003", "failure", "evidence-free Ready is denied and partial effects stay visible", pe_003),
    Check("PE-004", "isolation", "tenant quota and queue progress are isolated", pe_004),
    Check("PE-005", "drift", "ordinary drift records before and after then converges", pe_005),
    Check("PE-006", "break-glass", "emergency drift requires owner expiry reason and evidence", pe_006),
    Check("PE-007", "identity", "static credential fallback is prohibited", pe_007),
    Check("PE-008", "migration", "failed migration wave retains abort evidence and stops later waves", pe_008),
    Check("PE-009", "retirement", "retirement cleans active state and open exceptions", pe_009),
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
