#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from gitops.reconcile import reconcile

ROOT = Path(__file__).resolve().parent
DIGEST = re.compile(r"^sha256:[0-9a-f]{64}$")
OWNER = re.compile(r"^group:default/team-[a-z0-9-]+$")


def load() -> dict[str, Any]:
    value = json.loads((ROOT / "profiles.json").read_text(encoding="utf-8"))
    if not isinstance(value, dict) or value.get("schemaVersion") != 1:
        raise ValueError("profiles.json schemaVersion 1이 필요합니다.")
    return value


def iac(case: dict[str, Any]) -> str:
    identities = [case[layer]["externalId"] for layer in ("configuration", "state", "actual")]
    versions = [case[layer]["version"] for layer in ("configuration", "state", "actual")]
    return "in-sync" if len(set(identities)) == 1 and len(set(versions)) == 1 else "drift"


def catalog(case: dict[str, Any]) -> str:
    component = case["component"]
    valid = (
        component.get("kind") == "Component"
        and bool(OWNER.fullmatch(str(component.get("owner", ""))))
        and str(component.get("statusUrl", "")).startswith("https://")
        and bool(component.get("profileVersion"))
    )
    return "accepted" if valid else "rejected"


def instant(value: Any) -> datetime:
    if not isinstance(value, str) or not value:
        raise ValueError("UTC timestamp가 필요합니다.")
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("timezone이 있는 timestamp가 필요합니다.")
    return parsed


def bounded_emergency(value: Any, evaluated_at: Any) -> bool:
    if not isinstance(value, dict):
        return False
    if not all(isinstance(value.get(field), str) and value[field].strip() for field in ("ticket", "owner", "expiresAt")):
        return False
    try:
        duration = instant(value["expiresAt"]) - instant(evaluated_at)
        return timedelta(0) < duration <= timedelta(hours=24)
    except ValueError:
        return False


def gitops(case: dict[str, Any]) -> str:
    try:
        result = reconcile(case.get("desired"), case.get("live"))
    except (TypeError, ValueError):
        return "invalid"
    if result["action"] == "none":
        return "in-sync"
    if bounded_emergency(case.get("emergency"), case.get("evaluatedAt")):
        return "break-glass"
    return "reconcile"


def policy(case: dict[str, Any]) -> str:
    request = case["request"]
    if request.get("environmentClass") != "production":
        return "allow"
    return "allow" if DIGEST.fullmatch(str(request.get("releaseDigest", ""))) else "deny"


CHECKERS = {"iac": iac, "catalog": catalog, "gitops": gitops, "policy": policy}


def main() -> int:
    try:
        profiles = load()
        total = 0
        for profile, checker in CHECKERS.items():
            cases = profiles.get(profile)
            if not isinstance(cases, list) or not cases:
                raise ValueError(f"{profile}: case 배열이 필요합니다.")
            for case in cases:
                if not isinstance(case, dict):
                    raise ValueError(f"{profile}: case는 object여야 합니다.")
                actual = checker(case)
                expected = case.get("expected")
                marker = "PASS" if actual == expected else "FAIL"
                print(f"[{marker}] {profile}/{case.get('id')} expected={expected} actual={actual}")
                if marker == "FAIL":
                    return 1
                total += 1
    except (OSError, UnicodeError, json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
        print(f"PROFILE ERROR: {exc}", file=sys.stderr)
        return 2
    print(f"PROFILE SUMMARY: PASS cases={total} external_resources=0 network=0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
