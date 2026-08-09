from __future__ import annotations

from _reference_loader import load_reference

_reference = load_reference()
authorize_report = _reference.authorize_report
authorize_object = _reference.authorize_object


def detect(events: list[dict]) -> list[dict]:
    return []
