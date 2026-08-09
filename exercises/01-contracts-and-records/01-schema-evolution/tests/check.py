#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

CODE = "GUIDE_SEMANTIC:schema-evolution"


def load(path: Path):
    spec = importlib.util.spec_from_file_location("learner_solution", path / "solution.py")
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load solution")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main() -> int:
    try:
        target = Path(sys.argv[1]).resolve()
        solution = load(target)
        old = {
            "order_id": {"type": "string", "required": True},
            "amount": {"type": "int", "required": True},
        }
        optional = {
            **old,
            "channel": {"type": "string", "required": False, "default": None},
        }
        required = {**old, "country": {"type": "string", "required": True}}
        widened = {
            "order_id": {"type": "string", "required": True},
            "amount": {"type": "long", "required": True},
        }
        assert solution.reader_accepts(old, optional) is True
        assert solution.reader_accepts(old, required) is False
        assert solution.reader_accepts(old, widened) is True
        assert solution.reader_accepts(widened, old) is False
        assert solution.reader_accepts(optional, old) is True
    except Exception as exc:
        print(f"{CODE}: {exc}", file=sys.stderr)
        return 1
    print("OK schema-evolution")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
