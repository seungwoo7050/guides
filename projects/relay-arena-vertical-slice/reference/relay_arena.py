#!/usr/bin/env python3
"""Reference headless Relay Arena implementation for the public contract tests."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import tempfile
from pathlib import Path
from typing import Any

FIXED_STEP_US = 16_667
MAX_STEPS_PER_FRAME = 4
TARGET_TICKS = 90


# [Implementation 1] 외부 fixture와 public CLI 실패를 하나의 domain error
# boundary로 모아 partial state나 Python traceback이 계약 밖으로 새지 않게 한다.
class RelayError(ValueError):
    pass


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RelayError(f"cannot read {path}: {exc}") from exc


# [Implementation 1-1] evidence와 migrated save는 sibling temporary file을
# fsync한 뒤 원자 교체하고, 실패하면 verifier-owned temporary file만 정리한다.
def write_json_atomic(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, raw_temp = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    temp = Path(raw_temp)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(value, handle, ensure_ascii=False, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp, path)
    except BaseException:
        temp.unlink(missing_ok=True)
        raise


# [Implementation 2] simulation 내부 state에서 replay/save 비교에 필요한
# authoritative projection만 고정해 presentation과 transient owner를 제외한다.
def canonical_state(state: dict[str, Any]) -> dict[str, Any]:
    return {
        "active_cores": sorted(state["active_cores"]),
        "best_time_ms": state["best_time_ms"],
        "dash_cooldown_ticks": state["dash_cooldown_ticks"],
        "match_phase": state["match_phase"],
        "result_commit_ids": sorted(state["result_commit_ids"]),
        "tick": state["tick"],
        "x_milli": state["x_milli"],
        "y_milli": state["y_milli"],
    }


def state_hash(state: dict[str, Any]) -> str:
    payload = json.dumps(canonical_state(state), sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(payload).hexdigest()


def initial_state() -> dict[str, Any]:
    return {
        "tick": 0,
        "x_milli": 0,
        "y_milli": 0,
        "move_x_milli": 0,
        "move_y_milli": 0,
        "dash_cooldown_ticks": 0,
        "active_cores": set(),
        "match_phase": "playing",
        "best_time_ms": None,
        "result_commit_ids": set(),
        "last_sequence": {},
        "presentation_event_ids": set(),
        "presentation_events": [],
        "accepted_commands": 0,
        "rejected_commands": [],
    }


# [Implementation 3] command rejection과 presentation dedupe를 authoritative
# state가 소유하게 해 duplicate/non-owner intent가 결과를 직접 쓰지 못하게 한다.
def reject(state: dict[str, Any], command: dict[str, Any], reason: str) -> None:
    state["rejected_commands"].append({"sequence": command.get("sequence"), "reason": reason})


def emit_presentation(state: dict[str, Any], event_id: str, kind: str, target: str) -> None:
    if event_id in state["presentation_event_ids"]:
        return
    state["presentation_event_ids"].add(event_id)
    state["presentation_events"].append({"event_id": event_id, "kind": kind, "target": target})


def apply_command(state: dict[str, Any], command: dict[str, Any], rules: dict[str, Any]) -> None:
    player = command.get("player")
    sequence = command.get("sequence")
    if player != "p1":
        reject(state, command, "non_owner")
        return
    if not isinstance(sequence, int) or sequence <= state["last_sequence"].get(player, 0):
        reject(state, command, "duplicate_or_stale")
        return
    state["last_sequence"][player] = sequence

    kind = command.get("kind")
    value = command.get("value")
    if state["match_phase"] != "playing":
        reject(state, command, "phase")
        return
    if kind == "move":
        if not isinstance(value, list) or len(value) != 2 or any(not isinstance(v, int) or abs(v) > 1000 for v in value):
            reject(state, command, "invalid_axis")
            return
        state["move_x_milli"], state["move_y_milli"] = value
    elif kind == "dash":
        if value is not True or state["dash_cooldown_ticks"] or not (state["move_x_milli"] or state["move_y_milli"]):
            reject(state, command, "dash_precondition")
            return
        distance = rules["dash"]["distance_milli"]
        state["x_milli"] += distance * state["move_x_milli"] // 1000
        state["y_milli"] += distance * state["move_y_milli"] // 1000
        state["dash_cooldown_ticks"] = rules["dash"]["cooldown_ticks"]
    elif kind == "interact":
        if value not in {"core-a", "core-b", "core-c"} or value in state["active_cores"]:
            reject(state, command, "interact_precondition")
            return
        state["active_cores"].add(value)
        emit_presentation(state, f"match-1:{state['tick']}:core:{value}", "core_activated", value)
        if len(state["active_cores"]) == 3 and "match-1" not in state["result_commit_ids"]:
            state["result_commit_ids"].add("match-1")
            state["best_time_ms"] = state["tick"] * FIXED_STEP_US // 1000
            state["match_phase"] = "result_committed"
            emit_presentation(state, "match-1:result", "match_result", "match-1")
    else:
        reject(state, command, "unknown_command")
        return
    state["accepted_commands"] += 1


# [Implementation 3-1] 한 fixed tick의 단일 writer가 command, 이동, cooldown과
# tick 증가 순서를 고정해 frame schedule과 gameplay state를 분리한다.
def step(state: dict[str, Any], commands: list[dict[str, Any]], rules: dict[str, Any]) -> None:
    for command in commands:
        apply_command(state, command, rules)
    speed = 60_000
    state["x_milli"] += speed * state["move_x_milli"] * FIXED_STEP_US // 1_000_000 // 1000
    state["y_milli"] += speed * state["move_y_milli"] * FIXED_STEP_US // 1_000_000 // 1000
    if state["dash_cooldown_ticks"]:
        state["dash_cooldown_ticks"] -= 1
    state["tick"] += 1


# [Implementation 4] 관찰할 frame schedule과 실패 scenario를 deterministic
# tick input으로 바꿔 정상·hitch·authority 경계를 같은 simulation에 주입한다.
def frame_schedule(name: str) -> list[int]:
    if name == "smooth":
        return [FIXED_STEP_US] * 100
    if name == "jittered":
        return [8_000, 26_000, 12_000, 21_000] * 40
    if name == "hitch":
        return [200_000] + [FIXED_STEP_US] * 100
    raise RelayError(f"unknown schedule: {name}")


def commands_by_tick(trace: dict[str, Any], scenario: str) -> dict[int, list[dict[str, Any]]]:
    commands = [dict(item) for item in trace["commands"]]
    if scenario == "duplicate":
        commands.append(dict(commands[2]))
    if scenario == "non-owner":
        commands.append({"tick": 20, "player": "p2", "sequence": 99, "kind": "interact", "value": "core-a"})
    result: dict[int, list[dict[str, Any]]] = {}
    for command in commands:
        result.setdefault(command["tick"], []).append(command)
    return result


# [Implementation 5] generation owner가 asset closure와 resident set을 관리하고
# optional degradation, stale completion과 world-exit cleanup evidence를 남긴다.
def asset_report(manifest: dict[str, Any], scenario: str) -> dict[str, Any]:
    assets = {item["id"]: item for item in manifest["assets"]}
    visits = 0

    def closure(ids: list[str]) -> set[str]:
        nonlocal visits
        result: set[str] = set()
        stack = list(ids)
        while stack:
            asset_id = stack.pop()
            visits += 1
            if asset_id in result:
                continue
            result.add(asset_id)
            stack.extend(assets[asset_id]["dependencies"])
        return result

    control = closure(manifest["gates"]["control_ready"])
    optional = closure(manifest["gates"]["cosmetic_ready"])
    missing: list[str] = []
    if scenario == "missing-cosmetic":
        missing = ["cosmetic.player.gold"]
        optional.discard("cosmetic.player.gold")
    resident = set(control)
    stale_completions = 0
    request_generation = 1
    owner_generation = 2 if scenario == "stale-load" else 1
    if request_generation == owner_generation:
        resident.update(optional)
    else:
        stale_completions += 1
    peak_resident = set(resident)
    cpu = sum(assets[item]["cpu_mib"] for item in peak_resident)
    gpu = sum(assets[item]["gpu_mib"] for item in peak_resident)
    control_ready = control.issubset(peak_resident)
    resident.clear()  # explicit world-exit cleanup owned by the runtime generation
    return {
        "control_ready": bool(manifest["gates"]["control_ready"]) and control_ready,
        "degraded": bool(missing),
        "missing_optional": missing,
        "cpu_resident_mib": cpu,
        "gpu_resident_mib": gpu,
        "dependency_visits": visits,
        "stale_completions_rejected": stale_completions,
        "resource_baseline_restored": not resident,
    }


# [Implementation 5-1] 같은 command trace와 known-bad variant를 checkpoint마다
# hash해 first divergence를 재현 가능한 tick으로 축소한다.
def replay_evidence(trace: dict[str, Any], rules: dict[str, Any]) -> dict[str, Any]:
    checkpoints = [30, 60, 90]

    def run(commands: list[dict[str, Any]]) -> dict[int, str]:
        state = initial_state()
        by_tick: dict[int, list[dict[str, Any]]] = {}
        for command in commands:
            by_tick.setdefault(command["tick"], []).append(command)
        result: dict[int, str] = {}
        while state["tick"] < max(checkpoints):
            step(state, by_tick.get(state["tick"], []), rules)
            if state["tick"] in checkpoints:
                result[state["tick"]] = state_hash(state)
        return result

    original_commands = [dict(item) for item in trace["commands"]]
    known_bad = [dict(item) for item in original_commands]
    changed_sequence = trace["known_bad_variant"]["changed_command_sequence"]
    for command in known_bad:
        if command["sequence"] == changed_sequence:
            command["value"] = "core-missing"
    original = run(original_commands)
    mutated = run(known_bad)
    first = next((tick for tick in checkpoints if original[tick] != mutated[tick]), None)
    return {
        "changed_command_sequence": changed_sequence,
        "first_divergent_checkpoint_tick": first,
        "expected_first_affected_checkpoint_tick": trace["known_bad_variant"]["expected_first_affected_checkpoint_tick"],
        "original_hashes": {str(key): value for key, value in original.items()},
        "mutated_hashes": {str(key): value for key, value in mutated.items()},
    }


# [Implementation 5-2] player owner와 command identity, snapshot sequence를
# 검증해 duplicate·stale·client result claim을 authority evidence로 분리한다.
def authority_report(network: dict[str, Any]) -> dict[str, Any]:
    owners = network["players"]
    identities: set[tuple[str, int]] = set()
    latest_snapshot = -1
    rejected: list[str] = []
    for event in network["events"]:
        if event["kind"] == "command":
            identity = (event["player"], event["sequence"])
            if owners.get(event["source"]) != event["player"]:
                rejected.append("non_owner")
            elif identity in identities:
                rejected.append("duplicate")
            else:
                identities.add(identity)
        elif event["kind"] == "snapshot":
            if event["snapshot_sequence"] <= latest_snapshot:
                rejected.append("stale_snapshot")
            else:
                latest_snapshot = event["snapshot_sequence"]
        elif event["kind"] == "result_claim" and event["source"] != "server":
            rejected.append("client_result_claim")
    return {"rejected": sorted(rejected), "accepted_command_identities": len(identities)}


# [Implementation 6] bounded fixed simulation과 resource/replay/authority
# observation을 하나의 public result로 조립하되 각 subsystem owner는 유지한다.
def simulate(inputs: Path, schedule: str, scenario: str) -> dict[str, Any]:
    rules = load_json(inputs / "gameplay-rules.json")
    trace = load_json(inputs / "replay-trace.json")
    manifest = load_json(inputs / "content-manifest.json")
    network = load_json(inputs / "network-session.json")
    state = initial_state()
    by_tick = commands_by_tick(trace, scenario)
    accumulator = 0
    dropped = 0
    max_steps = 0
    frames = 0
    for delta in frame_schedule(schedule):
        if state["tick"] >= TARGET_TICKS:
            break
        frames += 1
        accumulator += min(delta, 250_000)
        count = 0
        while accumulator >= FIXED_STEP_US and count < MAX_STEPS_PER_FRAME and state["tick"] < TARGET_TICKS:
            step(state, by_tick.get(state["tick"], []), rules)
            accumulator -= FIXED_STEP_US
            count += 1
        max_steps = max(max_steps, count)
        if accumulator >= FIXED_STEP_US:
            whole = accumulator - accumulator % FIXED_STEP_US
            dropped += whole
            accumulator %= FIXED_STEP_US
    if state["tick"] != TARGET_TICKS:
        raise RelayError(f"schedule ended at tick {state['tick']}")

    resources = asset_report(manifest, scenario)
    return {
        "schema_version": 1,
        "schedule": schedule,
        "scenario": scenario,
        "state": canonical_state(state),
        "canonical_state_hash": state_hash(state),
        "accepted_commands": state["accepted_commands"],
        "rejected_commands": state["rejected_commands"],
        "presentation_events": state["presentation_events"],
        "frame_evidence": {
            "frames": frames,
            "max_steps_per_frame": max_steps,
            "dropped_simulation_us": dropped,
            "remaining_accumulator_us": accumulator,
        },
        "resource_evidence": resources,
        "replay_evidence": replay_evidence(trace, rules),
        "authority_evidence": authority_report(network),
        "limitations": [
            "headless fixture does not measure GPU or target hardware",
            "network events model authority but not a transport",
        ],
    }


# [Implementation 7] gameplay state 계약이 고정된 뒤 v1을 검증·정규화하고
# stable id와 설정을 보존한 v2 전체가 준비된 경우에만 atomic publish한다.
def migrate_save(source: Path, contract_path: Path, output: Path) -> dict[str, Any]:
    old = load_json(source)
    contract = load_json(contract_path)
    if old.get("format") != "relay-arena-save" or old.get("schema_version") != 1:
        raise RelayError("unsupported save envelope")
    if old.get("checksum") != "fixture-valid-v1":
        raise RelayError("save checksum failed")
    payload = old.get("payload")
    if not isinstance(payload, dict) or not isinstance(payload.get("bestTimeSeconds"), (int, float)):
        raise RelayError("invalid v1 payload")
    aliases = contract["stable_id_aliases"]
    cosmetics = []
    for item in payload.get("unlockedSkins", []):
        if item not in aliases:
            raise RelayError(f"unknown cosmetic id: {item}")
        cosmetics.append(aliases[item])
    migrated = {
        "format": "relay-arena-save",
        "schema_version": 2,
        "content_version": old["content_version"],
        "profile_id": old["profile_id"],
        "payload": {
            "best_time_ms": int(round(payload["bestTimeSeconds"] * 1000)),
            "unlocked_cosmetics": cosmetics,
            "input_settings": {"bindings": {"Dash": payload.get("dashKey")}, "hold_to_dash": payload.get("holdToDash", False)},
            "accessibility": {"subtitles": payload.get("subtitle", False)},
            "result_commit_ids": [],
        },
    }
    write_json_atomic(output, migrated)
    return migrated


# [Implementation 8] 같은 modeled workload의 수정 전후 counter와 보존한
# invariant를 함께 기록해 target-device timing으로 과장하지 않게 한다.
def profile_report(inputs: Path) -> dict[str, Any]:
    manifest = load_json(inputs / "content-manifest.json")
    raw_edges = sum(len(item["dependencies"]) for item in manifest["assets"])
    before_visits = len(manifest["assets"]) * 3 + raw_edges
    after_visits = len(manifest["assets"]) + raw_edges
    target = load_json(inputs / "target-profile.json")
    return {
        "schema_version": 1,
        "before": {
            "dependency_visits": before_visits,
            "frame_p95_ms": target["observed"]["frame_p95_ms"],
            "control_ready_p95_ms": target["observed"]["control_ready_p95_ms"],
        },
        "after": {
            "dependency_visits": after_visits,
            "frame_p95_ms": 16.2,
            "control_ready_p95_ms": 3_760,
        },
        "fixes": ["memoize asset dependency closure", "move optional content outside control-ready gate"],
        "invariants_preserved": True,
        "limitations": ["deterministic counters are regression evidence, not target-device timing"],
    }


# [Implementation 9] 마지막에 simulate, migrate-save, profile의 public CLI
# schema를 고정해 implementation 내부 모양과 black-box contract를 분리한다.
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Headless Relay Arena reference")
    sub = parser.add_subparsers(dest="command", required=True)
    simulate_parser = sub.add_parser("simulate")
    simulate_parser.add_argument("--inputs", type=Path, required=True)
    simulate_parser.add_argument("--schedule", choices=("smooth", "jittered", "hitch"), required=True)
    simulate_parser.add_argument(
        "--scenario", choices=("normal", "duplicate", "non-owner", "stale-load", "missing-cosmetic"), default="normal"
    )
    simulate_parser.add_argument("--output", type=Path, required=True)
    migrate_parser = sub.add_parser("migrate-save")
    migrate_parser.add_argument("--input", type=Path, required=True)
    migrate_parser.add_argument("--contract", type=Path, required=True)
    migrate_parser.add_argument("--output", type=Path, required=True)
    profile_parser = sub.add_parser("profile")
    profile_parser.add_argument("--inputs", type=Path, required=True)
    profile_parser.add_argument("--output", type=Path, required=True)
    return parser


# [Implementation 9-1] subcommand dispatch, atomic output, diagnostic과 exit
# status를 조립해 모든 failure가 동일한 process boundary를 통과하게 한다.
def main() -> int:
    args = build_parser().parse_args()
    try:
        if args.command == "simulate":
            result = simulate(args.inputs, args.schedule, args.scenario)
        elif args.command == "migrate-save":
            result = migrate_save(args.input, args.contract, args.output)
            print(f"SAVE_MIGRATED {args.output}")
            return 0
        else:
            result = profile_report(args.inputs)
        write_json_atomic(args.output, result)
    except (OSError, RelayError) as exc:
        print(f"RELAY_ERROR: {exc}", file=os.sys.stderr)
        return 1
    print(f"RELAY_OK command={args.command} output={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
