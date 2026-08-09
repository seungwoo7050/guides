"""Deterministic platform control-plane reference implementation.

The public functions accept and return JSON-compatible dictionaries.  They do
not contact a network, spawn processes, read credentials, or create resources.
"""

from __future__ import annotations

import copy
import hashlib
import json
from typing import Any


def _clone(value: Any) -> Any:
    return copy.deepcopy(value)


def _result(state: dict[str, Any], **result: Any) -> dict[str, Any]:
    return {"state": state, "result": result}


def _signature(request: dict[str, Any]) -> str:
    fields = {
        key: request.get(key)
        for key in (
            "operation_id",
            "tenant_id",
            "service_id",
            "environment_id",
            "artifact_digest",
            "profile_version",
            "credential_mode",
        )
    }
    payload = json.dumps(fields, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _required(request: dict[str, Any], names: tuple[str, ...]) -> str | None:
    for name in names:
        if not isinstance(request.get(name), str) or not request[name].strip():
            return name
    return None


def _external_smoke(evidence: Any, generation: int) -> dict[str, Any] | None:
    """Return smoke evidence bound to the current desired generation."""

    if not isinstance(evidence, list):
        return None
    for item in evidence:
        if (
            isinstance(item, dict)
            and item.get("kind") == "external-smoke"
            and item.get("status") == "pass"
            and isinstance(item.get("revision"), str)
            and bool(item["revision"].strip())
            and item.get("observed_generation") == generation
        ):
            return item
    return None


def request_environment(state: dict[str, Any], request: dict[str, Any]) -> dict[str, Any]:
    """Accept one tenant-scoped environment request or reject it atomically."""

    original = _clone(state)
    missing = _required(
        request,
        (
            "operation_id",
            "idempotency_key",
            "tenant_id",
            "service_id",
            "environment_id",
            "artifact_digest",
            "profile_version",
            "credential_mode",
        ),
    )
    if missing:
        return _result(original, status="Rejected", code="INVALID_REQUEST", field=missing)

    tenant_id = request["tenant_id"]
    tenant = original.get("tenants", {}).get(tenant_id)
    if not isinstance(tenant, dict):
        return _result(original, status="Rejected", code="UNKNOWN_TENANT")
    if request["credential_mode"] != "workload-identity":
        return _result(original, status="Rejected", code="STATIC_CREDENTIAL_FALLBACK")

    key = request["idempotency_key"]
    signature = _signature(request)
    existing = original.get("idempotency", {}).get(key)
    if isinstance(existing, dict):
        if existing.get("signature") != signature:
            return _result(
                original,
                status="Conflict",
                code="IDEMPOTENCY_CONFLICT",
                operation_id=existing.get("operation_id"),
            )
        return _result(
            original,
            status="Accepted",
            code="REUSED_OPERATION",
            operation_id=existing["operation_id"],
            reused=True,
        )

    environment_id = request["environment_id"]
    if environment_id in original.get("environments", {}):
        return _result(original, status="Conflict", code="ENVIRONMENT_EXISTS")

    active = sum(
        1
        for environment in original.get("environments", {}).values()
        if environment.get("tenant_id") == tenant_id
        and environment.get("condition") not in {"Retired", "Deleted"}
    )
    quota = int(tenant.get("environment_quota", 0))
    if active >= quota:
        return _result(original, status="Rejected", code="TENANT_QUOTA_EXCEEDED")

    updated = _clone(original)
    operation_id = request["operation_id"]
    environment = {
        "environment_id": environment_id,
        "tenant_id": tenant_id,
        "service_id": request["service_id"],
        "artifact_digest": request["artifact_digest"],
        "observed_artifact_digest": None,
        "profile_version": request["profile_version"],
        "generation": 1,
        "observed_generation": 0,
        "condition": "Progressing",
        "external_effects": [],
        "cleanup_required": False,
        "evidence": [],
    }
    updated.setdefault("environments", {})[environment_id] = environment
    updated.setdefault("operations", {})[operation_id] = {
        "operation_id": operation_id,
        "tenant_id": tenant_id,
        "service_id": request["service_id"],
        "environment_id": environment_id,
        "status": "Accepted",
        "attempts": 0,
    }
    updated.setdefault("idempotency", {})[key] = {
        "signature": signature,
        "operation_id": operation_id,
    }
    updated.setdefault("credentials", {})[environment_id] = {
        "mode": "workload-identity",
        "identity": f"spiffe://northstar/{tenant_id}/{request['service_id']}",
        "static_secret": False,
    }
    updated.setdefault("audit_events", []).append(
        {
            "event": "environment.requested",
            "operation_id": operation_id,
            "tenant_id": tenant_id,
            "environment_id": environment_id,
        }
    )
    return _result(updated, status="Accepted", code="NEW_OPERATION", operation_id=operation_id, reused=False)


def reconcile(state: dict[str, Any], request: dict[str, Any]) -> dict[str, Any]:
    """Apply one observable reconcile outcome without hiding partial effects."""

    original = _clone(state)
    operation_id = request.get("operation_id")
    operation = original.get("operations", {}).get(operation_id)
    if not isinstance(operation, dict):
        return _result(original, status="Rejected", code="UNKNOWN_OPERATION")
    environment_id = operation["environment_id"]
    outcome = request.get("outcome")
    if outcome not in {"ready", "partial", "blocked"}:
        return _result(original, status="Rejected", code="INVALID_OUTCOME")
    evidence = request.get("evidence")
    if not isinstance(evidence, list):
        evidence = []
    current_environment = original["environments"][environment_id]
    current_generation = current_environment.get("generation")
    if outcome == "ready":
        if (
            not isinstance(current_generation, int)
            or isinstance(current_generation, bool)
            or current_generation < 1
            or request.get("observed_generation") != current_generation
        ):
            return _result(original, status="Blocked", code="STALE_GENERATION")
        if _external_smoke(evidence, current_generation) is None:
            return _result(original, status="Blocked", code="READY_EVIDENCE_REQUIRED")

    updated = _clone(original)
    current_operation = updated["operations"][operation_id]
    environment = updated["environments"][environment_id]
    current_operation["attempts"] = int(current_operation.get("attempts", 0)) + 1

    if outcome == "partial":
        external_resource_id = request.get("external_resource_id")
        if not isinstance(external_resource_id, str) or not external_resource_id:
            return _result(original, status="Rejected", code="PARTIAL_EFFECT_ID_REQUIRED")
        if external_resource_id not in environment["external_effects"]:
            environment["external_effects"].append(external_resource_id)
        environment["condition"] = "Degraded"
        environment["cleanup_required"] = True
        environment["evidence"].extend(_clone(evidence))
        current_operation["status"] = "Partial"
        code = "PARTIAL_EFFECT_RECORDED"
    elif outcome == "blocked":
        environment["condition"] = "Blocked"
        environment["evidence"].extend(_clone(evidence))
        current_operation["status"] = "Blocked"
        code = "OPERATION_BLOCKED"
    else:
        environment["condition"] = "Ready"
        environment["observed_artifact_digest"] = environment["artifact_digest"]
        environment["observed_generation"] = environment["generation"]
        environment["cleanup_required"] = False
        environment["evidence"].extend(_clone(evidence))
        current_operation["status"] = "Ready"
        code = "READY_WITH_EVIDENCE"

    updated.setdefault("audit_events", []).append(
        {
            "event": "environment.reconciled",
            "operation_id": operation_id,
            "environment_id": environment_id,
            "outcome": outcome,
            "condition": environment["condition"],
        }
    )
    return _result(updated, status=environment["condition"], code=code, operation_id=operation_id)


def observe_drift(state: dict[str, Any], request: dict[str, Any]) -> dict[str, Any]:
    """Reconcile ordinary drift or record a bounded break-glass exception."""

    original = _clone(state)
    environment_id = request.get("environment_id")
    environment = original.get("environments", {}).get(environment_id)
    if not isinstance(environment, dict):
        return _result(original, status="Rejected", code="UNKNOWN_ENVIRONMENT")
    observed = request.get("observed_artifact_digest")
    if not isinstance(observed, str) or not observed:
        return _result(original, status="Rejected", code="INVALID_OBSERVED_STATE")
    desired = environment["artifact_digest"]
    if observed == desired:
        updated = _clone(original)
        updated["environments"][environment_id]["observed_artifact_digest"] = observed
        return _result(updated, status="InSync", code="NO_DRIFT")

    if request.get("break_glass") is True:
        required = ("approved_by", "expires_at", "reason", "evidence")
        if any(not request.get(field) for field in required):
            return _result(original, status="Rejected", code="UNBOUNDED_BREAK_GLASS")
        updated = _clone(original)
        current = updated["environments"][environment_id]
        current["observed_artifact_digest"] = observed
        current["condition"] = "Degraded"
        exception = {
            "environment_id": environment_id,
            "desired": desired,
            "observed": observed,
            "approved_by": request["approved_by"],
            "expires_at": request["expires_at"],
            "reason": request["reason"],
            "evidence": request["evidence"],
            "status": "Open",
        }
        updated.setdefault("break_glass", []).append(exception)
        updated.setdefault("audit_events", []).append(
            {"event": "drift.break-glass", **exception}
        )
        return _result(updated, status="EmergencyChange", code="BOUNDED_BREAK_GLASS")

    updated = _clone(original)
    current = updated["environments"][environment_id]
    current["observed_artifact_digest"] = desired
    current["condition"] = "Ready"
    evidence = {
        "event": "drift.reconciled",
        "environment_id": environment_id,
        "desired": desired,
        "observed_before": observed,
        "observed_after": desired,
    }
    current.setdefault("evidence", []).append(evidence)
    updated.setdefault("audit_events", []).append(evidence)
    return _result(updated, status="Reconciled", code="DRIFT_REVERTED")


def request_migration(state: dict[str, Any], request: dict[str, Any]) -> dict[str, Any]:
    """Run ordered waves and stop at the first declared failure."""

    original = _clone(state)
    missing = _required(request, ("migration_id", "profile_from", "profile_to"))
    waves = request.get("waves")
    if missing or not isinstance(waves, list) or not waves:
        return _result(original, status="Rejected", code="INVALID_MIGRATION")
    if any(not isinstance(wave, dict) or not wave.get("name") or not isinstance(wave.get("targets"), list) for wave in waves):
        return _result(original, status="Rejected", code="INVALID_WAVE")

    failed_wave = request.get("fail_wave")
    abort_evidence = request.get("abort_evidence")
    if failed_wave is not None and not (
        isinstance(abort_evidence, dict)
        and abort_evidence.get("kind") == "slo-regression"
        and isinstance(abort_evidence.get("metric"), str)
        and bool(abort_evidence["metric"].strip())
        and isinstance(abort_evidence.get("observed"), (int, float))
        and not isinstance(abort_evidence.get("observed"), bool)
        and isinstance(abort_evidence.get("threshold"), (int, float))
        and not isinstance(abort_evidence.get("threshold"), bool)
        and abort_evidence.get("decision") == "abort"
    ):
        return _result(original, status="Rejected", code="MIGRATION_ABORT_EVIDENCE_REQUIRED")

    updated = _clone(original)
    records: list[dict[str, Any]] = []
    aborted = False
    for wave in waves:
        if aborted:
            records.append({"name": wave["name"], "targets": _clone(wave["targets"]), "status": "Pending"})
            continue
        if wave["name"] == failed_wave:
            records.append({"name": wave["name"], "targets": _clone(wave["targets"]), "status": "Failed"})
            aborted = True
            continue
        records.append({"name": wave["name"], "targets": _clone(wave["targets"]), "status": "Completed"})
        for target in wave["targets"]:
            environment = updated.get("environments", {}).get(target)
            if isinstance(environment, dict):
                environment["profile_version"] = request["profile_to"]

    status = "Aborted" if aborted else "Completed"
    migration = {
        "migration_id": request["migration_id"],
        "profile_from": request["profile_from"],
        "profile_to": request["profile_to"],
        "status": status,
        "waves": records,
        "abort_evidence": _clone(abort_evidence) if aborted else None,
    }
    updated.setdefault("migrations", {})[request["migration_id"]] = migration
    updated.setdefault("audit_events", []).append(
        {"event": "migration.finished", "migration_id": request["migration_id"], "status": status}
    )
    return _result(updated, status=status, code="MIGRATION_ABORTED" if aborted else "MIGRATION_COMPLETED")


def retire_service(state: dict[str, Any], request: dict[str, Any]) -> dict[str, Any]:
    """Remove active service state and retain only an auditable tombstone."""

    original = _clone(state)
    missing = _required(request, ("operation_id", "service_id", "approved_by", "evidence"))
    if missing:
        return _result(original, status="Rejected", code="INVALID_RETIREMENT", field=missing)
    service_id = request["service_id"]
    if service_id in original.get("tombstones", {}):
        return _result(original, status="Retired", code="RETIREMENT_REUSED", reused=True)

    updated = _clone(original)
    environment_ids = sorted(
        environment_id
        for environment_id, environment in updated.get("environments", {}).items()
        if environment.get("service_id") == service_id
    )
    operation_ids = sorted(
        operation_id
        for operation_id, operation in updated.get("operations", {}).items()
        if operation.get("service_id") == service_id
    )
    for environment_id in environment_ids:
        updated.get("environments", {}).pop(environment_id, None)
        updated.get("credentials", {}).pop(environment_id, None)
    for operation_id in operation_ids:
        updated.get("operations", {}).pop(operation_id, None)
    for key, entry in list(updated.get("idempotency", {}).items()):
        if entry.get("operation_id") in operation_ids:
            updated["idempotency"].pop(key, None)
    updated["break_glass"] = [
        item for item in updated.get("break_glass", []) if item.get("environment_id") not in environment_ids
    ]
    tombstone = {
        "service_id": service_id,
        "operation_id": request["operation_id"],
        "approved_by": request["approved_by"],
        "evidence": request["evidence"],
        "removed_environments": environment_ids,
        "removed_operations": operation_ids,
        "status": "Retired",
    }
    updated.setdefault("tombstones", {})[service_id] = tombstone
    updated.setdefault("audit_events", []).append({"event": "service.retired", **tombstone})
    return _result(updated, status="Retired", code="RETIREMENT_COMPLETE", reused=False)


def _redact(value: Any) -> Any:
    if isinstance(value, dict):
        result: dict[str, Any] = {}
        for key in sorted(value):
            lowered = str(key).casefold()
            if any(token in lowered for token in ("password", "secret_value", "private_key", "access_token")):
                result[key] = "[REDACTED]"
            else:
                result[key] = _redact(value[key])
        return result
    if isinstance(value, list):
        return [_redact(item) for item in value]
    return _clone(value)


def snapshot(state: dict[str, Any]) -> dict[str, Any]:
    """Return a deterministic deep copy without secret material."""

    value = _redact(state)
    return json.loads(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
