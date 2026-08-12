from __future__ import annotations

from collections import defaultdict
from typing import Any

Finding = dict[str, str]


# [Implementation 1] 모든 진단을 evidence·remediation·safe order가 있는 stable schema로 만듭니다.
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


# [Implementation 2] user role과 shared key를 먼저 정규화해 뒤 권한 판정의 기준으로 씁니다.
def audit(snapshot: dict[str, Any]) -> list[Finding]:
    findings: list[Finding] = []
    users = snapshot.get("users", [])
    roles = {
        user.get("name"): set(user.get("roles", []))
        for user in users
        if isinstance(user, dict)
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
                repr(shared),
                "운영자마다 별도 SSH key를 발급하고 공유 key를 폐기한다.",
                "새 key로 별도 세션 재접속을 확인한 뒤 공유 key를 제거한다.",
            )
        )

    # [Implementation 3] 대체 관리 경로를 먼저 요구하는 SSH 경계를 판정합니다.
    ssh = snapshot.get("ssh", {})
    if ssh.get("password_authentication") is True:
        findings.append(
            finding(
                "ssh-password-authentication",
                "high",
                "password_authentication=true",
                "검증된 공개키 인증 경로를 사용하고 password 인증을 비활성화한다.",
                "별도 관리자 세션에서 key 로그인을 확인한 뒤 설정을 제한한다.",
            )
        )
    if str(ssh.get("permit_root_login", "")).lower() not in {"no", "prohibit-password"}:
        findings.append(
            finding(
                "ssh-root-login",
                "high",
                f"permit_root_login={ssh.get('permit_root_login')}",
                "별도 sudo 관리자 계정을 사용하고 root 직접 로그인을 제한한다.",
                "sudo와 공급자 console 접근을 먼저 확인한 뒤 root 로그인을 제한한다.",
            )
        )
    if str(ssh.get("source_restriction", "")).lower() in {"0.0.0.0/0", "::/0", "any", "public"}:
        findings.append(
            finding(
                "unrestricted-ssh-source",
                "high",
                f"source_restriction={ssh.get('source_restriction')}",
                "공급자 firewall, VPN 또는 관리 CIDR로 SSH 출발지를 제한한다.",
                "현재 관리자 주소와 비상 console을 확인한 뒤 제한을 적용한다.",
            )
        )

    # [Implementation 4] Docker control plane 접근을 host root 권한과 같은 수준으로 다룹니다.
    docker = snapshot.get("docker", {})
    remote = [str(item) for item in docker.get("remote_listeners", [])]
    unsafe_remote = [item for item in remote if item.startswith("tcp://")]
    if unsafe_remote:
        findings.append(
            finding(
                "unprotected-docker-tcp",
                "critical",
                ", ".join(unsafe_remote),
                "공개 TCP listener를 제거하고 보호된 SSH 또는 상호 TLS 관리 경로를 사용한다.",
                "대체 관리 경로를 검증하고 실행 중 배포를 동결한 뒤 listener를 제거한다.",
            )
        )
    consumers = [str(item) for item in docker.get("socket_mount_consumers", [])]
    if consumers:
        findings.append(
            finding(
                "docker-socket-mounted",
                "critical",
                ", ".join(consumers),
                "애플리케이션 container의 Docker socket mount를 제거한다.",
                "소비 기능이 실제로 필요한 API를 식별하고 대체 경로를 준비한 뒤 mount를 제거한다.",
            )
        )
    non_admin_members = [
        str(name)
        for name in docker.get("group_members", [])
        if "administrator" not in roles.get(name, set())
    ]
    if non_admin_members:
        findings.append(
            finding(
                "non-admin-docker-group",
                "critical",
                ", ".join(non_admin_members),
                "docker 그룹을 관리자 신뢰 수준의 계정으로 제한한다.",
                "해당 계정이 소유한 자동화와 container를 확인하고 대체 실행 경로를 만든 뒤 제거한다.",
            )
        )

    # [Implementation 5] public network, time, storage와 외부 backup의 운영 경계를 검사합니다.
    network = snapshot.get("network", {})
    ports = {int(port) for port in network.get("public_tcp_ports", [])}
    unexpected = sorted(ports - {22, 80, 443})
    if unexpected:
        findings.append(
            finding(
                "unexpected-public-service-port",
                "high",
                ",".join(str(port) for port in unexpected),
                "DB와 관리 dashboard를 loopback, 내부 network 또는 관리망으로 제한한다.",
                "내부 소비자의 연결 경로를 먼저 검증한 뒤 public publish를 제거한다.",
            )
        )
    if network.get("ipv6_enabled") is True and network.get("ipv6_firewall_reviewed") is not True:
        findings.append(
            finding(
                "ipv6-firewall-unreviewed",
                "high",
                "ipv6_enabled=true, ipv6_firewall_reviewed=false",
                "AAAA, IPv6 listener와 firewall 정책을 IPv4와 같은 기준으로 검토한다.",
                "외부 IPv6 접근을 측정한 뒤 record 또는 firewall을 일관되게 수정한다.",
            )
        )

    if snapshot.get("time", {}).get("synchronized") is not True:
        findings.append(
            finding(
                "time-not-synchronized",
                "medium",
                "time.synchronized=false",
                "시간 동기화 서비스를 복구하고 drift 경보를 추가한다.",
                "현재 시각 차이를 확인하고 TLS·DB·로그에 미칠 영향을 평가한 뒤 교정한다.",
            )
        )

    storage = snapshot.get("storage", {})
    threshold = storage.get("disk_alert_percent")
    if not isinstance(threshold, (int, float)) or not 1 <= float(threshold) < 100:
        findings.append(
            finding(
                "disk-alert-missing",
                "medium",
                f"disk_alert_percent={threshold}",
                "disk byte와 inode의 추세·임계값 경보를 구성한다.",
                "현재 사용량과 증가율을 먼저 측정한 뒤 여유 있는 임계값을 정한다.",
            )
        )
    locations = [str(item) for item in storage.get("backup_locations", [])]
    if not locations or all(item.startswith("/") or item.startswith("file:") for item in locations):
        findings.append(
            finding(
                "backup-local-only",
                "critical",
                ", ".join(locations) if locations else "no backup location",
                "암호화 backup을 host와 권한 경계가 다른 외부 저장소로 전송한다.",
                "복원 시험과 복호화 key 접근을 확인한 뒤 외부 복사본을 정본으로 승격한다.",
            )
        )

    # [Implementation 6] 입력 순서와 무관한 ID 정렬로 audit evidence를 재현 가능하게 합니다.
    return sorted(findings, key=lambda item: item["id"])
