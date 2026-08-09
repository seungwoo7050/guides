"""One reference implementation of the public security behavior contract."""

from __future__ import annotations

from datetime import datetime, timezone


POLICY_VERSION = "reference-v1"


def _parse_time(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def _event(request: dict, decision: str, reason: str) -> dict:
    return {
        "event_id": request.get("event_id"),
        "event_type": "authorization.decision",
        "actor_id": request.get("actor_id"),
        "effective_actor_id": request.get("effective_actor_id"),
        "credential_id": request.get("credential_id"),
        "tenant_id": request.get("tenant_id"),
        "job_id": request.get("job_id"),
        "action": request.get("action"),
        "resource_id": request.get("resource_id"),
        "decision": decision,
        "reason": reason,
        "correlation_id": request.get("correlation_id"),
        "policy_version": POLICY_VERSION,
    }


def _result(request: dict, decision: str, reason: str) -> dict:
    return {"decision": decision, "reason": reason, "event": _event(request, decision, reason)}


def authorize_report(state: dict, request: dict) -> dict:
    if not state.get("policy_available", False):
        return _result(request, "deny", "policy context unavailable")
    if request.get("action") != "report.read":
        return _result(request, "deny", "action context missing or invalid")
    if not request.get("actor_id") or request.get("effective_actor_id") != request.get("actor_id"):
        return _result(request, "deny", "actor context missing or delegated")
    actor = state.get("actors", {}).get(request.get("actor_id"))
    report = state.get("reports", {}).get(request.get("resource_id"))
    if actor is None or report is None:
        return _result(request, "deny", "actor or report not found")
    request_tenant = request.get("tenant_id")
    if not request_tenant or actor.get("tenant_id") != request_tenant:
        return _result(request, "deny", "actor tenant mismatch")
    if report.get("tenant_id") != request_tenant or report.get("owner_id") != request.get("actor_id"):
        return _result(request, "deny", "report scope mismatch")
    if report.get("status") != "completed":
        return _result(request, "deny", "report is not completed")
    return _result(request, "allow", "owner and tenant policy satisfied")


def authorize_object(state: dict, request: dict) -> dict:
    if not state.get("policy_available", False):
        return _result(request, "deny", "policy context unavailable")
    if request.get("action") != "object.read":
        return _result(request, "deny", "action context missing or invalid")
    credential = state.get("credentials", {}).get(request.get("credential_id"))
    if credential is None:
        return _result(request, "deny", "credential not found")
    required = ("tenant_id", "job_id", "object_prefix", "expires_at")
    if any(not credential.get(field) for field in required):
        return _result(request, "deny", "credential scope incomplete")
    if credential.get("revoked"):
        return _result(request, "deny", "credential revoked")
    if not request.get("actor_id") or request.get("effective_actor_id") != request.get("actor_id"):
        return _result(request, "deny", "actor context missing or delegated")
    if request.get("actor_id") != credential.get("service_id"):
        return _result(request, "deny", "credential service identity mismatch")
    if _parse_time(credential["expires_at"]) <= _parse_time(state["now"]):
        return _result(request, "deny", "credential expired")
    if request.get("tenant_id") != credential.get("tenant_id"):
        return _result(request, "deny", "tenant scope mismatch")
    if request.get("job_id") != credential.get("job_id"):
        return _result(request, "deny", "job scope mismatch")
    resource = str(request.get("resource_id", ""))
    if not resource.startswith(credential["object_prefix"]):
        return _result(request, "deny", "object prefix mismatch")
    return _result(request, "allow", "credential scope satisfied")


def detect(events: list[dict]) -> list[dict]:
    unique: dict[str, dict] = {}
    for event in events:
        event_id = event.get("event_id")
        if event_id and event_id not in unique:
            unique[event_id] = event
    groups: dict[str, list[dict]] = {}
    for event in unique.values():
        suspicious = (
            event.get("event_type") == "authorization.decision"
            and event.get("decision") == "deny"
            and any(term in str(event.get("reason", "")) for term in ("scope mismatch", "policy context unavailable"))
        )
        correlation_id = event.get("correlation_id")
        if suspicious and isinstance(correlation_id, str) and correlation_id:
            groups.setdefault(correlation_id, []).append(event)

    alerts: list[dict] = []
    for correlation_id, suspicious in sorted(groups.items()):
        suspicious.sort(key=lambda event: str(event.get("event_id")))
        alerts.append({
            "alert_id": f"DET-CROSS-SCOPE:{correlation_id}",
            "correlation_id": correlation_id,
            "actor_ids": sorted({str(event.get("actor_id")) for event in suspicious if event.get("actor_id")}),
            "effective_actor_ids": sorted({str(event.get("effective_actor_id")) for event in suspicious if event.get("effective_actor_id")}),
            "credential_ids": sorted({str(event.get("credential_id")) for event in suspicious if event.get("credential_id")}),
            "evidence_event_ids": [event["event_id"] for event in suspicious],
        })
    return alerts
