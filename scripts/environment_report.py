#!/usr/bin/env python3
from __future__ import annotations

import os
import platform
import re
import shutil
from datetime import UTC, datetime
from pathlib import Path

from process_runner import CommandSpawnError, run_process
from source_fingerprint import STATE_DIR, atomic_write_json, ensure_safe_state_dir

ROOT = Path(__file__).resolve().parents[1]
REPORT = STATE_DIR / "environment.json"


def probe(command: list[str], timeout: int = 8) -> dict[str, object]:
    executable = shutil.which(command[0])
    if not executable:
        return {"available": False, "command": command, "detail": "command not found"}
    try:
        result = run_process(command, cwd=ROOT, timeout_seconds=timeout)
    except CommandSpawnError as error:
        return {"available": False, "command": command, "detail": str(error)}
    if result.timed_out:
        return {"available": False, "command": command, "detail": "probe timed out"}
    output = (result.stdout + "\n" + result.stderr).strip()
    return {
        "available": result.returncode == 0,
        "command": command,
        "exit_code": result.returncode,
        "detail": output[:1200],
    }


def android_sdk() -> dict[str, object]:
    configured = os.environ.get("ANDROID_SDK_ROOT") or os.environ.get("ANDROID_HOME")
    if not configured:
        return {
            "configured": False,
            "api_36": False,
            "detail": "ANDROID_SDK_ROOT/ANDROID_HOME not set",
        }
    root = Path(configured).expanduser()
    platform_36 = root / "platforms/android-36"
    build_tools = root / "build-tools"
    build_36 = build_tools.is_dir() and any(
        path.is_dir() and re.fullmatch(r"36(?:\.\d+){0,2}", path.name)
        for path in build_tools.iterdir()
    )
    return {
        "configured": root.is_dir(),
        "path": str(root),
        "api_36": platform_36.is_dir(),
        "build_tools_36": build_36,
        "observation_level": (
            "observed-path-only: directory presence; package integrity, compile, install, and device use not proven"
        ),
    }


def main() -> None:
    report: dict[str, object] = {
        "schema": 1,
        "checked_at_utc": datetime.now(UTC).isoformat(),
        "host": {"system": platform.system(), "release": platform.release(), "machine": platform.machine()},
        "required_source_tools": {
            "node": probe(["node", "--version"]),
            "npm": probe(["npm", "--version"]),
            "python": probe(["python3", "--version"]),
        },
        "android": {
            "java": probe(["java", "-version"]),
            "adb": probe(["adb", "version"]),
            "sdk": android_sdk(),
        },
        "ios": {
            "xcodebuild": probe(["xcodebuild", "-version"]),
            "simctl": probe(["xcrun", "simctl", "list", "devices", "available"]),
        },
        "manual_evidence": {
            "android_native_build_install_device": "not-run",
            "ios_native_build_install_device": "not-run",
            "camera_location_notification_background": "not-run",
            "talkback_voiceover_performance": "not-run",
            "signing_store_submission_rollout": "not-run",
        },
        "claim_limit": (
            "host command/path observation only; availability does not prove native compile, signing, install, "
            "device behavior, or store delivery"
        ),
    }
    ensure_safe_state_dir()
    if REPORT.is_symlink() or (REPORT.exists() and not REPORT.is_file()):
        raise SystemExit(f"ENVIRONMENT ERROR: report가 regular file이 아닙니다: {REPORT}")
    atomic_write_json(REPORT, report)
    print(f"ENVIRONMENT REPORT {REPORT}")
    print(
        "OPTIONAL android_api36="
        f"{report['android']['sdk'].get('api_36', False)} "  # type: ignore[index,union-attr]
        f"xcode={report['ios']['xcodebuild'].get('available', False)} "  # type: ignore[index,union-attr]
        f"simctl={report['ios']['simctl'].get('available', False)}"  # type: ignore[index,union-attr]
    )
    print("MANUAL NOT-RUN device/accessibility/signing/store (see capstone evidence templates)")


if __name__ == "__main__":
    main()
