"""Defect: migration ignores a failed wave and promotes every target."""

from __future__ import annotations

import copy

from _reference_loader import export_reference

_reference = export_reference(globals())


def request_migration(state, request):
    changed = copy.deepcopy(request)
    changed.pop("fail_wave", None)
    return _reference.request_migration(state, changed)
