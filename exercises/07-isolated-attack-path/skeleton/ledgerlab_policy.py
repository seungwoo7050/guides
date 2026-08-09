"""Intentionally incomplete starting point for the isolated security lab."""

from __future__ import annotations


POLICY_VERSION = "skeleton-v1"


def _event(request: dict, decision: str, reason: str) -> dict:
    return {
        "event_id": request.get("event_id", "event-missing"),
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
    actor = state.get("actors", {}).get(request.get("actor_id"))
    report = state.get("reports", {}).get(request.get("resource_id"))
    if actor is None or report is None or report.get("status") != "completed":
        return _result(request, "deny", "missing actor, report, or completed state")
    # Intentionally incomplete: owner and tenant are not compared.
    return _result(request, "allow", "authenticated actor and completed report")


def authorize_object(state: dict, request: dict) -> dict:
    credential = state.get("credentials", {}).get(request.get("credential_id"))
    if credential is None:
        return _result(request, "deny", "credential not found")
    # Intentionally incomplete: job, exact prefix, expiry, and revocation are not enforced.
    if not str(request.get("resource_id", "")).startswith("synthetic/tenant-42/"):
        return _result(request, "deny", "outside synthetic tenant")
    return _result(request, "allow", "broad worker credential")


def detect(events: list[dict]) -> list[dict]:
    # Intentionally incomplete: no cross-scope analytic exists.
    return []
