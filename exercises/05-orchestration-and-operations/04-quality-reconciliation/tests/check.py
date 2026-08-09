#!/usr/bin/env python3
from __future__ import annotations

import copy
import importlib.util
import itertools
import sys
from pathlib import Path

CODE = "GUIDE_SEMANTIC:quality-reconciliation"
CONTRACT = "GUIDE_CONTRACT:quality-reconciliation"


def load(path: Path):
    spec = importlib.util.spec_from_file_location("learner_solution", path / "solution.py")
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load solution")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    if not callable(getattr(module, "validate_records", None)) or not callable(
        getattr(module, "reconcile", None)
    ):
        raise TypeError("validate_records and reconcile are required")
    return module


def record(record_id: str, currency: str = "KRW", amount: int = 100, status: str = "SETTLED") -> dict:
    return {"id": record_id, "currency": currency, "amount_minor": amount, "status": status}


def check(solution) -> None:
    rows = [record("ok"), {"id": "", "currency": "krw", "amount_minor": -1, "status": "BAD"}]
    original = copy.deepcopy(rows)
    validated = solution.validate_records(rows)
    assert rows == original, "validation must not mutate input"
    assert validated["valid"] == [record("ok")], "valid records must be preserved exactly"
    assert validated["quarantine"][0]["rules"] == [
        "id_required", "currency_format", "amount_non_negative_integer", "status_allowed"
    ], "hard-rule evidence is incomplete"
    duplicate = record("dup")
    assert solution.validate_records([duplicate, copy.deepcopy(duplicate)])["valid"] == [duplicate], (
        "identical duplicate records must collapse to one valid record"
    )

    a = record("conflict", amount=10)
    b = record("conflict", amount=20)
    expected = None
    for names in set(itertools.permutations(("a", "b", "a"))):
        candidate = [a if name == "a" else b for name in names]
        actual = solution.validate_records(candidate)
        if expected is None:
            expected = actual
        assert actual == expected, "conflict quarantine must be input-order independent"
        assert actual["valid"] == [], "sticky conflict ID must never re-enter valid output"
        assert len(actual["quarantine"]) == 3, "every conflicting input record needs evidence"
        assert all(item["rules"] == ["duplicate_id_conflict"] for item in actual["quarantine"]), (
            "every conflicting duplicate must carry only duplicate_id_conflict evidence"
        )

    source = [record("a"), record("b")]
    target = [record("a"), record("c")]
    reconciled = solution.reconcile(source, target)
    assert reconciled["source_count"] == reconciled["target_count"] == 2, (
        "reconciliation counts must include both valid source and target records"
    )
    assert reconciled["missing_keys"] == ["b"] and reconciled["extra_keys"] == ["c"], (
        "reconciliation must report exact sorted missing and extra keys"
    )
    assert reconciled["matched"] is False, "equal counts must not hide key differences"

    mismatched = solution.reconcile([record("same", "KRW", 100)], [record("same", "USD", 100)])
    assert mismatched["mismatched_keys"] == ["same"], (
        "same key with different currency must be reported as mismatched"
    )
    assert mismatched["source_net_by_currency"] == {"KRW": 100}, (
        "source net totals must retain their currency dimension"
    )
    assert mismatched["target_net_by_currency"] == {"USD": 100}, (
        "target net totals must retain their currency dimension"
    )
    assert mismatched["matched"] is False, "same scalar amount in another currency must not match"

    mixed = [record("k", "KRW", 100), record("r", "KRW", 40, "REFUNDED"), record("u", "USD", 7)]
    exact = solution.reconcile(mixed, copy.deepcopy(mixed))
    assert exact["source_net_by_currency"] == {"KRW": 60, "USD": 7}, (
        "refunds must subtract from per-currency source net totals"
    )
    assert exact["matched"] is True, "identical valid source and target datasets must match"

    quarantine_match = solution.reconcile([a, b, a], [])
    assert quarantine_match["source_count"] == quarantine_match["target_count"] == 0, (
        "conflicting source records must be excluded from valid reconciliation counts"
    )
    assert quarantine_match["matched"] is False, "quarantine must prevent a false empty-to-empty match"

    boolean_amount = record("bool")
    boolean_amount["amount_minor"] = True
    assert solution.validate_records([boolean_amount])["quarantine"][0]["rules"] == [
        "amount_non_negative_integer"
    ], "boolean amounts must be quarantined as non-integers"


def main() -> int:
    try:
        solution = load(Path(sys.argv[1]).resolve())
        check(solution)
    except AssertionError as exc:
        print(f"{CODE}: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"{CONTRACT}: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2
    print("OK quality-reconciliation")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
