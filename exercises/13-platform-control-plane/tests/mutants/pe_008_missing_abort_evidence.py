"""Defect: an aborted migration loses the evidence that caused the decision."""

from __future__ import annotations

from _reference_loader import export_reference

_reference = export_reference(globals())


def request_migration(state, request):
    response = _reference.request_migration(state, request)
    if response["result"].get("code") == "MIGRATION_ABORTED":
        response["state"]["migrations"][request["migration_id"]]["abort_evidence"] = None
    return response
