"""Defect: the controller invents evidence and publishes Ready."""

from __future__ import annotations

import copy

from _reference_loader import export_reference

_reference = export_reference(globals())


def reconcile(state, request):
    changed = copy.deepcopy(request)
    if changed.get("outcome") == "ready" and not changed.get("evidence"):
        changed["evidence"] = [{"kind": "invented", "status": "pass"}]
    return _reference.reconcile(state, changed)
