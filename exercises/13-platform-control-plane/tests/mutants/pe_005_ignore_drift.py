"""Defect: live drift is declared in sync without reconciliation."""

from __future__ import annotations

import copy

from _reference_loader import export_reference

_reference = export_reference(globals())


def observe_drift(state, request):
    return {"state": copy.deepcopy(state), "result": {"status": "InSync", "code": "NO_DRIFT"}}
