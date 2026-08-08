# 컴퓨터 네트워크 표준 지도

본문이 기준으로 삼은 IETF 문서와 registry를 계층별로 정리합니다. RFC는 후속 문서에 의해 갱신되거나 대체될 수 있으므로 구현 전에는 RFC Editor에서 현재 상태, 갱신·폐기 관계와 정오표를 다시 확인합니다. 이 지도는 2026년 8월 8일에 확인한 학습 기준선이며 표준 본문을 대체하지 않습니다.

## 이 지도를 사용하는 방법

표준 번호를 외우는 것이 목표는 아닙니다. 본문이나 패킷 관찰이 모호할 때 다음 순서로 사용합니다.

```text
관찰한 필드·상태·오류를 고정
→ 해당 프로토콜의 현재 기본 RFC 확인
→ Updates와 Obsoletes 관계 확인
→ 구현체가 협상한 옵션과 버전 확인
→ 학습 모델의 생략 범위와 비교
```

같은 이름의 프로토콜도 확장 옵션과 구현 버전에 따라 동작이 달라질 수 있습니다. 패킷 하나를 보고 표준 전체의 준수 여부를 단정하지 않습니다.

## 링크와 인터넷 계층

| 주제 | 기준 문서 |
|---|---|
| ARP | [RFC 826](https://www.rfc-editor.org/rfc/rfc826) |
| IPv4 router 요구사항 | [RFC 1812](https://www.rfc-editor.org/rfc/rfc1812) |
| IPv6 기본 규격 | [RFC 8200](https://www.rfc-editor.org/rfc/rfc8200) |
| IPv6 Neighbor Discovery | [RFC 4861](https://www.rfc-editor.org/rfc/rfc4861) |
| IPv6 Path MTU Discovery | [RFC 8201](https://www.rfc-editor.org/rfc/rfc8201) |
| Datagram PLPMTUD | [RFC 8899](https://www.rfc-editor.org/rfc/rfc8899) |
| ICMPv4 | [RFC 792](https://www.rfc-editor.org/rfc/rfc792)와 후속 update |
| ICMPv6 | [RFC 4443](https://www.rfc-editor.org/rfc/rfc4443) |
| 인터넷 체크섬 계산 | [RFC 1071](https://www.rfc-editor.org/rfc/rfc1071) |

IEEE 802.3과 802.1Q의 전체 표준은 IEEE가 관리합니다. EtherType, IP protocol number와 관련 할당값은 IANA registry의 현재 값을 확인합니다.

## NAT와 라우팅

| 주제 | 기준 문서 |
|---|---|
| UDP NAT 동작 요구 | [RFC 4787](https://www.rfc-editor.org/rfc/rfc4787) |
| TCP NAT 동작 요구 | [RFC 5382](https://www.rfc-editor.org/rfc/rfc5382) |
| Carrier-grade NAT 요구 | [RFC 6888](https://www.rfc-editor.org/rfc/rfc6888) |
| OSPFv2 | [RFC 2328](https://www.rfc-editor.org/rfc/rfc2328) |
| BGP-4 | [RFC 4271](https://www.rfc-editor.org/rfc/rfc4271)과 후속 update |

NAT mapping·filtering 이름과 traversal 동작은 여러 RFC에 나뉩니다. 한 표준의 권고를 모든 실제 장비의 현재 동작으로 일반화하지 않습니다. 라우팅 프로토콜도 기본 RFC와 별도로 보안, 확장 address family와 운영 정책 문서를 함께 확인해야 합니다.

## 전송 계층

| 주제 | 기준 문서 |
|---|---|
| UDP | [RFC 768](https://www.rfc-editor.org/rfc/rfc768)과 host 요구사항 update |
| TCP 기본 규격 | [RFC 9293](https://www.rfc-editor.org/rfc/rfc9293) |
| TCP congestion control 원칙 | [RFC 5681](https://www.rfc-editor.org/rfc/rfc5681) |
| TCP retransmission timer | [RFC 6298](https://www.rfc-editor.org/rfc/rfc6298) |
| TCP SACK | [RFC 2018](https://www.rfc-editor.org/rfc/rfc2018) |
| SACK 기반 loss recovery | [RFC 6675](https://www.rfc-editor.org/rfc/rfc6675) |
| CUBIC | [RFC 9438](https://www.rfc-editor.org/rfc/rfc9438) |
| QUIC transport | [RFC 9000](https://www.rfc-editor.org/rfc/rfc9000) |
| QUIC loss detection과 congestion control | [RFC 9002](https://www.rfc-editor.org/rfc/rfc9002) |

실제 TCP 구현은 ECN, timestamp, window scaling, pacing과 더 새로운 loss recovery 확장을 사용할 수 있습니다. 캡처를 해석할 때는 협상한 옵션, 운영체제와 congestion-control 구현을 함께 기록합니다.

## DNS, HTTP와 TLS

| 주제 | 기준 문서 |
|---|---|
| DNS 개념과 구현 | [RFC 1034](https://www.rfc-editor.org/rfc/rfc1034), [RFC 1035](https://www.rfc-editor.org/rfc/rfc1035)와 후속 update |
| DNS 용어 | [RFC 9499](https://www.rfc-editor.org/rfc/rfc9499) |
| SVCB와 HTTPS record | [RFC 9460](https://www.rfc-editor.org/rfc/rfc9460) |
| HTTP semantics | [RFC 9110](https://www.rfc-editor.org/rfc/rfc9110) |
| HTTP/1.1 | [RFC 9112](https://www.rfc-editor.org/rfc/rfc9112) |
| HTTP/2 | [RFC 9113](https://www.rfc-editor.org/rfc/rfc9113) |
| HTTP/3 | [RFC 9114](https://www.rfc-editor.org/rfc/rfc9114) |
| TLS 1.3 현재 기본 규격 | [RFC 9846](https://www.rfc-editor.org/rfc/rfc9846) |

RFC 9846은 2026년 7월에 발행되어 RFC 8446을 대체합니다. 기존 구현 문서가 RFC 8446을 참조하더라도 현재 변경점, 호환성과 정오표는 RFC 9846의 상태에서 다시 확인합니다.

## 현재 할당값을 확인할 registry

- [IANA Protocol Numbers](https://www.iana.org/assignments/protocol-numbers/protocol-numbers.xhtml)
- [IANA Service Name and Transport Protocol Port Number Registry](https://www.iana.org/assignments/service-names-port-numbers/service-names-port-numbers.xhtml)
- [IANA TLS Parameters](https://www.iana.org/assignments/tls-parameters/tls-parameters.xhtml)
- [IANA QUIC Registries](https://www.iana.org/assignments/quic/quic.xhtml)

registry 값을 코드에 복사한 뒤 영구 상수라고 가정하지 않습니다. 학습 구현은 지원하는 값의 범위를 명시하고, 알 수 없는 값은 잘못된 다른 프로토콜로 억지 해석하지 않아야 합니다.

## 학습 구현과 표준의 경계

이 저장소의 프로토콜 검사기와 상태 모델은 다음을 의도적으로 생략합니다.

- 운영용 parser가 요구하는 모든 Ethernet·IPv4·TCP 옵션과 확장 헤더
- TCP의 모든 예외 전이, timer와 현대 loss recovery
- 동적 라우팅 프로토콜의 wire format과 전체 수렴 절차
- TLS·QUIC 암호 구현과 인증서 검증기
- HTTP/2·HTTP/3 frame parser

따라서 검사 통과는 해당 RFC 전체를 구현했다는 증거가 아닙니다. 모델이 보장하는 필드, 상태와 실패 조건만 주장합니다.
