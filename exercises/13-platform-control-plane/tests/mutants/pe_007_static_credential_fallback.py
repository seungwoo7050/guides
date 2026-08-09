"""Defect: static credentials are silently converted to an accepted request."""

from __future__ import annotations

import copy

from _reference_loader import export_reference

_reference = export_reference(globals())


def request_environment(state, request):
    changed = copy.deepcopy(request)
    if changed.get("credential_mode") == "static-fallback":
        changed["credential_mode"] = "workload-identity"
    return _reference.request_environment(state, changed)
