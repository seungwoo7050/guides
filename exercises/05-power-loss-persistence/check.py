#!/usr/bin/env python3
"""Black-box checker for the power-loss-safe persistence exercise."""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType
from typing import Any, Callable


ROOT = Path(__file__).resolve().parent
FIXTURES = ROOT / "fixtures"
REQUIRED = (
    "FlashViolation",
    "PowerLoss",
    "NorFlash",
    "recover",
    "seed_image",
    "operation_lengths",
    "cut_points",
    "apply_update",
)


class InterfaceError(RuntimeError):
    pass


def load_submission(path: Path) -> ModuleType:
    unresolved = path
    if unresolved.is_dir():
        unresolved = unresolved / "persistence.py"
    if not unresolved.is_file() or unresolved.is_symlink():
        raise InterfaceError(f"submission file is missing or unsafe: {unresolved}")
    module_path = unresolved.resolve()
    spec = importlib.util.spec_from_file_location(
        f"persistence_submission_{abs(hash(module_path))}", module_path
    )
    if spec is None or spec.loader is None:
        raise InterfaceError(f"cannot load submission: {module_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    try:
        spec.loader.exec_module(module)
    except Exception as exc:  # import errors are an invalid public interface
        raise InterfaceError(f"submission import failed: {exc}") from exc
    missing = [name for name in REQUIRED if not hasattr(module, name)]
    if missing:
        raise InterfaceError("missing public names: " + ", ".join(missing))
    return module


def clear_one_bit(image: bytes, start: int, token: bytes) -> bytes:
    mutable = bytearray(image)
    offset = image.find(token, start)
    if offset < 0:
        raise AssertionError(f"cannot locate corruption token {token!r}")
    value = mutable[offset]
    mutable[offset] = value & (value - 1) if value else 1
    return bytes(mutable)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def test_nor_physics(module: ModuleType) -> None:
    flash = module.NorFlash()
    flash.program(0, b"\xf0\x0f")
    require(flash.snapshot()[:2] == b"\xf0\x0f", "program did not clear requested bits")
    try:
        flash.program(0, b"\xff")
    except module.FlashViolation:
        pass
    else:
        raise AssertionError("0-to-1 programming was accepted")

    torn = module.NorFlash()
    try:
        torn.program(0, b"\x00\x00\x00\x00", cut_after=2)
    except module.PowerLoss:
        pass
    else:
        raise AssertionError("program cut did not stop the operation")
    require(
        torn.snapshot()[:4] == b"\x00\x00\xff\xff",
        "program cut did not preserve the byte boundary",
    )


def test_exhaustive_cuts(module: ModuleType) -> None:
    fixture = json.loads((FIXTURES / "exhaustive-cuts.json").read_text(encoding="utf-8"))
    old = fixture["old_payload"].encode()
    new = fixture["new_payload"].encode()
    old_sequence = fixture["old_sequence"]
    new_sequence = fixture["new_sequence"]
    schema = fixture["schema"]
    image = module.seed_image(old, old_sequence, schema)
    baseline = module.recover(image)
    require(baseline["status"] == "ok" and baseline["payload"] == old, "seed is not recoverable")

    lengths = module.operation_lengths(new, new_sequence, schema)
    expected_operations = {
        "erase-inactive",
        "program-body",
        "program-commit",
        "obsolete-old",
    }
    require(set(lengths) == expected_operations, "operation plan is incomplete")
    points = module.cut_points(new, new_sequence, schema)
    normalized = {(point["operation"], point["after"]) for point in points}
    require(len(normalized) == len(points), "cut points contain duplicates")
    require(
        len(points) == sum(length + 1 for length in lengths.values()),
        "not every before/byte/after boundary is enumerated",
    )

    allowed = {old, new}
    for point in points:
        cut_image = module.apply_update(
            image,
            new,
            new_sequence,
            schema,
            cut=point,
        )
        result = module.recover(cut_image)
        require(result["status"] == "ok", f"no complete record after cut {point}")
        require(result["payload"] in allowed, f"partial payload selected after cut {point}")

    before_commit = module.apply_update(
        image,
        new,
        new_sequence,
        schema,
        cut={"operation": "program-commit", "after": 0},
    )
    require(
        module.recover(before_commit)["payload"] == old,
        "new record became visible before commit",
    )
    after_commit = module.apply_update(
        image,
        new,
        new_sequence,
        schema,
        cut={"operation": "program-commit", "after": lengths["program-commit"]},
    )
    require(
        module.recover(after_commit)["payload"] == new,
        "committed new record was not selected",
    )


def test_final_and_corruption(module: ModuleType) -> None:
    fixture = json.loads((FIXTURES / "corruption.json").read_text(encoding="utf-8"))
    require(
        [case.get("name") for case in fixture.get("cases", [])]
        == ["payload-bit", "magic-bit", "both-records"],
        "corruption fixture contract is incomplete",
    )
    old = b"old-complete"
    new = b"new-complete"
    image = module.seed_image(old, 12)
    both = module.apply_update(
        image,
        new,
        13,
        cut={"operation": "obsolete-old", "after": 0},
    )
    require(module.recover(both)["payload"] == new, "newer committed record was not selected")

    corrupted_new = clear_one_bit(both, 128, new)
    recovered = module.recover(corrupted_new)
    require(recovered["payload"] == old, "checksum corruption did not fall back to old record")

    corrupted_header = bytearray(both)
    corrupted_header[128] &= 0xFE
    require(
        module.recover(bytes(corrupted_header))["payload"] == old,
        "header corruption did not fall back to old record",
    )

    corrupted_both = clear_one_bit(corrupted_new, 0, old)
    require(
        module.recover(corrupted_both)["status"] == "recovery",
        "two corrupt records did not enter recovery",
    )

    final = module.apply_update(image, new, 13)
    result = module.recover(final)
    require(result["payload"] == new, "completed update did not select new record")
    require(result["slots"]["A"]["status"] == "obsolete", "old record was not obsoleted last")


def test_wrap_tie_and_schema(module: ModuleType) -> None:
    fixture = json.loads((FIXTURES / "wrap-and-schema.json").read_text(encoding="utf-8"))

    def retain_both(old_sequence: int, new_sequence: int) -> dict[str, Any]:
        image = module.seed_image(b"old", old_sequence)
        updated = module.apply_update(
            image,
            b"new",
            new_sequence,
            cut={"operation": "obsolete-old", "after": 0},
        )
        return module.recover(updated)

    expected_payloads = {"new": b"new", "old": b"old", "old-slot-a": b"old"}
    for case in fixture["wrap_cases"]:
        result = retain_both(case["old_sequence"], case["new_sequence"])
        require(
            result["payload"] == expected_payloads[case["expected"]],
            f"wrap case failed: {case}",
        )
        if case["expected"] == "old-slot-a":
            require(result["selected_slot"] == "A", "equal sequence tie is not deterministic")

    future_schema = fixture["unsupported_schema"]
    supported_schemas = tuple(fixture["supported_schemas"])
    future = module.seed_image(b"future", 1, schema=future_schema, stale_inactive=False)
    unsupported = module.recover(future, supported_schemas=supported_schemas)
    require(unsupported["status"] == "recovery", "unsupported schema was decoded")
    require(
        unsupported["slots"]["A"]["status"] == "unsupported-schema",
        "unsupported schema was not classified",
    )
    require(
        module.recover(future, supported_schemas=supported_schemas + (future_schema,))["payload"]
        == b"future",
        "explicitly supported schema was not recovered",
    )


TESTS: tuple[tuple[str, Callable[[ModuleType], None]], ...] = (
    ("NOR physical constraints", test_nor_physics),
    ("exhaustive byte-boundary cuts", test_exhaustive_cuts),
    ("corruption and final ordering", test_final_and_corruption),
    ("sequence wrap, tie, and schema", test_wrap_tie_and_schema),
)


def emit(report: dict[str, Any], as_json: bool) -> None:
    if as_json:
        print(json.dumps(report, ensure_ascii=False, sort_keys=True))
        return
    for result in report.get("tests", []):
        label = "PASS" if result["passed"] else "FAIL"
        detail = "" if result["passed"] else f": {result['detail']}"
        print(f"[{label}] {result['name']}{detail}")
    print(
        f"RESULT {report['status']} "
        f"passed={report.get('passed', 0)} total={report.get('total', 0)}"
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--submission", required=True, type=Path)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    try:
        module = load_submission(args.submission)
    except InterfaceError as exc:
        report = {"status": "INTERFACE_ERROR", "detail": str(exc), "passed": 0, "total": 0, "tests": []}
        emit(report, args.json)
        return 2

    results: list[dict[str, Any]] = []
    for name, test in TESTS:
        try:
            test(module)
        except Exception as exc:
            results.append({"name": name, "passed": False, "detail": f"{type(exc).__name__}: {exc}"})
        else:
            results.append({"name": name, "passed": True, "detail": ""})
    passed = sum(1 for result in results if result["passed"])
    report = {
        "status": "PASS" if passed == len(results) else "FAIL",
        "passed": passed,
        "total": len(results),
        "tests": results,
    }
    emit(report, args.json)
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
