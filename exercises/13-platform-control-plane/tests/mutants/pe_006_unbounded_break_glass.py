"""Defect: emergency changes gain invented owner and expiry."""

from __future__ import annotations

import copy

from _reference_loader import export_reference

_reference = export_reference(globals())


def observe_drift(state, request):
    changed = copy.deepcopy(request)
    if changed.get("break_glass") is True:
        changed.setdefault("approved_by", "implicit-admin")
        changed.setdefault("expires_at", "2099-01-01T00:00:00Z")
        changed.setdefault("reason", "implicit")
        changed.setdefault("evidence", "invented")
    return _reference.observe_drift(state, changed)
