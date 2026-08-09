#!/usr/bin/env python3
"""Compute Lamport/vector clocks for a finite event trace."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def compute(trace: dict[str, Any]) -> dict[str, Any]:
    processes = list(trace["processes"])
    lamport = {process: 0 for process in processes}
    vector = {process: {p: 0 for p in processes} for process in processes}
    messages: dict[str, dict[str, Any]] = {}
    result_events: list[dict[str, Any]] = []
    per_process_seen: dict[str, list[str]] = {p: [] for p in processes}
    event_process: dict[str, str] = {}
    send_by_message: dict[str, str] = {}
    receive_by_message: dict[str, str] = {}

    for event in trace["events"]:
        event_id = event["id"]
        process = event["process"]
        kind = event["kind"]
        if process not in lamport:
            raise ValueError(f"unknown process: {process}")

        if kind == "receive":
            message_id = event["message"]
            if message_id not in messages:
                raise ValueError(f"receive before send: {message_id}")
            sent = messages[message_id]
            lamport[process] = max(lamport[process], int(sent["lamport"])) + 1
            for p in processes:
                vector[process][p] = max(vector[process][p], int(sent["vector"][p]))
            vector[process][process] += 1
            receive_by_message[message_id] = event_id
        else:
            lamport[process] += 1
            vector[process][process] += 1

        clock = {
            "id": event_id,
            "process": process,
            "kind": kind,
            "lamport": lamport[process],
            "vector": dict(vector[process]),
        }
        result_events.append(clock)
        per_process_seen[process].append(event_id)
        event_process[event_id] = process

        if kind == "send":
            message_id = event["message"]
            if message_id in messages:
                raise ValueError(f"duplicate message id: {message_id}")
            messages[message_id] = {
                "lamport": lamport[process],
                "vector": dict(vector[process]),
            }
            send_by_message[message_id] = event_id

    cuts: dict[str, dict[str, Any]] = {}
    all_events = {event["id"]: event for event in trace["events"]}
    for cut_id, included_list in trace.get("candidate_cuts", {}).items():
        included = set(included_list)
        reasons: list[str] = []

        unknown = included - set(all_events)
        if unknown:
            reasons.append(f"unknown events: {sorted(unknown)}")

        for process, ordered_ids in per_process_seen.items():
            seen_gap = False
            for event_id in ordered_ids:
                if event_id not in included:
                    seen_gap = True
                elif seen_gap:
                    reasons.append(f"{process}: {event_id} before a missing local predecessor")
                    break

        for message_id, receive_id in receive_by_message.items():
            send_id = send_by_message[message_id]
            if receive_id in included and send_id not in included:
                reasons.append(f"receive {receive_id} includes no send {send_id}")

        cuts[cut_id] = {"consistent": not reasons, "reasons": reasons}

    return {"events": result_events, "cuts": cuts}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("trace", type=Path)
    args = parser.parse_args()
    data = json.loads(args.trace.read_text(encoding="utf-8"))
    print(json.dumps(compute(data), ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
