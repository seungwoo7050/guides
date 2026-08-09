#!/usr/bin/env python3
"""Build a reproducible dataset identity from pinned execution inputs."""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping
from typing import Any


_FLOATING_VERSION = re.compile(
    r"(^|[:/@])(?:latest|current|main|head|tip)($|[:/@])",
    re.IGNORECASE,
)


def _required_text(value: object, label: str) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise ValueError(f"{label} must be a non-empty trimmed string")
    return value


def _pinned_map(value: object, label: str, *, required: bool) -> dict[str, str]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{label} must be a mapping")
    result: dict[str, str] = {}
    for raw_key, raw_version in value.items():
        key = _required_text(raw_key, f"{label} key")
        version = _required_text(raw_version, f"{label}.{key}")
        if _FLOATING_VERSION.search(version):
            raise ValueError(f"{label}.{key} must be pinned, not {version!r}")
        result[key] = version
    if required and not result:
        raise ValueError(f"{label} must not be empty")
    return result


def _json_object(value: object, label: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{label} must be a mapping")
    if any(not isinstance(key, str) or not key for key in value):
        raise ValueError(f"{label} keys must be non-empty strings")
    try:
        encoded = json.dumps(
            dict(value),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
        normalized = json.loads(encoded)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{label} must contain finite JSON values") from exc
    if not isinstance(normalized, dict):
        raise ValueError(f"{label} must be a JSON object")
    return normalized


def build_manifest(
    *,
    product: str,
    data_interval: str,
    source_positions: Mapping[str, str],
    code_revision: str,
    config: Mapping[str, Any],
    schema_versions: Mapping[str, str] | None = None,
    reference_versions: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    """Return the canonical logical inputs used to derive a dataset version."""

    revision = _required_text(code_revision, "code_revision")
    if _FLOATING_VERSION.search(revision):
        raise ValueError("code_revision must be pinned")
    return {
        "identity_version": 1,
        "product": _required_text(product, "product"),
        "data_interval": _required_text(data_interval, "data_interval"),
        "source_positions": _pinned_map(source_positions, "source_positions", required=True),
        "code_revision": revision,
        "config": _json_object(config, "config"),
        "schema_versions": _pinned_map(schema_versions or {}, "schema_versions", required=False),
        "reference_versions": _pinned_map(
            reference_versions or {}, "reference_versions", required=False
        ),
    }


def dataset_identity(**kwargs: Any) -> str:
    """Return a content identity that changes when any pinned logical input changes."""

    manifest = build_manifest(**kwargs)
    encoded = json.dumps(
        manifest,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


def demo() -> None:
    arguments = {
        "product": "daily-revenue",
        "data_interval": "[2026-08-09T00:00:00Z,2026-08-10T00:00:00Z)",
        "source_positions": {
            "orders": "lsn:0/16B6A20",
            "payments": "sha256:payment-manifest-v4",
        },
        "code_revision": "git:4f7c2a1",
        "config": {"timezone": "UTC", "currency_unit": "minor"},
        "schema_versions": {"orders": "avro:17"},
        "reference_versions": {"fx": "snapshot:2026-08-09-r2"},
    }
    print(json.dumps({"identity": dataset_identity(**arguments), "manifest": build_manifest(**arguments)}, indent=2))


if __name__ == "__main__":
    demo()
