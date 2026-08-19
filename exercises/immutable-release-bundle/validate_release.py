#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
from pathlib import Path
from typing import Any

import yaml

IMAGE = re.compile(r"^[a-z0-9./_-]+@sha256:([0-9a-f]{64})$")
REVISION = re.compile(r"^[0-9a-f]{12,64}$")


def _mapping(value: Any, label: str, errors: list[str]) -> dict[str, Any]:
    if not isinstance(value, dict):
        errors.append(f"{label} must be a mapping")
        return {}
    return value


def _read_manifest(path: Path, errors: list[str]) -> dict[str, Any]:
    try:
        value = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        errors.append(f"cannot load release manifest: {exc}")
        return {}
    return _mapping(value, "release manifest", errors)


def _validate_dockerfile(path: Path, errors: list[str]) -> None:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        errors.append(f"cannot read Dockerfile: {exc}")
        return
    lowered = text.lower()
    base_match = re.search(r"^arg\s+base_image=([^\s]+)$", text, re.MULTILINE | re.IGNORECASE)
    if not base_match or ":" not in base_match.group(1) or base_match.group(1).endswith(":latest"):
        errors.append("Dockerfile BASE_IMAGE must have an explicit non-latest version")
    for label in (
        "org.opencontainers.image.source",
        "org.opencontainers.image.revision",
        "org.opencontainers.image.version",
        "org.opencontainers.image.created",
    ):
        if label not in text:
            errors.append(f"Dockerfile is missing OCI label: {label}")
    user_match = re.search(r"^user\s+(.+)$", text, re.MULTILINE | re.IGNORECASE)
    if not user_match or user_match.group(1).strip() in {"0", "root"}:
        errors.append("Dockerfile must select a non-root runtime user")
    if not re.search(r'^entrypoint\s+\["[^\"]+"', text, re.MULTILINE | re.IGNORECASE):
        errors.append("Dockerfile must use an exec-form ENTRYPOINT")
    if any(token in lowered for token in ("password=", "token=", "secret_value", "private_key=")):
        errors.append("Dockerfile appears to contain a secret value")


# [Implementation 7] Release bundle validation
def validate_bundle(root: Path) -> list[str]:
    errors: list[str] = []
    manifest = _read_manifest(root / "release.yaml", errors)
    _validate_dockerfile(root / "Dockerfile", errors)
    if not manifest:
        return errors
    if manifest.get("schema_version") != 1:
        errors.append("schema_version must be 1")
    for key in ("release_id", "created_at"):
        if not isinstance(manifest.get(key), str) or not manifest[key].strip():
            errors.append(f"{key} is required")
    revision = manifest.get("source_revision")
    if not isinstance(revision, str) or not REVISION.fullmatch(revision):
        errors.append("source_revision must be a 12-64 character hexadecimal revision")

    component = _mapping(manifest.get("component"), "component", errors)
    image = component.get("image")
    image_match = IMAGE.fullmatch(image) if isinstance(image, str) else None
    if not image_match:
        errors.append("component.image must be an exact sha256 digest reference")
        image_digest = ""
    else:
        image_digest = f"sha256:{image_match.group(1)}"
    if not isinstance(component.get("name"), str) or not component["name"].strip():
        errors.append("component.name is required")

    compatibility = _mapping(manifest.get("compatibility"), "compatibility", errors)
    database = _mapping(compatibility.get("database_schema"), "compatibility.database_schema", errors)
    minimum, maximum = database.get("min"), database.get("max")
    if not isinstance(minimum, int) or not isinstance(maximum, int) or minimum > maximum:
        errors.append("database compatibility range is invalid")
    if not isinstance(compatibility.get("configuration_schema"), int) or compatibility["configuration_schema"] <= 0:
        errors.append("configuration_schema must be a positive integer")

    secrets = _mapping(manifest.get("required_secrets"), "required_secrets", errors)
    if not secrets:
        errors.append("required_secrets must declare versioned secret names")
    for name, value in secrets.items():
        if not isinstance(name, str) or not isinstance(value, str) or not value.strip():
            errors.append("required_secrets entries must map names to version identifiers")
        if any(word in str(name).lower() for word in ("value", "password_value", "token_value")):
            errors.append("required_secrets may not contain secret values")

    rollback = _mapping(manifest.get("rollback"), "rollback", errors)
    rollback_image = rollback.get("image")
    if not isinstance(rollback_image, str) or not IMAGE.fullmatch(rollback_image):
        errors.append("rollback.image must be an exact sha256 digest reference")
    rollback_database = _mapping(rollback.get("database_schema"), "rollback.database_schema", errors)
    rollback_min, rollback_max = rollback_database.get("min"), rollback_database.get("max")
    if not isinstance(rollback_min, int) or not isinstance(rollback_max, int) or rollback_min > rollback_max:
        errors.append("rollback database compatibility range is invalid")
    elif isinstance(minimum, int) and isinstance(maximum, int) and max(minimum, rollback_min) > min(maximum, rollback_max):
        errors.append("release and rollback database compatibility ranges do not overlap")

    supply_chain = _mapping(manifest.get("supply_chain"), "supply_chain", errors)
    sbom = _mapping(supply_chain.get("sbom"), "supply_chain.sbom", errors)
    if sbom.get("generated") is not True or sbom.get("format") != "spdx-json":
        errors.append("SBOM must be generated in spdx-json format")
    if not image_digest or sbom.get("subject_digest") != image_digest:
        errors.append("SBOM subject digest must match the deployed image digest")
    provenance = _mapping(supply_chain.get("provenance"), "supply_chain.provenance", errors)
    if provenance.get("generated") is not True or provenance.get("verified_before_deploy") is not True:
        errors.append("provenance must be generated and verified before deployment")
    if provenance.get("source_revision") != revision:
        errors.append("provenance source revision must match release source_revision")
    if not isinstance(provenance.get("source_repository"), str) or not provenance["source_repository"].startswith("https://"):
        errors.append("provenance source_repository must be an HTTPS URL")

    registry = _mapping(manifest.get("registry"), "registry", errors)
    if registry.get("production_pull_scope") != "read-only":
        errors.append("production registry credentials must be read-only")
    if registry.get("immutable_tags") is not True:
        errors.append("registry immutable_tags must be true")
    if not isinstance(registry.get("retain_rollback_days"), int) or registry["retain_rollback_days"] <= 0:
        errors.append("registry retain_rollback_days must be positive")

    verification = _mapping(manifest.get("verification"), "verification", errors)
    smoke_paths = verification.get("smoke_paths")
    if not isinstance(smoke_paths, list) or not smoke_paths or not all(
        isinstance(path, str) and path.startswith("/") for path in smoke_paths
    ):
        errors.append("verification.smoke_paths must contain absolute HTTP paths")
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate an immutable release bundle.")
    parser.add_argument("root", nargs="?", type=Path, default=Path("."))
    args = parser.parse_args(argv)
    errors = validate_bundle(args.root)
    if errors:
        print(f"invalid release bundle: {len(errors)} issue(s)")
        for error in errors:
            print(f"- {error}")
        return 1
    print(f"valid release bundle: {args.root.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
