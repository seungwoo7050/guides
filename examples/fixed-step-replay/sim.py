#!/usr/bin/env python3
"""Small deterministic fixed-step simulation used by the guide verifier."""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent


class SimulationError(ValueError):
    pass


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SimulationError(f"cannot read {path.name}: {exc}") from exc


def canonical_bytes(state: dict[str, int]) -> bytes:
    return json.dumps(
        state,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def state_hash(state: dict[str, int]) -> str:
    return hashlib.sha256(canonical_bytes(state)).hexdigest()


def validate_inputs(config: dict[str, Any], trace: dict[str, Any]) -> None:
    for key in (
        "fixed_step_us",
        "max_frame_delta_us",
        "max_steps_per_frame",
        "target_ticks",
        "move_speed_milli_per_second",
        "dash_distance_milli",
        "dash_cooldown_ticks",
    ):
        if not isinstance(config.get(key), int) or config[key] <= 0:
            raise SimulationError(f"config.{key} must be a positive integer")
    if config.get("overload_policy") != "drop_whole_backlog_steps_keep_fraction":
        raise SimulationError("unsupported overload_policy")

    commands = trace.get("commands")
    schedules = trace.get("frame_schedules")
    initial = trace.get("initial_state")
    if not isinstance(commands, list) or not isinstance(schedules, dict) or not isinstance(initial, dict):
        raise SimulationError("trace requires initial_state, commands, and frame_schedules")

    command_ids: set[tuple[int, int]] = set()
    for command in commands:
        if not isinstance(command, dict):
            raise SimulationError("each command must be an object")
        tick = command.get("tick")
        sequence = command.get("sequence")
        if not isinstance(tick, int) or tick < 0 or not isinstance(sequence, int) or sequence < 0:
            raise SimulationError("command tick/sequence must be non-negative integers")
        key = (tick, sequence)
        if key in command_ids:
            raise SimulationError(f"duplicate command identity {key}")
        command_ids.add(key)
        if command.get("kind") not in {"move", "dash"}:
            raise SimulationError(f"unsupported command kind: {command.get('kind')}")

    for name, frames in schedules.items():
        if not isinstance(name, str) or not isinstance(frames, list) or not frames:
            raise SimulationError("each frame schedule must be a non-empty array")
        if any(not isinstance(delta, int) or delta < 0 for delta in frames):
            raise SimulationError(f"schedule {name} contains an invalid delta")


def commands_by_tick(trace: dict[str, Any]) -> dict[int, list[dict[str, Any]]]:
    result: dict[int, list[dict[str, Any]]] = {}
    for command in trace["commands"]:
        result.setdefault(command["tick"], []).append(command)
    for commands in result.values():
        commands.sort(key=lambda item: item["sequence"])
    return result


def apply_command(state: dict[str, int], command: dict[str, Any], config: dict[str, Any]) -> None:
    kind = command["kind"]
    if kind == "move":
        value = command.get("value")
        if (
            not isinstance(value, list)
            or len(value) != 2
            or any(not isinstance(axis, int) or axis < -1000 or axis > 1000 for axis in value)
        ):
            state["rejected_commands"] += 1
            return
        state["move_x_milli"], state["move_y_milli"] = value
        state["accepted_commands"] += 1
        return

    if kind == "dash":
        if (
            command.get("value") is not True
            or state["dash_cooldown_ticks"] != 0
            or (state["move_x_milli"] == 0 and state["move_y_milli"] == 0)
        ):
            state["rejected_commands"] += 1
            return
        state["x_milli"] += config["dash_distance_milli"] * state["move_x_milli"] // 1000
        state["y_milli"] += config["dash_distance_milli"] * state["move_y_milli"] // 1000
        state["dash_cooldown_ticks"] = config["dash_cooldown_ticks"]
        state["dash_count"] += 1
        state["accepted_commands"] += 1
        return

    raise SimulationError(f"unsupported command kind: {kind}")


def step(
    state: dict[str, int],
    commands: list[dict[str, Any]],
    config: dict[str, Any],
) -> None:
    for command in commands:
        apply_command(state, command, config)

    # Integer fixed-point integration. At 60 Hz and 60 units/s, full input moves
    # 1000 milli-units per tick. Integer division makes the rounding contract explicit.
    step_us = config["fixed_step_us"]
    speed = config["move_speed_milli_per_second"]
    state["x_milli"] += speed * state["move_x_milli"] * step_us // 1_000_000 // 1000
    state["y_milli"] += speed * state["move_y_milli"] * step_us // 1_000_000 // 1000

    if state["dash_cooldown_ticks"] > 0:
        state["dash_cooldown_ticks"] -= 1
    state["tick"] += 1


def run_schedule(
    schedule_name: str,
    frame_deltas: list[int],
    config: dict[str, Any],
    trace: dict[str, Any],
) -> dict[str, Any]:
    state = copy.deepcopy(trace["initial_state"])
    expected_state_keys = {
        "tick",
        "x_milli",
        "y_milli",
        "move_x_milli",
        "move_y_milli",
        "dash_cooldown_ticks",
        "dash_count",
        "accepted_commands",
        "rejected_commands",
    }
    if set(state) != expected_state_keys or any(not isinstance(v, int) for v in state.values()):
        raise SimulationError("initial_state fields do not match the simulation contract")

    by_tick = commands_by_tick(trace)
    accumulator = 0
    dropped = 0
    frames_used = 0
    max_steps_observed = 0
    target_ticks = config["target_ticks"]

    for raw_delta in frame_deltas:
        if state["tick"] >= target_ticks:
            break
        frames_used += 1
        accumulator += min(raw_delta, config["max_frame_delta_us"])
        steps_this_frame = 0

        while (
            accumulator >= config["fixed_step_us"]
            and steps_this_frame < config["max_steps_per_frame"]
            and state["tick"] < target_ticks
        ):
            current_tick = state["tick"]
            step(state, by_tick.get(current_tick, []), config)
            accumulator -= config["fixed_step_us"]
            steps_this_frame += 1

        max_steps_observed = max(max_steps_observed, steps_this_frame)
        if accumulator >= config["fixed_step_us"]:
            whole_backlog = accumulator - (accumulator % config["fixed_step_us"])
            dropped += whole_backlog
            accumulator %= config["fixed_step_us"]

    if state["tick"] != target_ticks:
        raise SimulationError(
            f"schedule {schedule_name} ended at tick {state['tick']}, expected {target_ticks}"
        )

    return {
        "schedule": schedule_name,
        "state": state,
        "state_hash": state_hash(state),
        "frames_used": frames_used,
        "remaining_accumulator_us": accumulator,
        "dropped_simulation_us": dropped,
        "max_steps_observed": max_steps_observed,
    }


def run_all(config_path: Path, trace_path: Path) -> dict[str, Any]:
    config = load_json(config_path)
    trace = load_json(trace_path)
    validate_inputs(config, trace)
    runs = {
        name: run_schedule(name, frames, config, trace)
        for name, frames in trace["frame_schedules"].items()
    }
    return {"config": config, "runs": runs}


def verify(results: dict[str, Any], expected_path: Path) -> None:
    expected = load_json(expected_path)
    expected_state = expected.get("canonical_state")
    expected_hash = expected.get("canonical_state_hash")
    if not isinstance(expected_state, dict) or not isinstance(expected_hash, str):
        raise SimulationError("expected-state.json is missing canonical state/hash")

    for name, result in results["runs"].items():
        if result["state"] != expected_state:
            raise SimulationError(f"{name}: canonical state mismatch")
        if result["state_hash"] != expected_hash:
            raise SimulationError(f"{name}: state hash mismatch")

    hashes = {result["state_hash"] for result in results["runs"].values()}
    if len(hashes) != 1:
        raise SimulationError("frame schedules produced different gameplay states")

    overload = results["runs"].get("overload")
    if overload is None or overload["dropped_simulation_us"] <= 0:
        raise SimulationError("overload schedule did not exercise backlog dropping")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=HERE / "config.json")
    parser.add_argument("--trace", type=Path, default=HERE / "input-trace.json")
    parser.add_argument("--expected", type=Path, default=HERE / "expected-state.json")
    parser.add_argument("--verify", action="store_true")
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args()

    try:
        results = run_all(args.config, args.trace)
        if args.verify:
            verify(results, args.expected)
        print(json.dumps(results, ensure_ascii=False, indent=2 if args.pretty else None, sort_keys=True))
        if args.verify:
            print("FIXED_STEP_REPLAY_OK", file=sys.stderr)
        return 0
    except SimulationError as exc:
        print(f"FIXED_STEP_REPLAY_ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
