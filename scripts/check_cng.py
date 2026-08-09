#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import os
import plistlib
import re
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

from process_runner import CommandSpawnError, ProcessResult, run_process
from source_manifest import SourceManifestError, build_manifest, copy_source_subset

ROOT = Path(__file__).resolve().parents[1]
SOURCE_RELATIVE = Path("exercises/field-notes/reference")
EXPO = ROOT / "node_modules/.bin/expo"
PROFILE_ENV = "FIELD_NOTES_BUILD_PROFILE"
CNG_PROFILE = "development"
ANDROID_NS = "{http://schemas.android.com/apk/res/android}"
TOOLS_NS = "{http://schemas.android.com/tools}"
VIEW = "android.intent.action.VIEW"
DEFAULT = "android.intent.category.DEFAULT"
BROWSABLE = "android.intent.category.BROWSABLE"
ANDROID_REQUIRED_PERMISSIONS = {
    "android.permission.ACCESS_COARSE_LOCATION",
    "android.permission.ACCESS_FINE_LOCATION",
    "android.permission.CAMERA",
    "android.permission.POST_NOTIFICATIONS",
}
ANDROID_FORBIDDEN_PERMISSIONS = {
    "android.permission.ACCESS_BACKGROUND_LOCATION",
    "android.permission.FOREGROUND_SERVICE",
    "android.permission.FOREGROUND_SERVICE_DATA_SYNC",
    "android.permission.FOREGROUND_SERVICE_LOCATION",
    "android.permission.READ_EXTERNAL_STORAGE",
    "android.permission.READ_MEDIA_IMAGES",
    "android.permission.RECORD_AUDIO",
    "android.permission.SCHEDULE_EXACT_ALARM",
    "android.permission.USE_EXACT_ALARM",
    "android.permission.WRITE_EXTERNAL_STORAGE",
}
IOS_REQUIRED_USAGE_DESCRIPTIONS = {
    "NSCameraUsageDescription",
    "NSLocationWhenInUseUsageDescription",
}
IOS_FORBIDDEN_USAGE_DESCRIPTIONS = {
    "NSLocationAlwaysAndWhenInUseUsageDescription",
    "NSLocationAlwaysUsageDescription",
    "NSMicrophoneUsageDescription",
}
IOS_REQUIRED_BACKGROUND_MODES = {"processing"}
IOS_FORBIDDEN_BACKGROUND_MODES = {
    "audio",
    "fetch",
    "location",
    "remote-notification",
}
IOS_REQUIRED_BACKGROUND_TASK_IDENTIFIERS = {
    "com.expo.modules.backgroundtask.processing"
}


def fail(message: str, output: str = "") -> None:
    detail = f"\n{output[-5000:]}" if output else ""
    raise SystemExit(f"CNG ERROR: {message}{detail}")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(command: list[str], cwd: Path, timeout_seconds: int) -> ProcessResult:
    try:
        result = run_process(
            command,
            cwd=cwd,
            timeout_seconds=timeout_seconds,
            combine_output=False,
            grace_seconds=5,
            env={
                **os.environ,
                "CI": "1",
                "EXPO_NO_TELEMETRY": "1",
                PROFILE_ENV: CNG_PROFILE,
            },
        )
    except CommandSpawnError as error:
        fail(str(error))
    if result.timed_out:
        fail(f"command timed out: {' '.join(command)}", result.stdout + "\n" + result.stderr)
    if result.returncode != 0:
        fail(
            f"command failed: {' '.join(command)} exit={result.returncode}",
            result.stdout + "\n" + result.stderr,
        )
    return result


def scheme_values(config: dict[str, object]) -> set[str]:
    raw = config.get("scheme")
    if isinstance(raw, str):
        return {raw}
    if isinstance(raw, list) and all(isinstance(value, str) for value in raw):
        return set(raw)
    return set()


