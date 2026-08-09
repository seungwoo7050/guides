from __future__ import annotations

import re

CURRENCY = re.compile(r"^[A-Z]{3}$")


def validate_records(records: list[dict]) -> dict:
    valid = {}
    quarantine = []
    for record in records:
        rules = []
        record_id = record.get("id")
        if not isinstance(record_id, str) or not record_id:
            rules.append("id_required")
        if not isinstance(record.get("currency"), str) or not CURRENCY.fullmatch(record["currency"]):
            rules.append("currency_format")
        amount = record.get("amount_minor")
        if not isinstance(amount, int) or isinstance(amount, bool) or amount < 0:
            rules.append("amount_non_negative_integer")
        if record.get("status") not in {"SETTLED", "REFUNDED"}:
            rules.append("status_allowed")
        if rules:
            quarantine.append({"id": record_id, "rules": rules, "record": dict(record)})
            continue
        previous = valid.get(record_id)
        if previous is not None and previous != record:
            quarantine.append({"id": record_id, "rules": ["duplicate_id_conflict"], "record": dict(record)})
            valid.pop(record_id, None)
            continue
        valid[record_id] = dict(record)
    return {"valid": [valid[key] for key in sorted(valid)], "quarantine": quarantine}


def _net(records):
    totals = {}
    for record in records:
        totals[record["currency"]] = totals.get(record["currency"], 0) + (
            record["amount_minor"] if record["status"] == "SETTLED" else -record["amount_minor"]
        )
    return dict(sorted(totals.items()))


def reconcile(source_records: list[dict], target_records: list[dict]) -> dict:
    source = validate_records(source_records)
    target = validate_records(target_records)
    left = {record["id"]: record for record in source["valid"]}
    right = {record["id"]: record for record in target["valid"]}
    return {
        "source_count": len(left),
        "target_count": len(right),
        "source_net_by_currency": _net(source["valid"]),
        "target_net_by_currency": _net(target["valid"]),
        "missing_keys": sorted(set(left) - set(right)),
        "extra_keys": sorted(set(right) - set(left)),
        "mismatched_keys": [],
        "source_quarantine": source["quarantine"],
        "target_quarantine": target["quarantine"],
        "matched": len(left) == len(right) and set(left) == set(right) and _net(source["valid"]) == _net(target["valid"]),
    }
