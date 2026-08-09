#!/usr/bin/env python3
"""Known wrong: response time is reduced to task WCET."""

from __future__ import annotations

import importlib.util
from pathlib import Path

REFERENCE = Path(__file__).resolve().parents[2] / "reference" / "analysis.py"
SPEC = importlib.util.spec_from_file_location("exercise4_reference_for_wrong", REFERENCE)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("cannot load reference analysis")
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def analyze_workload(workload):
    # BUG: average/isolated execution is not end-to-end response time.
    tasks = {
        task["name"]: {
            "response": task["wcet"],
            "deadline": task["deadline"],
            "blocking": 0,
            "schedulable": task["wcet"] <= task["deadline"],
            "iterations": [task["wcet"]],
        }
        for task in workload["tasks"]
    }
    return {"unit": workload.get("unit", "us"), "tasks": tasks, "all_schedulable": all(v["schedulable"] for v in tasks.values())}


analyze_queue = MODULE.analyze_queue
simulate_priority_inversion = MODULE.simulate_priority_inversion
