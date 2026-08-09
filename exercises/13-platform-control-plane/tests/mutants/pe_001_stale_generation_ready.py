"""Defect: stale observedGeneration is silently promoted to the desired generation."""

from __future__ import annotations

import copy

from _reference_loader import export_reference

_reference = export_reference(globals())


def reconcile(state, request):
    changed = copy.deepcopy(request)
    if changed.get("outcome") == "ready":
        operation = state.get("operations", {}).get(changed.get("operation_id"), {})
        environment = state.get("environments", {}).get(operation.get("environment_id"), {})
        changed["observed_generation"] = environment.get("generation")
        for evidence in changed.get("evidence", []):
            if isinstance(evidence, dict):
                evidence["observed_generation"] = environment.get("generation")
    return _reference.reconcile(state, changed)
