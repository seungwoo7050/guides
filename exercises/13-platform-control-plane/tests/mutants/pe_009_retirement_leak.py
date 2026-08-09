"""Defect: retirement leaves one environment and credential active."""

from __future__ import annotations

import copy

from _reference_loader import export_reference

_reference = export_reference(globals())


def retire_service(state, request):
    result = _reference.retire_service(state, request)
    leaked = next(
        ((key, value) for key, value in state.get("environments", {}).items() if value.get("service_id") == request.get("service_id")),
        None,
    )
    if leaked is not None:
        key, value = leaked
        result["state"].setdefault("environments", {})[key] = copy.deepcopy(value)
        if key in state.get("credentials", {}):
            result["state"].setdefault("credentials", {})[key] = copy.deepcopy(state["credentials"][key])
    return result