def validate_android_links(manifest_path: Path, expected_schemes: set[str]) -> dict[str, str]:
    root = ET.parse(manifest_path).getroot()
    application = root.find("application")
    if application is None:
        fail("generated Android manifest에 application이 없습니다.")
    owners: dict[str, str] = {}
    for activity in list(application.findall("activity")) + list(application.findall("activity-alias")):
        activity_name = activity.attrib.get(f"{ANDROID_NS}name", "<unnamed>")
        if activity.attrib.get(f"{ANDROID_NS}exported") != "true":
            continue
        for intent_filter in activity.findall("intent-filter"):
            actions = {
                item.attrib.get(f"{ANDROID_NS}name") for item in intent_filter.findall("action")
            }
            categories = {
                item.attrib.get(f"{ANDROID_NS}name") for item in intent_filter.findall("category")
            }
            if VIEW not in actions or not {DEFAULT, BROWSABLE}.issubset(categories):
                continue
            schemes = {
                item.attrib.get(f"{ANDROID_NS}scheme") for item in intent_filter.findall("data")
            }
            for scheme in expected_schemes.intersection(value for value in schemes if value):
                owners[scheme] = activity_name
    missing = expected_schemes - set(owners)
    if missing:
        fail(
            "generated Android exported VIEW+DEFAULT+BROWSABLE activity filter에 scheme 누락: "
            f"{sorted(missing)}"
        )
    return owners


def validate_android_permissions(manifest_path: Path) -> dict[str, object]:
    root = ET.parse(manifest_path).getroot()
    requested: set[str] = set()
    removal_directives: set[str] = set()
    for element_name in ("uses-permission", "uses-permission-sdk-23"):
        for item in root.findall(element_name):
            permission = item.attrib.get(f"{ANDROID_NS}name")
            if not permission:
                continue
            if item.attrib.get(f"{TOOLS_NS}node") == "remove":
                removal_directives.add(permission)
            else:
                requested.add(permission)

    effective = requested - removal_directives
    missing = ANDROID_REQUIRED_PERMISSIONS - effective
    forbidden = ANDROID_FORBIDDEN_PERMISSIONS.intersection(effective)
    if missing:
        fail(
            "generated Android manifest의 Stage 03 필수 permission 누락: "
            f"{sorted(missing)}"
        )
    if forbidden:
        fail(
            "generated Android manifest에 Stage 03 금지 permission이 유효하게 선언됨: "
            f"{sorted(forbidden)}"
        )
    return {
        "effective_requested": sorted(effective),
        "required": sorted(ANDROID_REQUIRED_PERMISSIONS),
        "forbidden_effective": [],
        "removal_directives": sorted(removal_directives),
    }


def android_application_ids(gradle: str) -> set[str]:
    return set(
        re.findall(r"\bapplicationId\s+(?:=\s*)?['\"]([^'\"]+)['\"]", gradle)
    )


def ios_bundle_ids(pbx: str) -> list[str]:
    values: list[str] = []
    for quoted, plain in re.findall(
        r"\bPRODUCT_BUNDLE_IDENTIFIER\s*=\s*(?:\"([^\"]+)\"|([^;]+));", pbx
    ):
        values.append((quoted or plain).strip())
    return values


def plist_schemes(plist: dict[str, object]) -> set[str]:
    raw_types = plist.get("CFBundleURLTypes", [])
    if not isinstance(raw_types, list):
        fail("generated iOS plist CFBundleURLTypes가 list가 아닙니다.")
    values: set[str] = set()
    for index, item in enumerate(raw_types):
        if not isinstance(item, dict):
            fail(f"generated iOS URL type가 object가 아닙니다: index={index}")
        raw_schemes = item.get("CFBundleURLSchemes", [])
        if not isinstance(raw_schemes, list) or not all(
            isinstance(value, str) for value in raw_schemes
        ):
            fail(f"generated iOS URL schemes가 string list가 아닙니다: index={index}")
        values.update(raw_schemes)
    return values


