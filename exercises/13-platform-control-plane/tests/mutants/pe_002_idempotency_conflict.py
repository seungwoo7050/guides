"""Defect: changed payload silently creates a second operation."""

from __future__ import annotations

import copy

from _reference_loader import export_reference

_reference = export_reference(globals())


def request_environment(state, request):
    result = _reference.request_environment(state, request)
    if result["result"].get("code") == "IDEMPOTENCY_CONFLICT":
        changed = copy.deepcopy(request)
        changed["idempotency_key"] = request["idempotency_key"] + "-alias"
        changed["operation_id"] = request["operation_id"] + "-alias"
        changed["environment_id"] = request["environment_id"] + "-alias"
        return _reference.request_environment(state, changed)
    return result
