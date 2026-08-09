"""Defect: a bounded exception does not retain its decision reason."""

from __future__ import annotations

from _reference_loader import export_reference

_reference = export_reference(globals())


def observe_drift(state, request):
    response = _reference.observe_drift(state, request)
    if response["result"].get("code") == "BOUNDED_BREAK_GLASS":
        response["state"]["break_glass"][-1].pop("reason", None)
    return response
