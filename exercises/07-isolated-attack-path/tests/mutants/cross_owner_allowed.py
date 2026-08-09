from __future__ import annotations

from _reference_loader import load_reference

_reference = load_reference()
authorize_object = _reference.authorize_object
detect = _reference.detect


def authorize_report(state: dict, request: dict) -> dict:
    result = _reference.authorize_report(state, request)
    if request.get("actor_id") == "user-b" and request.get("resource_id") == "report-a":
        result["decision"] = "allow"
        result["reason"] = "mutant skips resource owner"
        result["event"]["decision"] = "allow"
        result["event"]["reason"] = result["reason"]
    return result
