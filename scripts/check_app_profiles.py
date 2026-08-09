#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import re
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from process_runner import CommandSpawnError, ProcessResult, run_process

ROOT = Path(__file__).resolve().parents[1]
REFERENCE = ROOT / "exercises/field-notes/reference"
EXPO = ROOT / "node_modules/.bin/expo"
PROFILE_ENV = "FIELD_NOTES_BUILD_PROFILE"
PUBLIC_PROFILES = ("development", "preview", "production")
PROFILE_EXPECTATIONS: dict[str, dict[str, str]] = {
    "development": {
        "name": "Field Notes Development",
        "application_id": "dev.openai.guides.fieldnotes.reference.development",
        "scheme": "fieldnotes-development",
        "app_identity_label": "development",
        "backend_environment_label": "local-development",
    },
    "preview": {
        "name": "Field Notes Preview",
        "application_id": "dev.openai.guides.fieldnotes.reference.preview",
        "scheme": "fieldnotes-preview",
        "app_identity_label": "preview",
        "backend_environment_label": "preview-test-not-configured",
    },
    "production": {
        "name": "Field Notes Reference",
        "application_id": "dev.openai.guides.fieldnotes.reference",
        "scheme": "fieldnotes",
        "app_identity_label": "production",
        "backend_environment_label": "production-external-not-configured",
    },
}
URL_VALUE = re.compile(r"[a-z][a-z0-9+.-]*://", re.IGNORECASE)
SECRET_WORDS = {
    "secret",
    "token",
    "password",
    "passwd",
    "credential",
    "credentials",
    "privatekey",
    "apikey",
    "apiurl",
}


class AppProfileContractError(ValueError):
    pass