def validate_ios_permissions(plist: dict[str, object]) -> dict[str, object]:
    description_lengths: dict[str, int] = {}
    for key in sorted(IOS_REQUIRED_USAGE_DESCRIPTIONS):
        value = plist.get(key)
        if not isinstance(value, str) or not value.strip():
            fail(f"generated iOS plist의 Stage 03 usage description 누락/공백: {key}")
        description_lengths[key] = len(value.strip())

    forbidden_present = sorted(IOS_FORBIDDEN_USAGE_DESCRIPTIONS.intersection(plist))
    if forbidden_present:
        fail(
            "generated iOS plist에 Stage 03 금지 usage description 존재: "
            f"{forbidden_present}"
        )

    raw_background_modes = plist.get("UIBackgroundModes", [])
    if not isinstance(raw_background_modes, list) or not all(
        isinstance(value, str) for value in raw_background_modes
    ):
        fail("generated iOS plist UIBackgroundModes가 string list가 아닙니다.")
    background_mode_set = set(raw_background_modes)
    missing_background_modes = IOS_REQUIRED_BACKGROUND_MODES - background_mode_set
    forbidden_background_modes = IOS_FORBIDDEN_BACKGROUND_MODES.intersection(
        background_mode_set
    )
    if missing_background_modes:
        fail(
            "generated iOS plist UIBackgroundModes의 Stage 05 필수 mode 누락: "
            f"{sorted(missing_background_modes)}"
        )
    if forbidden_background_modes:
        fail(
            "generated iOS plist UIBackgroundModes에 Stage 05 금지 mode 존재: "
            f"{sorted(forbidden_background_modes)}"
        )
    background_modes = sorted(background_mode_set)

    raw_task_identifiers = plist.get("BGTaskSchedulerPermittedIdentifiers", [])
    if not isinstance(raw_task_identifiers, list) or not all(
        isinstance(value, str) for value in raw_task_identifiers
    ):
        fail(
            "generated iOS plist BGTaskSchedulerPermittedIdentifiers가 string list가 아닙니다."
        )
    task_identifiers = set(raw_task_identifiers)
    if task_identifiers != IOS_REQUIRED_BACKGROUND_TASK_IDENTIFIERS:
        fail(
            "generated iOS plist background task identifier 불일치: "
            f"expected={sorted(IOS_REQUIRED_BACKGROUND_TASK_IDENTIFIERS)} "
            f"actual={sorted(task_identifiers)}"
        )

    photo_library_keys = sorted(
        key
        for key in ("NSPhotoLibraryAddUsageDescription", "NSPhotoLibraryUsageDescription")
        if key in plist
    )
    return {
        "required_description_lengths": description_lengths,
        "forbidden_present": [],
        "background_modes": background_modes,
        "background_task_identifiers": sorted(task_identifiers),
        "photo_library_usage_description_keys": photo_library_keys,
    }


