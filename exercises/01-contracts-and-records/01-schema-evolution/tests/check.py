#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

CODE = "GUIDE_SEMANTIC:schema-evolution"
CONTRACT = "GUIDE_CONTRACT:schema-evolution"


def load(path: Path):
    spec = importlib.util.spec_from_file_location("learner_solution", path / "solution.py")
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load solution")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    if not callable(getattr(module, "reader_accepts", None)):
        raise TypeError("reader_accepts is required")
    return module


def check(solution) -> None:
    old = {
        "order_id": {"type": "string", "required": True},
        "amount": {"type": "int", "required": True},
    }
    optional = {**old, "channel": {"type": "string", "required": False, "default": None}}
    required = {**old, "country": {"type": "string", "required": True}}
    defaulted = {**old, "country": {"type": "string", "required": True, "default": "KR"}}
    widened = {"order_id": old["order_id"], "amount": {"type": "long", "required": True}}
    double = {"order_id": old["order_id"], "amount": {"type": "double", "required": True}}
    writer_optional = {"order_id": {"type": "string", "required": False}}
    reader_required = {"order_id": {"type": "string", "required": True}}
    reader_defaulted = {"order_id": {"type": "string", "required": True, "default": "unknown"}}

    assert solution.reader_accepts(old, optional) is True, "optional reader field must be compatible"
    assert solution.reader_accepts(old, required) is False, "new required field without default must fail"
    assert solution.reader_accepts(old, defaulted) is True, "reader default must cover an absent field"
    assert solution.reader_accepts(old, widened) is True, "int-to-long widening must pass"
    assert solution.reader_accepts(old, double) is True, "int-to-double widening must pass"
    assert solution.reader_accepts(widened, old) is False, "long-to-int narrowing must fail"
    assert solution.reader_accepts(optional, old) is True, "old reader may ignore a new writer field"
    assert solution.reader_accepts(writer_optional, reader_required) is False, (
        "optional writer field cannot satisfy a required reader field"
    )
    assert solution.reader_accepts(writer_optional, reader_defaulted) is True, (
        "reader default must cover an omitted writer field"
    )
    try:
        solution.reader_accepts({"x": {"type": "mystery"}}, {"x": {"type": "mystery"}})
    except ValueError:
        pass
    else:
        raise AssertionError("unsupported types must be rejected")


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
    print("OK schema-evolution")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
