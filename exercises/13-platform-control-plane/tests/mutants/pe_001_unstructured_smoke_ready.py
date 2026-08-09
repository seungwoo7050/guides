"""Defect: incomplete smoke evidence is embellished by the controller."""

from __future__ import annotations

import copy

from _reference_loader import export_reference

_reference = export_reference(globals())


def reconcile(state, request):
    changed = copy.deepcopy(request)
    if changed.get("outcome") == "ready":
        operation = state.get("operations", {}).get(changed.get("operation_id"), {})
        environment = state.get("environments", {}).get(operation.get("environment_id"), {})
        generation = environment.get("generation")
        evidence = changed.get("evidence")
        if isinstance(evidence, list):
            for item in evidence:
                if isinstance(item, dict) and item.get("kind") == "external-smoke":
                    item.setdefault("revision", "invented-revision")
                    item.setdefault("observed_generation", generation)
    return _reference.reconcile(state, changed)
