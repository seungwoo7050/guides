from __future__ import annotations

import json
import re
from collections import defaultdict

CURRENCY = re.compile(r"^[A-Z]{3}$")
ALLOWED_STATUS = {"SETTLED", "REFUNDED"}


def _copy(value: object):
    return json.loads(json.dumps(value, ensure_ascii=False, allow_nan=False))


def _canonical(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def validate_records(records: list[dict]) -> dict:
    if not isinstance(records, list):
        raise ValueError("records must be a list")
    invalid: list[dict] = []
    candidates: dict[str, list[dict]] = defaultdict(list)
    for raw in records:
        if not isinstance(raw, dict):
            raise ValueError("record must be an object")
        record = _copy(raw)
        record_id = record.get("id")
        rules: list[str] = []
        if not isinstance(record_id, str) or not record_id:
            rules.append("id_required")
        currency = record.get("currency")
        if not isinstance(currency, str) or CURRENCY.fullmatch(currency) is None:
            rules.append("currency_format")
        amount = record.get("amount_minor")
        if not isinstance(amount, int) or isinstance(amount, bool) or amount < 0:
            rules.append("amount_non_negative_integer")
        if record.get("status") not in ALLOWED_STATUS:
            rules.append("status_allowed")
        if rules:
            invalid.append({"id": record_id, "rules": rules, "record": record})
        else:
            candidates[record_id].append(record)

    valid: list[dict] = []
    conflicts: list[dict] = []
    for record_id, group in candidates.items():
        variants = {_canonical(record) for record in group}
        if len(variants) == 1:
            valid.append(min(group, key=_canonical))
            continue
        conflicts.extend(
            {"id": record_id, "rules": ["duplicate_id_conflict"], "record": record}
            for record in group
        )

    quarantine = invalid + conflicts
    quarantine.sort(key=lambda item: (str(item["id"]), tuple(item["rules"]), _canonical(item["record"])))
    valid.sort(key=lambda record: record["id"])
    return {"valid": valid, "quarantine": quarantine}


def _net_by_currency(records: list[dict]) -> dict[str, int]:
    totals: dict[str, int] = defaultdict(int)
    for record in records:
        sign = 1 if record["status"] == "SETTLED" else -1
        totals[record["currency"]] += sign * record["amount_minor"]
    return {currency: totals[currency] for currency in sorted(totals)}


def reconcile(source_records: list[dict], target_records: list[dict]) -> dict:
    source = validate_records(source_records)
    target = validate_records(target_records)
    source_by_id = {record["id"]: record for record in source["valid"]}
    target_by_id = {record["id"]: record for record in target["valid"]}
    source_keys = set(source_by_id)
    target_keys = set(target_by_id)
    missing = sorted(source_keys - target_keys)
    extra = sorted(target_keys - source_keys)
    mismatched = sorted(
        key
        for key in source_keys & target_keys
        if _canonical(source_by_id[key]) != _canonical(target_by_id[key])
    )
    source_net = _net_by_currency(source["valid"])
    target_net = _net_by_currency(target["valid"])
    matched = (
        not source["quarantine"]
        and not target["quarantine"]
        and not missing
        and not extra
        and not mismatched
        and source_net == target_net
    )
    return {
        "source_count": len(source_by_id),
        "target_count": len(target_by_id),
        "source_net_by_currency": source_net,
        "target_net_by_currency": target_net,
        "missing_keys": missing,
        "extra_keys": extra,
        "mismatched_keys": mismatched,
        "source_quarantine": source["quarantine"],
        "target_quarantine": target["quarantine"],
        "matched": matched,
    }
