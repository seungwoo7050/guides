from __future__ import annotations

from collections import defaultdict


def _positive_int(value: object, label: str, minimum: int = 1) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < minimum:
        raise ValueError(f"{label} must be an integer >= {minimum}")
    return value


def _nonnegative_int(value: object, label: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ValueError(f"{label} must be a non-negative integer")
    return value


def _file(raw: object) -> dict:
    if not isinstance(raw, dict):
        raise ValueError("file metadata must be an object")
    path = raw.get("path")
    partition = raw.get("partition")
    active = raw.get("active")
    if not isinstance(path, str) or not path:
        raise ValueError("file path must be a non-empty string")
    if not isinstance(partition, str) or not partition:
        raise ValueError("partition must be a non-empty string")
    if not isinstance(active, bool):
        raise ValueError("active must be boolean")
    return {
        "path": path,
        "partition": partition,
        "schema_id": _nonnegative_int(raw.get("schema_id"), "schema_id"),
        "spec_id": _nonnegative_int(raw.get("spec_id"), "spec_id"),
        "bytes": _nonnegative_int(raw.get("bytes"), "bytes"),
        "rows": _nonnegative_int(raw.get("rows"), "rows"),
        "active": active,
    }


def plan_compaction(files: list[dict], target_bytes: int, max_group_files: int) -> list[dict]:
    target = _positive_int(target_bytes, "target_bytes")
    max_files = _positive_int(max_group_files, "max_group_files", minimum=2)
    if not isinstance(files, list):
        raise ValueError("files must be a list")
    normalized = [_file(raw) for raw in files]
    paths = [file["path"] for file in normalized]
    if len(paths) != len(set(paths)):
        raise ValueError("file paths must be unique")

    buckets: dict[tuple[str, int, int], list[dict]] = defaultdict(list)
    for file in normalized:
        if file["active"] and file["bytes"] < target:
            buckets[(file["partition"], file["schema_id"], file["spec_id"])].append(file)

    plans: list[dict] = []
    for identity in sorted(buckets):
        bins: list[dict] = []
        for file in sorted(buckets[identity], key=lambda value: (-value["bytes"], value["path"])):
            destination = next(
                (
                    group
                    for group in bins
                    if len(group["files"]) < max_files and group["bytes"] + file["bytes"] <= target
                ),
                None,
            )
            if destination is None:
                destination = {"files": [], "bytes": 0}
                bins.append(destination)
            destination["files"].append(file)
            destination["bytes"] += file["bytes"]
        for group in bins:
            if len(group["files"]) < 2:
                continue
            inputs = sorted(group["files"], key=lambda value: value["path"])
            plans.append(
                {
                    "partition": identity[0],
                    "schema_id": identity[1],
                    "spec_id": identity[2],
                    "inputs": [file["path"] for file in inputs],
                    "input_bytes": sum(file["bytes"] for file in inputs),
                    "input_rows": sum(file["rows"] for file in inputs),
                }
            )
    return sorted(plans, key=lambda plan: (plan["partition"], plan["schema_id"], plan["spec_id"], plan["inputs"]))
