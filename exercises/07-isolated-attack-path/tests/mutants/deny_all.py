from __future__ import annotations

from _reference_loader import load_reference

_reference = load_reference()
detect = _reference.detect


def _deny(request: dict) -> dict:
    result = _reference._result(request, "deny", "mutant denies every request")
    return result


def authorize_report(state: dict, request: dict) -> dict:
    return _deny(request)


def authorize_object(state: dict, request: dict) -> dict:
    return _deny(request)