def main() -> None:
    if not EXPO.is_file() or not (ROOT / "node_modules").is_dir():
        fail("Expo CLI가 없습니다. 먼저 ./prepare.sh를 실행하십시오.")
    try:
        source_manifest = build_manifest(ROOT)
    except SourceManifestError as error:
        fail(str(error))

    with tempfile.TemporaryDirectory(prefix="mobile-app-cng-") as temporary:
        project = Path(temporary) / "reference"
        try:
            copied = copy_source_subset(
                ROOT, SOURCE_RELATIVE, project, entries=source_manifest
            )
        except SourceManifestError as error:
            fail(str(error))
        (project / "node_modules").symlink_to(ROOT / "node_modules", target_is_directory=True)

        config_result = run(
            [str(EXPO), "config", "--type", "public", "--json"], project, 120
        )
        try:
            config = json.loads(config_result.stdout)
        except json.JSONDecodeError as error:
            fail(f"public app config JSON을 읽지 못했습니다: {error}", config_result.stdout)
        if not isinstance(config, dict):
            fail("public app config가 object가 아닙니다.")
        android_config = config.get("android")
        ios_config = config.get("ios")
        expected_android = android_config.get("package") if isinstance(android_config, dict) else None
        expected_ios = ios_config.get("bundleIdentifier") if isinstance(ios_config, dict) else None
        expected_schemes = scheme_values(config)
        extra = config.get("extra")
        field_notes = extra.get("fieldNotes") if isinstance(extra, dict) else None
        resolved_profile = (
            field_notes.get("buildProfile") if isinstance(field_notes, dict) else None
        )
        if not isinstance(expected_android, str) or not isinstance(expected_ios, str):
            fail("public app config의 Android/iOS application identity가 없습니다.")
        if not expected_schemes:
            fail("public app config에 deep-link scheme이 없습니다.")
        if resolved_profile != CNG_PROFILE:
            fail(
                "public app config profile 불일치: "
                f"expected={CNG_PROFILE} actual={resolved_profile!r}"
            )

        run(
            [str(EXPO), "prebuild", "--clean", "--no-install", "--platform", "all"],
            project,
            720,
        )

        manifest_path = project / "android/app/src/main/AndroidManifest.xml"
        gradle_path = project / "android/app/build.gradle"
        plist_paths = list((project / "ios").glob("*/Info.plist"))
        pbx_paths = list((project / "ios").glob("*.xcodeproj/project.pbxproj"))
        for path in (manifest_path, gradle_path):
            if path.is_symlink() or not path.is_file():
                fail(f"clean CNG regular result 누락: {path.relative_to(project)}")
        if len(plist_paths) != 1 or len(pbx_paths) != 1:
            fail(
                "iOS plist/project 결과가 정확히 하나가 아닙니다: "
                f"plist={len(plist_paths)} project={len(pbx_paths)}"
            )
        if any(path.is_symlink() or not path.is_file() for path in (*plist_paths, *pbx_paths)):
            fail("iOS plist/project 결과에 symlink/special entry가 있습니다.")

        android_owners = validate_android_links(manifest_path, expected_schemes)
        android_permissions = validate_android_permissions(manifest_path)
        application_ids = android_application_ids(gradle_path.read_text(errors="replace"))
        if application_ids != {expected_android}:
            fail(
                f"generated Android applicationId 불일치: expected={expected_android} "
                f"actual={sorted(application_ids)}"
            )

        with plist_paths[0].open("rb") as handle:
            plist = plistlib.load(handle)
        if not isinstance(plist, dict):
            fail("generated iOS plist가 dictionary가 아닙니다.")
        ios_permissions = validate_ios_permissions(plist)
        actual_ios_schemes = plist_schemes(plist)
        missing_ios_schemes = expected_schemes - actual_ios_schemes
        if missing_ios_schemes:
            fail(f"generated iOS URL scheme 누락: {sorted(missing_ios_schemes)}")
        bundle_ids = ios_bundle_ids(pbx_paths[0].read_text(errors="replace"))
        if not bundle_ids or set(bundle_ids) != {expected_ios}:
            fail(
                f"generated iOS relevant build configuration bundle identifier 불일치: "
                f"expected={expected_ios} actual={sorted(set(bundle_ids))}"
            )

        evidence = {
            "copied_source_files": copied,
            "build_profile": resolved_profile,
            "android_application_id": expected_android,
            "android_link_owners": android_owners,
            "ios_bundle_id": expected_ios,
            "ios_build_configuration_count": len(bundle_ids),
            "permission_summary": {
                "android": android_permissions,
                "ios": ios_permissions,
            },
            "schemes": sorted(expected_schemes),
            "android_manifest_sha256": sha256(manifest_path),
            "ios_plist_sha256": sha256(plist_paths[0]),
            "ios_project_sha256": sha256(pbx_paths[0]),
        }
        print(
            "CNG OK "
            f"android_application_id={expected_android} ios_bundle_id={expected_ios} "
            f"schemes={','.join(sorted(expected_schemes))} "
            f"ios_configs={len(bundle_ids)}"
        )
        print("EVIDENCE_JSON " + json.dumps(evidence, ensure_ascii=False, sort_keys=True))
        print(
            "CNG LIMIT: generated identity/link/permission declarations only; native compile, "
            "runtime permission prompts/behavior, signing, install, device, and store remain unverified"
        )


if __name__ == "__main__":
    main()
