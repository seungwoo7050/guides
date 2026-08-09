from __future__ import annotations


def validate_records(records: list[dict]) -> dict:
    return {"valid": list(records), "quarantine": []}


def reconcile(source_records: list[dict], target_records: list[dict]) -> dict:
    return {
        "source_count": len(source_records),
        "target_count": len(target_records),
        "source_net_by_currency": {},
        "target_net_by_currency": {},
        "missing_keys": [],
        "extra_keys": [],
        "mismatched_keys": [],
        "source_quarantine": [],
        "target_quarantine": [],
        "matched": len(source_records) == len(target_records),
    }
