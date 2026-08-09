"""Intentionally incomplete learner starter for the platform control plane."""

from __future__ import annotations

import copy
from typing import Any


def _result(state: dict[str, Any], **result: Any) -> dict[str, Any]:
    return {"state": state, "result": result}


def request_environment(state: dict[str, Any], request: dict[str, Any]) -> dict[str, Any]:
    updated = copy.deepcopy(state)
    operation_id = request.get("operation_id", "unknown")
    environment_id = request.get("environment_id", operation_id)
    updated.setdefault("environments", {})[environment_id] = {
        "environment_id": environment_id,
        "tenant_id": request.get("tenant_id"),
        "service_id": request.get("service_id"),
        "artifact_digest": request.get("artifact_digest"),
        "observed_artifact_digest": None,
        "profile_version": request.get("profile_version"),
        "condition": "Progressing",
        "external_effects": [],
        "cleanup_required": False,
        "evidence": [],
    }
    updated.setdefault("operations", {})[operation_id] = {
        "operation_id": operation_id,
        "tenant_id": request.get("tenant_id"),
        "service_id": request.get("service_id"),
        "environment_id": environment_id,
        "status": "Accepted",
    }
    updated.setdefault("credentials", {})[environment_id] = {
        "mode": request.get("credential_mode"),
        "static_secret": request.get("credential_mode") != "workload-identity",
    }
    return _result(updated, status="Accepted", code="NEW_OPERATION", operation_id=operation_id, reused=False)


def reconcile(state: dict[str, Any], request: dict[str, Any]) -> dict[str, Any]:
    updated = copy.deepcopy(state)
    operation = updated.get("operations", {}).get(request.get("operation_id"))
    if not operation:
        return _result(updated, status="Rejected", code="UNKNOWN_OPERATION")
    environment = updated["environments"][operation["environment_id"]]
    environment["condition"] = "Ready"
    environment["observed_artifact_digest"] = environment.get("artifact_digest")
    operation["status"] = "Ready"
    return _result(updated, status="Ready", code="READY")


def observe_drift(state: dict[str, Any], request: dict[str, Any]) -> dict[str, Any]:
    return _result(copy.deepcopy(state), status="InSync", code="NO_DRIFT")


def request_migration(state: dict[str, Any], request: dict[str, Any]) -> dict[str, Any]:
    updated = copy.deepcopy(state)
    records = [
        {"name": wave.get("name"), "targets": copy.deepcopy(wave.get("targets", [])), "status": "Completed"}
        for wave in request.get("waves", [])
    ]
    updated.setdefault("migrations", {})[request.get("migration_id", "unknown")] = {
        "migration_id": request.get("migration_id"),
        "status": "Completed",
        "waves": records,
    }
    return _result(updated, status="Completed", code="MIGRATION_COMPLETED")


def retire_service(state: dict[str, Any], request: dict[str, Any]) -> dict[str, Any]:
    updated = copy.deepcopy(state)
    service_id = request.get("service_id")
    updated.setdefault("tombstones", {})[service_id] = {"service_id": service_id, "status": "Retired"}
    return _result(updated, status="Retired", code="RETIREMENT_COMPLETE", reused=False)


def snapshot(state: dict[str, Any]) -> dict[str, Any]:
    return state
