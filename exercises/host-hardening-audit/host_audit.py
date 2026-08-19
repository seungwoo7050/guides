#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

Finding = dict[str, str]


# [Implementation 1] Stable finding schema
def finding(
    finding_id: str,
    severity: str,
    evidence: str,
    remediation: str,
    safe_order: str,
) -> Finding:
    return {
        "id": finding_id,
        "severity": severity,
        "evidence": evidence,
        "remediation": remediation,
        "safe_order": safe_order,
    }


# [Implementation 2] Snapshot input boundary
def load_snapshot(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise ValueError(f"cannot read snapshot: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid JSON snapshot: {exc}") from exc
    if not isinstance(value, dict):
        raise ValueError("snapshot root must be an object")
    return value


# [Implementation 3] User role and shared key normalization
def audit(snapshot: dict[str, Any]) -> list[Finding]:
    findings: list[Finding] = []
    users = snapshot.get("users", [])
    if not isinstance(users, list):
        raise ValueError("users must be an array")
    roles = {
        str(user.get("name")): set(str(role) for role in user.get("roles", []))
        for user in users
        if isinstance(user, dict) and user.get("name")
    }
    key_owners: dict[str, list[str]] = defaultdict(list)
    for user in users:
        if not isinstance(user, dict):
            continue
        for fingerprint in user.get("ssh_key_fingerprints", []):
            key_owners[str(fingerprint)].append(str(user.get("name", "unknown")))
    shared = {key: owners for key, owners in key_owners.items() if len(owners) > 1}
    if shared:
        findings.append(
            finding(
                "shared-admin-key",
                "high",
                json.dumps(shared, sort_keys=True),
                "Issue a distinct SSH key to every operator and revoke shared keys.",
                "Verify a separate session with each replacement key before revocation.",
            )
        )

    # [Implementation 4] SSH access boundary
    ssh = snapshot.get("ssh", {})
    if not isinstance(ssh, dict):
        raise ValueError("ssh must be an object")
    if ssh.get("password_authentication") is True:
        findings.append(
            finding(
                "ssh-password-authentication",
                "high",
                "password_authentication=true",
                "Disable password authentication after verified public-key access exists.",
                "Open and verify a second key-authenticated administrator session first.",
            )
        )
    if str(ssh.get("permit_root_login", "")).lower() not in {"no", "prohibit-password"}:
        findings.append(
            finding(
                "ssh-root-login",
                "high",
                f"permit_root_login={ssh.get('permit_root_login')}",
                "Use a dedicated sudo administrator and restrict direct root login.",
                "Verify sudo and provider-console access before restricting root login.",
            )
        )
    if str(ssh.get("source_restriction", "")).lower() in {"0.0.0.0/0", "::/0", "any", "public"}:
        findings.append(
            finding(
                "unrestricted-ssh-source",
                "high",
                f"source_restriction={ssh.get('source_restriction')}",
                "Restrict SSH to an administrator CIDR, VPN, or provider firewall rule.",
                "Confirm the current administrator address and emergency console first.",
            )
        )

    # [Implementation 5] Docker control plane boundary
    docker = snapshot.get("docker", {})
    if not isinstance(docker, dict):
        raise ValueError("docker must be an object")
    remote = [str(item) for item in docker.get("remote_listeners", [])]
    unsafe_remote = [item for item in remote if item.startswith("tcp://")]
    if unsafe_remote:
        findings.append(
            finding(
                "unprotected-docker-tcp",
                "critical",
                ", ".join(unsafe_remote),
                "Remove unprotected TCP listeners and use SSH or mutual TLS administration.",
                "Verify the replacement management path and freeze deployments first.",
            )
        )
    consumers = [str(item) for item in docker.get("socket_mount_consumers", [])]
    if consumers:
        findings.append(
            finding(
                "docker-socket-mounted",
                "critical",
                ", ".join(consumers),
                "Remove Docker socket mounts from application containers.",
                "Replace required behavior with a narrow API before removing the mount.",
            )
        )
    non_admin_members = [
        str(name)
        for name in docker.get("group_members", [])
        if "administrator" not in roles.get(str(name), set())
    ]
    if non_admin_members:
        findings.append(
            finding(
                "non-admin-docker-group",
                "critical",
                ", ".join(non_admin_members),
                "Limit docker group membership to accounts trusted as host administrators.",
                "Identify owned automation and provide a replacement execution path first.",
            )
        )

    # [Implementation 6] Network, time, and storage recovery boundary
    network = snapshot.get("network", {})
    if not isinstance(network, dict):
        raise ValueError("network must be an object")
    try:
        ports = {int(port) for port in network.get("public_tcp_ports", [])}
    except (TypeError, ValueError) as exc:
        raise ValueError("network.public_tcp_ports must contain integers") from exc
    unexpected = sorted(ports - {22, 80, 443})
    if unexpected:
        findings.append(
            finding(
                "unexpected-public-service-port",
                "high",
                ",".join(str(port) for port in unexpected),
                "Move databases and management services to loopback or a private network.",
                "Verify all internal consumers before removing public publication.",
            )
        )
    if network.get("ipv6_enabled") is True and network.get("ipv6_firewall_reviewed") is not True:
        findings.append(
            finding(
                "ipv6-firewall-unreviewed",
                "high",
                "ipv6_enabled=true, ipv6_firewall_reviewed=false",
                "Review IPv6 listeners, DNS records, and firewall policy with the IPv4 baseline.",
                "Measure external IPv6 reachability before changing records or firewall rules.",
            )
        )

    time_state = snapshot.get("time", {})
    if not isinstance(time_state, dict):
        raise ValueError("time must be an object")
    if time_state.get("synchronized") is not True:
        findings.append(
            finding(
                "time-not-synchronized",
                "medium",
                "time.synchronized=false",
                "Restore time synchronization and alert on clock drift.",
                "Measure current drift and assess TLS, database, and log impact before correction.",
            )
        )

    storage = snapshot.get("storage", {})
    if not isinstance(storage, dict):
        raise ValueError("storage must be an object")
    threshold = storage.get("disk_alert_percent")
    if not isinstance(threshold, (int, float)) or not 1 <= float(threshold) < 100:
        findings.append(
            finding(
                "disk-alert-missing",
                "medium",
                f"disk_alert_percent={threshold}",
                "Configure byte and inode trend alerts with an actionable threshold.",
                "Measure current usage and growth rate before choosing the threshold.",
            )
        )
    locations = [str(item) for item in storage.get("backup_locations", [])]
    if not locations or all(item.startswith("/") or item.startswith("file:") for item in locations):
        findings.append(
            finding(
                "backup-local-only",
                "critical",
                ", ".join(locations) if locations else "no backup location",
                "Replicate encrypted backups to storage outside the host trust boundary.",
                "Verify restore and decryption-key access before promoting the external copy.",
            )
        )

    return sorted(findings, key=lambda item: item["id"])


# [Implementation 7] Deterministic JSON CLI projection
def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Audit a declarative Linux host snapshot.")
    parser.add_argument("snapshot", type=Path)
    parser.add_argument("--fail-on-findings", action="store_true")
    args = parser.parse_args(argv)
    try:
        findings = audit(load_snapshot(args.snapshot))
    except ValueError as exc:
        parser.error(str(exc))
    print(json.dumps({"findings": findings}, indent=2, sort_keys=True))
    return 1 if args.fail_on_findings and findings else 0


if __name__ == "__main__":
    raise SystemExit(main())
