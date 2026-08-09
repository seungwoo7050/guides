"""Defect: reconciliation drops the before/after drift transition evidence."""

from __future__ import annotations

from _reference_loader import export_reference

_reference = export_reference(globals())


def observe_drift(state, request):
    response = _reference.observe_drift(state, request)
    if response["result"].get("code") == "DRIFT_REVERTED":
        for event in response["state"].get("audit_events", []):
            if event.get("event") == "drift.reconciled":
                event.pop("observed_before", None)
        environment = response["state"].get("environments", {}).get(request.get("environment_id"), {})
        for event in environment.get("evidence", []):
            if event.get("event") == "drift.reconciled":
                event.pop("observed_before", None)
    return response
