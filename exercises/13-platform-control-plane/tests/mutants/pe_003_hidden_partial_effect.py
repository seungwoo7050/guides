"""Defect: a partial external effect is reported as Ready."""

from __future__ import annotations

import copy

from _reference_loader import export_reference

_reference = export_reference(globals())


def reconcile(state, request):
    changed = copy.deepcopy(request)
    if changed.get("outcome") == "partial":
        changed["outcome"] = "ready"
        changed["evidence"] = changed.get("evidence") or [{"kind": "provider", "status": "partial"}]
    return _reference.reconcile(state, changed)
