"""JSON fixture를 결정론적 운영체제 상태 모델에 연결하는 명령행 인터페이스입니다."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Any, Mapping

from .deadlock import detect_deadlocked, find_wait_cycle, safe_sequence
from .device_io import DeviceQueue
from .filesystem import FileSystemModel
from .journal import Journal
from .lifecycle import KernelState
from .paging import MemoryManager, simulate_replacement
from .scheduler import JobSpec, simulate
from .synchronization import ConditionChannel


def _load(path: str) -> dict[str, Any]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("fixture 최상위 값은 JSON 객체여야 합니다.")
    return data


def _dump(data: Any) -> None:
    json.dump(data, sys.stdout, ensure_ascii=False, indent=2, sort_keys=True)
    sys.stdout.write("\n")


def run_lifecycle(data: Mapping[str, Any]) -> dict[str, Any]:
    model = KernelState()
    for raw in data.get("operations", []):
        if not isinstance(raw, Mapping):
            raise ValueError("lifecycle operation은 객체여야 합니다.")
        op = raw.get("op")
        if op == "add":
            model.add(str(raw["tid"]))
        elif op == "admit":
            model.admit(str(raw["tid"]))
        elif op == "dispatch":
            model.dispatch()
        elif op == "preempt":
            model.preempt()
        elif op == "yield":
            model.yield_cpu()
        elif op == "block":
            model.block(str(raw["channel"]), str(raw.get("reason", "unspecified")))
        elif op == "wake-one":
            model.wake_one(str(raw["channel"]))
        elif op == "wake-all":
            model.wake_all(str(raw["channel"]))
        elif op == "exit":
            model.exit_running()
        else:
            raise ValueError(f"지원하지 않는 lifecycle operation입니다: {op}")
    return model.snapshot()


def run_schedule(data: Mapping[str, Any]) -> dict[str, Any]:
    jobs = []
    for raw in data.get("jobs", []):
        if not isinstance(raw, Mapping):
            raise ValueError("job 항목은 객체여야 합니다.")
        jobs.append(
            JobSpec(
                tid=str(raw["tid"]),
                arrival=int(raw.get("arrival", 0)),
                cpu_bursts=tuple(int(item) for item in raw["cpu_bursts"]),
                io_waits=tuple(int(item) for item in raw.get("io_waits", [])),
                priority=int(raw.get("priority", 0)),
            )
        )
    result = simulate(
        jobs,
        str(data.get("policy", "fcfs")),
        quantum=int(data.get("quantum", 2)),
    )
    return {
        "policy": result.policy.value,
        "timeline": [asdict(tick) for tick in result.timeline],
        "completion_order": list(result.completion_order),
        "metrics": {tid: asdict(metrics) for tid, metrics in sorted(result.metrics.items())},
        "makespan": result.makespan,
        "cpu_busy_ticks": result.cpu_busy_ticks,
    }


def run_deadlock(data: Mapping[str, Any]) -> dict[str, Any]:
    mode = str(data.get("mode", "detect"))
    if mode == "cycle":
        graph = data.get("graph", {})
        if not isinstance(graph, Mapping):
            raise ValueError("graph는 객체여야 합니다.")
        return {"cycle": find_wait_cycle({str(key): list(value) for key, value in graph.items()})}
    available = [int(item) for item in data.get("available", [])]
    allocation = {str(key): [int(item) for item in value] for key, value in data.get("allocation", {}).items()}
    if mode == "detect":
        outstanding = {str(key): [int(item) for item in value] for key, value in data.get("outstanding", {}).items()}
        return {"deadlocked": sorted(detect_deadlocked(available, allocation, outstanding))}
    if mode == "avoid":
        maximum = {str(key): [int(item) for item in value] for key, value in data.get("maximum", {}).items()}
        sequence = safe_sequence(available, allocation, maximum)
        return {"safe": sequence is not None, "sequence": sequence}
    raise ValueError(f"지원하지 않는 deadlock mode입니다: {mode}")


def run_condition(data: Mapping[str, Any]) -> dict[str, Any]:
    channel = ConditionChannel(str(data.get("name", "event")))
    tokens: dict[str, Any] = {}
    outcomes: list[dict[str, Any]] = []
    for raw in data.get("operations", []):
        op = raw.get("op")
        tid = str(raw.get("tid", ""))
        if op == "prepare":
            tokens[tid] = channel.prepare_wait()
        elif op == "commit":
            outcomes.append({"tid": tid, "slept": channel.commit_wait(tid, tokens[tid])})
        elif op == "notify-one":
            outcomes.append({"awakened": channel.notify_one()})
        elif op == "notify-all":
            outcomes.append({"awakened": channel.notify_all()})
        else:
            raise ValueError(f"지원하지 않는 condition operation입니다: {op}")
    return {
        "generation": channel.generation,
        "waiters": sorted(channel.waiters),
        "outcomes": outcomes,
    }


def run_memory(data: Mapping[str, Any]) -> dict[str, Any]:
    model = MemoryManager(max_frames=int(data.get("max_frames", 64)))
    results: list[dict[str, Any]] = []
    for raw in data.get("operations", []):
        op = raw.get("op")
        if op == "create-process":
            model.create_process(str(raw["pid"]))
        elif op == "map-zero":
            model.map_demand_zero(str(raw["pid"]), int(raw["vpn"]), writable=bool(raw.get("writable", True)))
        elif op == "map-value":
            model.map_value(str(raw["pid"]), int(raw["vpn"]), int(raw.get("value", 0)), writable=bool(raw.get("writable", True)))
        elif op == "fork":
            model.fork(str(raw["parent"]), str(raw["child"]))
        elif op == "read":
            results.append({"value": model.read(str(raw["pid"]), int(raw["vpn"]))})
        elif op == "write":
            fault = model.write(str(raw["pid"]), int(raw["vpn"]), int(raw["value"]))
            results.append({"fault": None if fault is None else fault.value})
        elif op == "unmap":
            model.unmap(str(raw["pid"]), int(raw["vpn"]))
        elif op == "destroy-process":
            model.destroy_process(str(raw["pid"]))
        else:
            raise ValueError(f"지원하지 않는 memory operation입니다: {op}")
    return {"results": results, "snapshot": model.snapshot()}


def run_replacement(data: Mapping[str, Any]) -> dict[str, Any]:
    result = simulate_replacement(
        [int(item) for item in data.get("references", [])],
        int(data.get("capacity", 3)),
        str(data.get("policy", "fifo")),
    )
    return asdict(result)


def run_filesystem(data: Mapping[str, Any]) -> dict[str, Any]:
    model = FileSystemModel()
    journal = Journal()
    applied: set[int] = set()
    for raw in data.get("operations", []):
        op = raw.get("op")
        if op == "begin":
            txid = journal.begin()
            raw["result_txid"] = txid
        elif op == "journal":
            journal.append(int(raw["txid"]), dict(raw["operation"]))
        elif op == "commit":
            journal.commit(int(raw["txid"]))
        elif op == "recover":
            journal.recover(model.apply_operation, already_applied=applied)
        elif op == "crash":
            model.crash_recover()
        else:
            model.apply_operation(raw)
    return {"filesystem": model.snapshot(), "journal": journal.snapshot(), "applied": sorted(applied)}


def run_io(data: Mapping[str, Any]) -> dict[str, Any]:
    queue = DeviceQueue(queue_depth=int(data.get("queue_depth", 8)))
    aliases: dict[str, int] = {}
    reaped: list[dict[str, Any]] = []
    for raw in data.get("operations", []):
        op = raw.get("op")
        if op == "submit":
            request_id = queue.submit(
                str(raw["owner"]),
                tuple(int(item) for item in raw["buffer_pages"]),
                int(raw["length"]),
            )
            if "as" in raw:
                aliases[str(raw["as"])] = request_id
        elif op == "start":
            queue.start_next()
        elif op == "cancel":
            request_id = _request_id(raw, aliases)
            queue.cancel(str(raw["owner"]), request_id)
        elif op == "complete":
            request_id = _request_id(raw, aliases)
            queue.interrupt_complete(
                request_id,
                bytes_transferred=int(raw.get("bytes_transferred", 0)),
                error=None if raw.get("error") is None else str(raw.get("error")),
            )
        elif op == "reap":
            request = queue.reap(str(raw["owner"]))
            reaped.append({} if request is None else {
                "request_id": request.request_id,
                "state": request.state.value,
                "bytes_transferred": request.bytes_transferred,
                "error": request.error,
            })
        else:
            raise ValueError(f"지원하지 않는 io operation입니다: {op}")
    return {"snapshot": queue.snapshot(), "reaped": reaped}


def _request_id(raw: Mapping[str, Any], aliases: Mapping[str, int]) -> int:
    if "request_id" in raw:
        return int(raw["request_id"])
    return aliases[str(raw["request"])]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="결정론적 운영체제 상태 모델")
    parser.add_argument(
        "model",
        choices=["lifecycle", "schedule", "deadlock", "condition", "memory", "replacement", "filesystem", "io"],
    )
    parser.add_argument("fixture", help="JSON fixture 경로")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    data = _load(args.fixture)
    runners = {
        "lifecycle": run_lifecycle,
        "schedule": run_schedule,
        "deadlock": run_deadlock,
        "condition": run_condition,
        "memory": run_memory,
        "replacement": run_replacement,
        "filesystem": run_filesystem,
        "io": run_io,
    }
    try:
        result = runners[args.model](data)
    except (KeyError, TypeError, ValueError, RuntimeError, BufferError, PermissionError) as exc:
        print(f"모델 실행 실패: {exc}", file=sys.stderr)
        return 1
    _dump(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
