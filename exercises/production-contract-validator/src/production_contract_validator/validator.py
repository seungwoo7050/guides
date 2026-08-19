from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


def _mapping(value: Any, label: str, errors: list[str]) -> dict[str, Any]:
    if not isinstance(value, dict):
        errors.append(f"{label} must be a mapping")
        return {}
    return value


def _nonempty(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


# [Implementation 1] YAML document input boundary
def load_contract(path: Path) -> tuple[dict[str, Any], list[str]]:
    try:
        document = yaml.safe_load(path.read_text(encoding="utf-8"))
    except OSError as exc:
        return {}, [f"cannot read contract: {exc}"]
    except yaml.YAMLError as exc:
        return {}, [f"invalid YAML: {exc}"]
    errors: list[str] = []
    root = _mapping(document, "document", errors)
    if root.get("schema_version") != 1:
        errors.append("schema_version must be 1")
    return root, errors


# [Implementation 2] Service and endpoint policy
def _validate_service_and_endpoints(root: dict[str, Any], errors: list[str]) -> None:
    service = _mapping(root.get("service"), "service", errors)
    for key in ("name", "user_capability", "owner"):
        if not _nonempty(service.get(key)):
            errors.append(f"service.{key} is required")
    capability = str(service.get("user_capability", "")).lower()
    if any(word in capability for word in ("docker", "nginx", "mariadb")):
        errors.append("service.user_capability must describe user value, not an implementation list")

    endpoints = _mapping(root.get("endpoints"), "endpoints", errors)
    public = endpoints.get("public")
    management = endpoints.get("management")
    if not isinstance(public, list) or not public:
        errors.append("endpoints.public must contain at least one endpoint")
        public = []
    if not isinstance(management, list) or not management:
        errors.append("endpoints.management must contain at least one endpoint")
        management = []

    public_ports: set[int] = set()
    for index, item in enumerate(public):
        endpoint = _mapping(item, f"endpoints.public[{index}]", errors)
        for key in ("name", "protocol", "owner"):
            if not _nonempty(endpoint.get(key)):
                errors.append(f"endpoints.public[{index}].{key} is required")
        port = endpoint.get("port")
        if not isinstance(port, int):
            errors.append(f"endpoints.public[{index}].port must be an integer")
        elif port not in {80, 443}:
            errors.append(f"unexpected public service port: {port}")
        else:
            public_ports.add(port)
    if 443 not in public_ports:
        errors.append("a public HTTPS endpoint on port 443 is required")

    for index, item in enumerate(management):
        endpoint = _mapping(item, f"endpoints.management[{index}]", errors)
        for key in ("name", "protocol", "source_restriction", "owner"):
            if not _nonempty(endpoint.get(key)):
                errors.append(f"endpoints.management[{index}].{key} is required")
        restriction = str(endpoint.get("source_restriction", "")).lower()
        if restriction in {"any", "public", "0.0.0.0/0", "::/0"}:
            errors.append("management endpoint source restriction is too broad")


# [Implementation 3] Recoverable data inventory policy
def _validate_data(root: dict[str, Any], errors: list[str]) -> None:
    entries = root.get("data")
    if not isinstance(entries, list) or len(entries) < 3:
        errors.append("data must cover business data, secrets, and configuration")
        entries = []
    classifications: set[str] = set()
    for index, item in enumerate(entries):
        entry = _mapping(item, f"data[{index}]", errors)
        for key in ("name", "classification", "source_of_truth", "recovery_source", "owner"):
            if not _nonempty(entry.get(key)):
                errors.append(f"data[{index}].{key} is required")
        classification = entry.get("classification")
        if isinstance(classification, str):
            classifications.add(classification)
        if entry.get("external_recovery_copy") is not True:
            errors.append(f"data[{index}] must identify an external recovery copy")
        rpo = entry.get("rpo_minutes")
        if not isinstance(rpo, int) or rpo < 0:
            errors.append(f"data[{index}].rpo_minutes must be a non-negative integer")
    if not {"business", "secret", "configuration"}.issubset(classifications):
        errors.append("data classifications must include business, secret, and configuration")


# [Implementation 4] Availability objective policy
def _validate_objectives(root: dict[str, Any], errors: list[str]) -> None:
    objectives = _mapping(root.get("objectives"), "objectives", errors)
    for key in ("rto_minutes", "rpo_minutes"):
        value = objectives.get(key)
        if not isinstance(value, int) or value <= 0:
            errors.append(f"objectives.{key} must be a positive integer")
    availability = _mapping(objectives.get("availability"), "objectives.availability", errors)
    path = availability.get("path")
    if not _nonempty(path) or path in {"/healthz", "/readyz"}:
        errors.append("availability.path must exercise a user-facing capability")
    location = str(availability.get("measurement_location", "")).lower()
    if not location or location in {"host", "localhost", "container"}:
        errors.append("availability.measurement_location must be an external probe")
    target = availability.get("target_percent")
    if not isinstance(target, (int, float)) or not 90 <= float(target) <= 100:
        errors.append("availability.target_percent must be between 90 and 100")
    window = availability.get("window_days")
    if not isinstance(window, int) or window <= 0:
        errors.append("availability.window_days must be a positive integer")


# [Implementation 5] Threat and residual risk policy
def _validate_threats(root: dict[str, Any], errors: list[str]) -> None:
    threat_model = _mapping(root.get("threat_model"), "threat_model", errors)
    boundaries = threat_model.get("trust_boundaries")
    if not isinstance(boundaries, list) or len(boundaries) < 4 or not all(_nonempty(item) for item in boundaries):
        errors.append("threat_model.trust_boundaries must contain at least four entries")
    risks = threat_model.get("risks")
    if not isinstance(risks, list) or len(risks) < 4:
        errors.append("threat_model.risks must contain at least four risks")
        risks = []
    identifiers: set[str] = set()
    for index, item in enumerate(risks):
        risk = _mapping(item, f"threat_model.risks[{index}]", errors)
        for key in ("id", "scenario", "prevention", "detection", "recovery", "owner"):
            if not _nonempty(risk.get(key)):
                errors.append(f"threat_model.risks[{index}].{key} is required")
        identifier = risk.get("id")
        if isinstance(identifier, str):
            if identifier in identifiers:
                errors.append(f"duplicate risk id: {identifier}")
            identifiers.add(identifier)

    residual = root.get("residual_risks")
    if not isinstance(residual, list) or not residual:
        errors.append("residual_risks must declare accepted residual risk")
        residual = []
    for index, item in enumerate(residual):
        risk = _mapping(item, f"residual_risks[{index}]", errors)
        for key in ("id", "statement", "accepted_by", "mitigation"):
            if not _nonempty(risk.get(key)):
                errors.append(f"residual_risks[{index}].{key} is required")
    if not any(
        isinstance(item, dict) and "single-host" in str(item.get("id", ""))
        for item in residual
    ):
        errors.append("single-host outage must be declared as a residual risk")


# [Implementation 6] Production readiness gate
def _validate_readiness(root: dict[str, Any], errors: list[str]) -> None:
    readiness = _mapping(root.get("readiness"), "readiness", errors)
    for key in (
        "immutable_release",
        "external_backup",
        "rollback_tested",
        "certificate_monitored",
        "restore_drill_tested",
    ):
        if readiness.get(key) is not True:
            errors.append(f"readiness.{key} must be true")


def validate_contract(path: Path) -> list[str]:
    root, errors = load_contract(path)
    if not root:
        return errors
    _validate_service_and_endpoints(root, errors)
    _validate_data(root, errors)
    _validate_objectives(root, errors)
    _validate_threats(root, errors)
    _validate_readiness(root, errors)
    return errors
