"""Defect: retirement leaves a break-glass exception active."""

from __future__ import annotations

import copy

from _reference_loader import export_reference

_reference = export_reference(globals())


def retire_service(state, request):
    response = _reference.retire_service(state, request)
    retired_environments = set(response["state"].get("tombstones", {}).get(request.get("service_id"), {}).get("removed_environments", []))
    leaked = [
        copy.deepcopy(item)
        for item in state.get("break_glass", [])
        if item.get("environment_id") in retired_environments
    ]
    response["state"].setdefault("break_glass", []).extend(leaked)
    return response
