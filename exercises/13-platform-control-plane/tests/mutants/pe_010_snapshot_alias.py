"""Defect: snapshot aliases internal state and exposes secret material."""

from __future__ import annotations

from _reference_loader import export_reference

_reference = export_reference(globals())


def snapshot(state):
    return state