def _object(value: object, path: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise AppProfileContractError(f"{path}: expected an object")
    return value


def _at(value: object, path: tuple[str, ...]) -> object:
    current = value
    traversed: list[str] = []
    for key in path:
        traversed.append(key)
        current = _object(current, ".".join(traversed[:-1]) or "config").get(key)
        if current is None:
            raise AppProfileContractError(f"{'.'.join(traversed)}: missing")
    return current


def _key_words(key: str) -> set[str]:
    with_boundaries = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", key)
    pieces = [part for part in re.split(r"[^a-zA-Z0-9]+", with_boundaries.lower()) if part]
    words = set(pieces)
    words.add("".join(pieces))
    return words


def _reject_public_secrets_and_urls(value: object, path: str = "config") -> None:
    if isinstance(value, Mapping):
        for raw_key, child in value.items():
            key = str(raw_key)
            if _key_words(key).intersection(SECRET_WORDS):
                raise AppProfileContractError(f"{path}.{key}: secret-like public key")
            _reject_public_secrets_and_urls(child, f"{path}.{key}")
        return
    if isinstance(value, list):
        for index, child in enumerate(value):
            _reject_public_secrets_and_urls(child, f"{path}[{index}]")
        return
    if isinstance(value, str) and URL_VALUE.search(value):
        raise AppProfileContractError(f"{path}: URL value is forbidden in public config")


def validate_public_config(profile: str, config: object) -> dict[str, object]:
    if profile not in PROFILE_EXPECTATIONS:
        raise AppProfileContractError(f"unknown profile: {profile}")
    root = _object(config, "config")
    expected = PROFILE_EXPECTATIONS[profile]

    exact_values: tuple[tuple[tuple[str, ...], object], ...] = (
        (("name",), expected["name"]),
        (("version",), "1.0.0"),
        (("scheme",), expected["scheme"]),
        (("android", "package"), expected["application_id"]),
        (("android", "versionCode"), 1),
        (("ios", "bundleIdentifier"), expected["application_id"]),
        (("ios", "buildNumber"), "1"),
        (("runtimeVersion", "policy"), "appVersion"),
        (("updates", "enabled"), False),
        (("extra", "fieldNotes", "buildProfile"), profile),
        (
            ("extra", "fieldNotes", "appIdentityLabel"),
            expected["app_identity_label"],
        ),
        (
            ("extra", "fieldNotes", "backendEnvironmentLabel"),
            expected["backend_environment_label"],
        ),
    )
    for path, expected_value in exact_values:
        actual = _at(root, path)
        if type(actual) is not type(expected_value) or actual != expected_value:
            raise AppProfileContractError(
                f"{'.'.join(path)}: expected {expected_value!r}, received {actual!r}"
            )

    updates = _object(root["updates"], "updates")
    forbidden_update_keys = {"url", "channel"}.intersection(updates)
    if forbidden_update_keys:
        raise AppProfileContractError(
            f"updates: remote update routing keys are forbidden: {sorted(forbidden_update_keys)}"
        )
    _reject_public_secrets_and_urls(root)
    return {
        "profile": profile,
        "name": root["name"],
        "application_id": _at(root, ("android", "package")),
        "ios_bundle_identifier": _at(root, ("ios", "bundleIdentifier")),
        "scheme": root["scheme"],
        "version": root["version"],
        "android_version_code": _at(root, ("android", "versionCode")),
        "ios_build_number": _at(root, ("ios", "buildNumber")),
        "runtime_policy": _at(root, ("runtimeVersion", "policy")),
        "updates_enabled": _at(root, ("updates", "enabled")),
        "backend_environment_label": _at(
            root, ("extra", "fieldNotes", "backendEnvironmentLabel")
        ),
    }


def validate_raw_profile_config(profile: str, config: object) -> bool:
    root = _object(config, "rawConfig")
    plugins = root.get("plugins")
    if not isinstance(plugins, list):
        raise AppProfileContractError("plugins: expected an array")
    matches: list[object] = []
    for entry in plugins:
        if entry == "expo-dev-client":
            matches.append(entry)
        elif isinstance(entry, list) and entry and entry[0] == "expo-dev-client":
            matches.append(entry)
    if len(matches) != 1:
        raise AppProfileContractError("plugins: expo-dev-client must appear exactly once")
    entry = matches[0]
    if not isinstance(entry, list) or len(entry) != 2:
        raise AppProfileContractError(
            "plugins.expo-dev-client: explicit options object is required"
        )
    options = _object(entry[1], "plugins.expo-dev-client.options")
    actual = options.get("addGeneratedScheme")
    expected = profile == "development"
    if type(actual) is not bool or actual is not expected:
        raise AppProfileContractError(
            "plugins.expo-dev-client.addGeneratedScheme: "
            f"expected {expected!r}, received {actual!r}"
        )
    _reject_public_secrets_and_urls(root, "rawConfig")
    return actual


def validate_profile_set(
    configs: Mapping[str, object], default_config: object
) -> list[dict[str, object]]:
    if set(configs) != set(PUBLIC_PROFILES):
        raise AppProfileContractError(
            f"profile set must be exactly {list(PUBLIC_PROFILES)}; received {sorted(configs)}"
        )
    summaries = [validate_public_config(profile, configs[profile]) for profile in PUBLIC_PROFILES]
    if default_config != configs["development"]:
        raise AppProfileContractError(
            f"unset {PROFILE_ENV} must resolve exactly like development"
        )
    for field in ("name", "application_id", "ios_bundle_identifier", "scheme"):
        values = [summary[field] for summary in summaries]
        if len(set(values)) != len(values):
            raise AppProfileContractError(f"{field}: profile values must be unique")
    return summaries


def _run(
    command: list[str], *, env: Mapping[str, str], timeout_seconds: float = 30
) -> ProcessResult:
    try:
        result = run_process(
            command,
            cwd=REFERENCE,
            timeout_seconds=timeout_seconds,
            grace_seconds=3,
            env=env,
        )
    except CommandSpawnError as error:
        raise AppProfileContractError(str(error)) from error
    if result.timed_out:
        raise AppProfileContractError(f"command timed out: {' '.join(command)}")
    return result


def node_version(base_env: Mapping[str, str]) -> str:
    result = _run(["node", "--version"], env=base_env, timeout_seconds=5)
    version = result.stdout.strip()
    if result.returncode != 0 or re.fullmatch(r"v24\.\d+\.\d+", version) is None:
        raise AppProfileContractError(
            f"Node 24 is required to resolve Expo config; observed {version!r}"
        )
    return version


def resolve_public_config(
    profile: str | None, base_env: Mapping[str, str]
) -> dict[str, object]:
    if not EXPO.is_file():
        raise AppProfileContractError(f"Expo CLI is not installed at {EXPO}")
    environment = dict(base_env)
    environment.update({"CI": "1", "EXPO_NO_TELEMETRY": "1"})
    if profile is None:
        environment.pop(PROFILE_ENV, None)
    else:
        environment[PROFILE_ENV] = profile
    result = _run(
        [str(EXPO), "config", "--type", "public", "--json"],
        env=environment,
    )
    if result.returncode != 0:
        raise AppProfileContractError(
            f"Expo config failed for {profile or '<unset>'}: "
            f"{(result.stderr or result.stdout)[-1200:]}"
        )
    try:
        parsed: Any = json.loads(result.stdout)
    except json.JSONDecodeError as error:
        raise AppProfileContractError(
            f"Expo config emitted invalid JSON for {profile or '<unset>'}: {error}"
        ) from error
    if not isinstance(parsed, dict):
        raise AppProfileContractError("Expo public config must be a JSON object")
    return parsed


def resolve_raw_profile_config(
    profile: str | None, base_env: Mapping[str, str]
) -> dict[str, object]:
    environment = dict(base_env)
    if profile is None:
        environment.pop(PROFILE_ENV, None)
    else:
        environment[PROFILE_ENV] = profile
    source = (
        "const factory=require('./app.config.js');"
        "process.stdout.write(JSON.stringify(factory.resolveConfig(process.env)));"
    )
    result = _run(["node", "-e", source], env=environment, timeout_seconds=5)
    if result.returncode != 0:
        raise AppProfileContractError(
            f"raw app config failed for {profile or '<unset>'}: "
            f"{(result.stderr or result.stdout)[-1200:]}"
        )
    try:
        parsed: Any = json.loads(result.stdout)
    except json.JSONDecodeError as error:
        raise AppProfileContractError(
            f"raw app config emitted invalid JSON for {profile or '<unset>'}: {error}"
        ) from error
    if not isinstance(parsed, dict):
        raise AppProfileContractError("raw app config must be a JSON object")
    return parsed


def unknown_profile_is_rejected(base_env: Mapping[str, str]) -> bool:
    environment = dict(base_env)
    environment.update(
        {
            "CI": "1",
            "EXPO_NO_TELEMETRY": "1",
            PROFILE_ENV: "unknown-review-profile",
        }
    )
    result = _run(
        [str(EXPO), "config", "--type", "public", "--json"],
        env=environment,
    )
    return result.returncode != 0 and not result.timed_out


def assess(base_env: Mapping[str, str] | None = None) -> dict[str, object]:
    environment = dict(os.environ if base_env is None else base_env)
    observed_node = node_version(environment)
    configs = {
        profile: resolve_public_config(profile, environment)
        for profile in PUBLIC_PROFILES
    }
    default_config = resolve_public_config(None, environment)
    summaries = validate_profile_set(configs, default_config)
    raw_configs = {
        profile: resolve_raw_profile_config(profile, environment)
        for profile in PUBLIC_PROFILES
    }
    raw_default = resolve_raw_profile_config(None, environment)
    if raw_default != raw_configs["development"]:
        raise AppProfileContractError(
            f"unset {PROFILE_ENV} raw config must resolve exactly like development"
        )
    for summary in summaries:
        profile = str(summary["profile"])
        summary["dev_client_generated_scheme"] = validate_raw_profile_config(
            profile, raw_configs[profile]
        )
    if not unknown_profile_is_rejected(environment):
        raise AppProfileContractError(f"unknown {PROFILE_ENV} was not rejected")
    return {
        "schema": 1,
        "status": "passed",
        "node": observed_node,
        "resolver": "expo config --type public --json plus raw plugin-input inspection",
        "profiles": summaries,
        "default_matches_development": True,
        "unknown_profile_rejected": True,
        "guarantees": {
            "public_config_contract": True,
            "native_generation": False,
            "native_compile": False,
            "signing": False,
            "device_install_or_launch": False,
            "store_delivery": False,
            "stable_approval": False,
        },
    }


def main() -> None:
    try:
        evidence = assess()
    except AppProfileContractError as error:
        print(
            json.dumps(
                {
                    "schema": 1,
                    "status": "failed",
                    "error": str(error),
                    "guarantees": {"stable_approval": False},
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        raise SystemExit(1) from error
    print(
        "APP PROFILES OK "
        f"profiles={','.join(PUBLIC_PROFILES)} default=development "
        "updates_enabled=false unknown_profile_rejected=true"
    )
    print("EVIDENCE_JSON " + json.dumps(evidence, ensure_ascii=False, sort_keys=True))
    print(
        "APP PROFILE LIMIT: resolved public config only; native generation/compile, "
        "signing, device install, backend availability, store delivery, Update delivery, "
        "and stable approval remain unverified"
    )


if __name__ == "__main__":
    main()
