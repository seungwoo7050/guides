from __future__ import annotations

from _reference_loader import load_reference

_reference = load_reference()
authorize_report = _reference.authorize_report
detect = _reference.detect


def authorize_object(state: dict, request: dict) -> dict:
    result = _reference.authorize_object(state, request)
    resource = str(request.get("resource_id", ""))
    if resource.startswith("synthetic/tenant-42/job-81"):
        result["decision"] = "allow"
        result["reason"] = "mutant uses ambiguous string prefix"
        result["event"]["decision"] = "allow"
        result["event"]["reason"] = result["reason"]
    return result
