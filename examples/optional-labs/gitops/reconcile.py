#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any


DIGEST = re.compile(r"^sha256:[0-9a-f]{64}$")


def read(path: str) -> dict[str, Any]:
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path}: object가 필요합니다.")
    return value


def validate_state(label: str, value: Any) -> None:
    if not isinstance(value, dict):
        raise ValueError(f"{label}: object가 필요합니다.")
    for field in ("service", "environment", "revision"):
        if not isinstance(value.get(field), str) or not value[field].strip():
            raise ValueError(f"{label}.{field}: non-empty string이 필요합니다.")
    if not DIGEST.fullmatch(str(value.get("artifactDigest", ""))):
        raise ValueError(f"{label}.artifactDigest: sha256 digest가 필요합니다.")


def reconcile(desired: Any, live: Any) -> dict[str, str]:
    validate_state("desired", desired)
    validate_state("live", live)
    for field in ("service", "environment"):
        if desired[field] != live[field]:
            raise ValueError(f"{field}: 다른 target state는 비교할 수 없습니다.")

    same = (
        desired["revision"] == live["revision"]
        and desired["artifactDigest"] == live["artifactDigest"]
    )
    return {
        "service": desired["service"],
        "environment": desired["environment"],
        "desiredRevision": desired["revision"],
        "liveRevision": live["revision"],
        "desiredDigest": desired["artifactDigest"],
        "liveDigest": live["artifactDigest"],
        "action": "none" if same else "reconcile",
    }


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        print("usage: reconcile.py DESIRED LIVE", file=sys.stderr)
        return 2
    try:
        desired = read(argv[1])
        live = read(argv[2])
        result = reconcile(desired, live)
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        print(f"GITOPS ERROR: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0 if result["action"] == "none" else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
