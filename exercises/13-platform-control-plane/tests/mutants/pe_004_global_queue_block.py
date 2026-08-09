"""Defect: one progressing tenant blocks every tenant queue."""

from __future__ import annotations

import copy

from _reference_loader import export_reference

_reference = export_reference(globals())


def request_environment(state, request):
    if any(item.get("condition") == "Progressing" for item in state.get("environments", {}).values()):
        return {"state": copy.deepcopy(state), "result": {"status": "Rejected", "code": "GLOBAL_QUEUE_BUSY"}}
    return _reference.request_environment(state, request)
