"""계층별 증거에서 첫 실패와 구체적인 진단을 도출합니다."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Mapping

from .model import StageEvidence, Trace


# [Implementation 2] 자동화 출력과 사람의 조사 기록이 공유할 진단 결과 계약을 고정합니다.
@dataclass(frozen=True)
class Diagnosis:
    """자동화와 사람이 함께 사용할 수 있는 진단 결과입니다."""

    code: str
    layer: str | None
    last_success: str | None
    first_failure: str | None
    summary: str
    evidence: tuple[str, ...]
    next_checks: tuple[str, ...]

    @property
    def healthy(self) -> bool:
        return self.code == "HEALTHY"

    def to_mapping(self) -> dict[str, object]:
        return {
            "code": self.code,
            "healthy": self.healthy,
            "layer": self.layer,
            "last_success": self.last_success,
            "first_failure": self.first_failure,
            "summary": self.summary,
            "evidence": list(self.evidence),
            "next_checks": list(self.next_checks),
        }


Classifier = Callable[[StageEvidence], tuple[str, str, tuple[str, ...]]]


# [Implementation 2-1] 첫 실패와 마지막 성공을 고정한 뒤 해당 계층 classifier에 위임합니다.
def diagnose(trace: Trace) -> Diagnosis:
    """첫 실패 단계와 facts를 조합해 진단 코드를 선택합니다."""

    failure = trace.first_failure
    if failure is None:
        return Diagnosis(
            code="HEALTHY",
            layer=None,
            last_success=trace.stages[-1].stage,
            first_failure=None,
            summary="기록된 모든 계층이 성공했습니다.",
            evidence=tuple(stage.observation for stage in trace.stages),
            next_checks=(
                "요청 지연과 결과가 실제 기대 계약을 만족하는지 확인합니다.",
                "문제가 간헐적이면 실패 시점의 같은 계층 증거를 다시 수집합니다.",
            ),
        )

    classifiers: dict[str, Classifier] = {
        "dns": _classify_dns,
        "route": _classify_route,
        "neighbor": _classify_neighbor,
        "path": _classify_path,
        "transport": _classify_transport,
        "tls": _classify_tls,
        "http": _classify_http,
    }
    code, summary, next_checks = classifiers[failure.stage](failure)
    last_success = trace.last_success
    evidence = _evidence_lines(failure)
    return Diagnosis(
        code=code,
        layer=failure.stage,
        last_success=last_success.stage if last_success else None,
        first_failure=failure.stage,
        summary=summary,
        evidence=evidence,
        next_checks=next_checks,
    )


# [Implementation 2-2] machine 결과와 같은 경계를 안정적인 text 표현으로 변환합니다.
def render_text(diagnosis: Diagnosis) -> str:
    """진단을 사람이 읽는 안정적인 텍스트 형식으로 출력합니다."""

    lines = [
        f"code: {diagnosis.code}",
        f"healthy: {'yes' if diagnosis.healthy else 'no'}",
        f"last_success: {diagnosis.last_success or '-'}",
        f"first_failure: {diagnosis.first_failure or '-'}",
        f"summary: {diagnosis.summary}",
        "evidence:",
    ]
    lines.extend(f"- {item}" for item in diagnosis.evidence)
    lines.append("next_checks:")
    lines.extend(f"- {item}" for item in diagnosis.next_checks)
    return "\n".join(lines)


# [Implementation 2-3] 각 계층의 facts가 지지하는 범위까지만 구체적인 원인으로 분류합니다.
def _classify_dns(stage: StageEvidence) -> tuple[str, str, tuple[str, ...]]:
    rcode = _text(stage.facts, "rcode").upper()
    if rcode == "NXDOMAIN":
        return (
            "DNS_NAME_NOT_FOUND",
            "질의한 이름이 존재하지 않는다는 DNS 응답을 받았습니다.",
            (
                "질의한 이름과 검색 도메인 적용 결과를 확인합니다.",
                "권한 서버와 재귀 리졸버가 같은 NXDOMAIN을 반환하는지 비교합니다.",
                "부정 캐시 TTL이 지난 뒤 다시 확인합니다.",
            ),
        )
    return (
        "DNS_FAILURE",
        "주소 후보를 얻기 전에 DNS 단계가 실패했습니다.",
        (
            "사용한 리졸버와 실제 rcode를 확인합니다.",
            "timeout, SERVFAIL, 정책 차단과 잘못된 위임을 구분합니다.",
        ),
    )


def _classify_route(stage: StageEvidence) -> tuple[str, str, tuple[str, ...]]:
    selected = stage.facts.get("selected")
    error = _text(stage.facts, "error")
    if selected is False or error == "no-route":
        return (
            "NO_ROUTE",
            "목적지 주소에 사용할 로컬 경로를 선택하지 못했습니다.",
            (
                "실제 목적지에 대한 route lookup 결과를 확인합니다.",
                "정책 규칙, VPN, 네임스페이스와 출발지 주소 선택을 확인합니다.",
                "기본 경로가 아니라 목적지별 최종 선택 결과를 기록합니다.",
            ),
        )
    return (
        "ROUTE_FAILURE",
        "로컬 경로 선택 단계가 실패했습니다.",
        (
            "선택된 테이블, 프리픽스, 다음 홉과 출력 인터페이스를 확인합니다.",
            "경로는 있지만 인터페이스가 사용할 수 없는 상태인지 확인합니다.",
        ),
    )


def _classify_neighbor(stage: StageEvidence) -> tuple[str, str, tuple[str, ...]]:
    state = _text(stage.facts, "state").upper()
    if state in {"FAILED", "INCOMPLETE", "UNRESOLVED"}:
        return (
            "NEIGHBOR_UNRESOLVED",
            "경로가 선택한 다음 홉의 링크 계층 주소를 해석하지 못했습니다.",
            (
                "ARP Request 또는 Neighbor Solicitation이 실제로 나가는지 확인합니다.",
                "응답, VLAN, 링크 상태와 중복 주소를 확인합니다.",
                "원격 서버가 아니라 현재 링크의 다음 홉을 조사합니다.",
            ),
        )
    return (
        "NEIGHBOR_FAILURE",
        "현재 링크에서 다음 홉에 도달하기 전에 실패했습니다.",
        (
            "neighbor cache의 상태 전이와 인터페이스 오류 계수기를 확인합니다.",
            "스위치 포트, VLAN과 무선 격리 범위를 확인합니다.",
        ),
    )


def _classify_path(stage: StageEvidence) -> tuple[str, str, tuple[str, ...]]:
    small_ok = stage.facts.get("small_packet_ok") is True
    large_ok = stage.facts.get("large_packet_ok") is True
    too_big_seen = stage.facts.get("icmp_too_big_seen") is True
    if small_ok and not large_ok and not too_big_seen:
        return (
            "MTU_BLACK_HOLE",
            "작은 패킷은 통과하지만 큰 패킷이 필요한 ICMP 없이 사라집니다.",
            (
                "출력 인터페이스와 터널을 포함한 유효 MTU를 확인합니다.",
                "ICMP Packet Too Big 또는 fragmentation-needed 차단 여부를 확인합니다.",
                "페이로드 크기를 단계적으로 바꾸어 실패 경계를 재현합니다.",
            ),
        )
    return (
        "PATH_FAILURE",
        "로컬 이웃을 지난 뒤 종단 전송 전에 경로 전달이 실패했습니다.",
        (
            "홉별 TTL·Hop Limit, ICMP와 인터페이스 폐기 계수기를 확인합니다.",
            "작은 패킷과 큰 패킷, IPv4와 IPv6 결과를 분리합니다.",
        ),
    )


def _classify_transport(stage: StageEvidence) -> tuple[str, str, tuple[str, ...]]:
    if stage.facts.get("rst_received") is True:
        return (
            "CONNECTION_REFUSED",
            "대상 경로는 응답했지만 전송 종단점이 연결을 거부했습니다.",
            (
                "대상 주소와 포트에서 수신 프로세스가 대기 중인지 확인합니다.",
                "RST를 실제 종단점과 중간 정책 장비 중 누가 보냈는지 확인합니다.",
            ),
        )
    syn_sent = stage.facts.get("syn_sent")
    syn_ack = stage.facts.get("syn_ack_received")
    if isinstance(syn_sent, int) and not isinstance(syn_sent, bool) and syn_sent > 0 and syn_ack is False:
        return (
            "TRANSPORT_TIMEOUT",
            "전송 연결 요청을 보냈지만 제한 시간 안에 응답을 받지 못했습니다.",
            (
                "클라이언트와 서버 경계에서 같은 tuple의 SYN을 비교합니다.",
                "방화벽, 비대칭 경로, NAT 상태와 서버 수신 대기를 확인합니다.",
                "재전송 간격과 전체 애플리케이션 마감 시간을 구분합니다.",
            ),
        )
    return (
        "TRANSPORT_FAILURE",
        "전송 연결 또는 데이터그램 교환 단계가 실패했습니다.",
        (
            "TCP 플래그·순서 번호 또는 UDP 요청·응답 tuple을 확인합니다.",
            "EOF, RST, ICMP 오류와 단순 timeout을 구분합니다.",
        ),
    )


def _classify_tls(stage: StageEvidence) -> tuple[str, str, tuple[str, ...]]:
    if stage.facts.get("certificate_name_match") is False:
        return (
            "TLS_NAME_MISMATCH",
            "서버 인증서가 요청한 이름과 일치하지 않습니다.",
            (
                "클라이언트가 보낸 SNI와 요청 이름을 확인합니다.",
                "선택된 IP, 가상 호스트와 반환된 인증서의 SAN을 비교합니다.",
                "호스트 이름 검증을 우회하지 말고 DNS·프록시 구성을 수정합니다.",
            ),
        )
    return (
        "TLS_HANDSHAKE_FAILED",
        "전송 연결 뒤 TLS 협상 또는 인증이 실패했습니다.",
        (
            "TLS alert, 인증서 체인, 신뢰 저장소와 시스템 시간을 확인합니다.",
            "SNI, 지원 버전, cipher suite와 ALPN 협상을 확인합니다.",
        ),
    )


def _classify_http(stage: StageEvidence) -> tuple[str, str, tuple[str, ...]]:
    status = stage.facts.get("status")
    if status == 403:
        return (
            "HTTP_FORBIDDEN",
            "네트워크와 TLS는 성공했지만 HTTP 권한 검사에서 요청을 거부했습니다.",
            (
                "인증 성공 여부와 요청 주체의 권한을 분리해 확인합니다.",
                "프록시와 애플리케이션 중 어느 계층이 403을 생성했는지 확인합니다.",
                "네트워크 규칙 변경으로 애플리케이션 인가 실패를 우회하지 않습니다.",
            ),
        )
    if status == 401:
        return (
            "HTTP_UNAUTHORIZED",
            "HTTP 종단점에 도달했지만 유효한 인증 정보가 필요합니다.",
            (
                "인증 헤더, cookie와 세션 만료를 확인합니다.",
                "TLS 클라이언트 인증과 HTTP 애플리케이션 인증을 구분합니다.",
            ),
        )
    return (
        "HTTP_FAILURE",
        "HTTP 계층이 성공 응답 계약을 만족하지 못했습니다.",
        (
            "상태 코드, 리디렉션, 응답 생성 주체와 본문 프레이밍을 확인합니다.",
            "전송 성공과 업무 처리 성공을 별도로 기록합니다.",
        ),
    )


def _evidence_lines(stage: StageEvidence) -> tuple[str, ...]:
    facts = ", ".join(
        f"{key}={_display(value)}" for key, value in sorted(stage.facts.items())
    )
    if facts:
        return (stage.observation, facts)
    return (stage.observation,)


def _text(facts: Mapping[str, Any], key: str) -> str:
    value = facts.get(key)
    return value.strip() if isinstance(value, str) else ""


def _display(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if value is None:
        return "null"
    if isinstance(value, list):
        return "[" + ", ".join(_display(item) for item in value) + "]"
    return str(value)
