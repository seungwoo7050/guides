#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys
from typing import Any

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def load_vm() -> Any:
    path = ROOT / "examples/bytecode-vm/vm.py"
    spec = importlib.util.spec_from_file_location("guide_bytecode_vm", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def main() -> int:
    vm = load_vm()
    target = json.loads((HERE / "reference/virtual-target.json").read_text(encoding="utf-8"))
    trace = json.loads((HERE / "reference/bytecode-trace.json").read_text(encoding="utf-8"))
    assert target["target"] == "mica-vm-json-v1"
    assert "not an OS sandbox" in target["trust_boundary"]
    program, constants = vm.compile_expression(trace["source_projection"])
    assert [list(instruction) for instruction in program] == trace["instructions"]
    assert [{"type": value.type, "value": value.value} for value in constants] == trace["constants"]
    assert vm.disassemble(program, constants) == trace["disassembly"]
    interpreted = vm.evaluate_expression(trace["source_projection"])
    executed = vm.execute(program, constants)
    assert interpreted == executed == vm.Value("Int", 14)
    assert trace["interpreter"] == trace["vm"]

    bad_programs = [
        [("ADD",), ("RETURN",)],
        [("CONST", 99), ("RETURN",)],
        [("CONST", 0)],
    ]
    for bad in bad_programs:
        try:
            vm.verify(bad, constants)
        except vm.VerificationError:
            pass
        else:
            raise AssertionError(f"invalid bytecode accepted: {bad}")
    overflow_program, overflow_constants = vm.compile_expression(["+", vm.I64_MAX, 1])
    for engine in (
        lambda: vm.evaluate_expression(["+", vm.I64_MAX, 1]),
        lambda: vm.execute(overflow_program, overflow_constants),
    ):
        try:
            engine()
        except vm.ExecutionError as fault:
            assert str(fault) == "MICA4002"
        else:
            raise AssertionError("unchecked backend overflow")
    print("PASS lab06 virtual target valid compile disassembly VM differential invalid-bytecode overflow")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
