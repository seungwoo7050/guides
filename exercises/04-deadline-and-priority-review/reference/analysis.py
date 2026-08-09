#!/usr/bin/env python3
"""Deterministic reference analysis for deadline and priority review."""

from __future__ import annotations

from typing import Any


def _ceil_div(value: int, divisor: int) -> int:
    return (value + divisor - 1) // divisor


def analyze_workload(workload: dict[str, Any]) -> dict[str, Any]:
    """Run conservative fixed-priority response-time iteration.

    Smaller numeric priority means higher priority.  All values use the unit in
    ``workload['unit']``. Interrupt interference applies to every task.
    """

    tasks = sorted(workload["tasks"], key=lambda task: (task["priority"], task["name"]))
    interrupts = workload.get("interrupts", [])
    result: dict[str, Any] = {"unit": workload.get("unit", "us"), "tasks": {}}
    for task in tasks:
        for key in ("wcet", "period", "deadline"):
            if not isinstance(task[key], int) or task[key] <= 0:
                raise ValueError(f"{task['name']}.{key} must be a positive integer")
        blocking = int(task.get("blocking", 0))
        if blocking < 0:
            raise ValueError("blocking cannot be negative")
        base = task["wcet"] + blocking
        response = base
        iterations = [response]
        converged = False
        for _ in range(100):
            interference = 0
            for higher in tasks:
                if higher["priority"] >= task["priority"]:
                    continue
                interference += _ceil_div(response, higher["period"]) * higher["wcet"]
            isr_interference = 0
            for interrupt in interrupts:
                isr_interference += _ceil_div(response, interrupt["min_gap"]) * interrupt["wcet"]
            next_response = base + interference + isr_interference
            if next_response == response:
                converged = True
                break
            response = next_response
            iterations.append(response)
            if response > max(task["deadline"] * 100, 1_000_000_000):
                break
        result["tasks"][task["name"]] = {
            "response": response,
            "deadline": task["deadline"],
            "blocking": blocking,
            "schedulable": converged and response <= task["deadline"],
            "iterations": iterations,
        }
    result["all_schedulable"] = all(item["schedulable"] for item in result["tasks"].values())
    return result


def analyze_queue(specification: dict[str, Any]) -> dict[str, Any]:
    """Simulate arrival-before-service queue pressure with drop-newest policy."""

    capacity = specification["capacity"]
    service_per_tick = specification["service_per_tick"]
    if capacity <= 0 or service_per_tick <= 0:
        raise ValueError("queue capacity and service_per_tick must be positive")
    if specification.get("drop_policy") != "drop_newest":
        raise ValueError("this reference profile requires an explicit drop_newest policy")
    arrivals = sorted(specification["arrivals"], key=lambda item: (item["time"], item["id"]))
    pending = list(arrivals)
    queue: list[dict[str, Any]] = []
    accepted = 0
    dropped: list[str] = []
    completed: list[dict[str, Any]] = []
    deadline_misses: list[str] = []
    max_depth = 0
    timeline: list[dict[str, Any]] = []
    tick = min((item["time"] for item in arrivals), default=0)
    steps = 0
    while pending or queue:
        steps += 1
        if steps > 10_000:
            raise RuntimeError("queue simulation did not converge")
        arrived: list[str] = []
        dropped_now: list[str] = []
        while pending and pending[0]["time"] == tick:
            event = pending.pop(0)
            arrived.append(event["id"])
            if len(queue) >= capacity:
                dropped.append(event["id"])
                dropped_now.append(event["id"])
            else:
                queue.append(event)
                accepted += 1
                max_depth = max(max_depth, len(queue))
        completed_now: list[str] = []
        for _ in range(service_per_tick):
            if not queue:
                break
            event = queue.pop(0)
            latency = tick - event["time"]
            completed.append({"id": event["id"], "completion": tick, "latency": latency})
            completed_now.append(event["id"])
            if latency > event["relative_deadline"]:
                deadline_misses.append(event["id"])
        timeline.append(
            {
                "time": tick,
                "arrived": arrived,
                "dropped": dropped_now,
                "completed": completed_now,
                "depth_after": len(queue),
            }
        )
        tick += 1
        if pending and not queue and tick < pending[0]["time"]:
            tick = pending[0]["time"]
    return {
        "accepted": accepted,
        "dropped": dropped,
        "completed": completed,
        "deadline_misses": deadline_misses,
        "max_depth": max_depth,
        "timeline": timeline,
    }


def simulate_priority_inversion(specification: dict[str, Any], *, protocol: str) -> dict[str, Any]:
    """Produce a per-tick trace for the canonical low/high/medium inversion."""

    if protocol not in {"none", "inheritance"}:
        raise ValueError("protocol must be none or inheritance")
    low = specification["low"]
    high = specification["high"]
    medium = specification["medium"]
    remaining = {
        "low": low["lock_work"],
        "high": high["work"],
        "medium": medium["work"],
    }
    completion: dict[str, int] = {}
    trace: list[dict[str, Any]] = []
    time = 0
    while any(value > 0 for value in remaining.values()):
        if time > specification.get("horizon", 100):
            raise RuntimeError("priority trace exceeded its horizon")
        high_blocked = time >= high["release"] and remaining["high"] > 0 and remaining["low"] > 0
        low_priority = high["priority"] if protocol == "inheritance" and high_blocked else low["priority"]
        candidates: list[tuple[int, str]] = []
        if time >= low["release"] and remaining["low"] > 0:
            candidates.append((low_priority, "low"))
        if time >= medium["release"] and remaining["medium"] > 0:
            candidates.append((medium["priority"], "medium"))
        if time >= high["release"] and remaining["high"] > 0 and not high_blocked:
            candidates.append((high["priority"], "high"))
        if not candidates:
            running = "idle"
        else:
            _, running = min(candidates, key=lambda item: (item[0], item[1]))
            remaining[running] -= 1
            if remaining[running] == 0:
                completion[running] = time + 1
        trace.append(
            {
                "time": time,
                "running": running,
                "high_state": "BLOCKED" if high_blocked else ("DONE" if remaining["high"] == 0 else "READY"),
                "low_effective_priority": low_priority,
            }
        )
        time += 1
    high_response = completion["high"] - high["release"]
    return {
        "protocol": protocol,
        "completion": completion,
        "high_response": high_response,
        "high_deadline_miss": high_response > high["deadline"],
        "trace": trace,
    }
