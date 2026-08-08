# 컴퓨터 네트워크 학습 로드맵

이 문서는 가이드의 대상, 선행 개념, 학습 경로, 실습 대응과 종료 능력을 고정합니다. 네트워크를 장비 명령 모음으로 외우기보다 한 요청이 지나가는 경계, 각 경계의 상태와 실패 증거를 모델링하는 것이 목표입니다.

## 대상 독자

다음 독자를 대상으로 합니다.

- 하나 이상의 프로그래밍 언어로 작은 프로그램을 실행해 본 사람
- 터미널에서 디렉터리를 이동하고 명령의 표준 출력과 종료 상태를 확인할 수 있는 사람
- 웹, 서버, 인프라 또는 시스템 프로젝트에서 네트워크 오류를 계층별로 구분하려는 사람
- 패킷, 경로 표와 상태 전이를 코드와 fixture로 검증하려는 사람

소켓 API를 처음 구현하는 과정은 아닙니다. `socket`, `bind`, `connect`, `accept`, 부분 입출력과 파일 디스크립터 수명은 C 또는 C++ 가이드에서 먼저 다룰 수 있습니다. Python 실습 코드는 Python 3.12 이상의 표준 라이브러리만 사용하며 문법이 낯설다면 Python 가이드의 파일·CLI·테스트 기초를 먼저 확인합니다.

## 선행지식과 지원 환경

터미널에서 명령을 실행하고 종료 상태·표준 출력·표준 오류를 구분하며, 작은 Python 프로그램의 조건문과 반복문을 읽을 수 있어야 합니다. 전체 검증 환경은 Git, Make, Python 3.12 이상과 실행 중인 Docker Desktop 또는 Linux Docker daemon을 요구합니다. `verify.sh`는 digest로 고정한 Linux 이미지를 `--pull=never --privileged`로 실행하므로 daemon 접근과 privileged container 실행이 모두 필수이며 어떤 검사도 skip하지 않습니다.

## 완료 뒤 할 수 있어야 하는 일

가이드를 마치면 다음 능력을 갖추어야 합니다.

1. 애플리케이션 데이터가 링크 프레임까지 캡슐화되고 라우터에서 어떤 값이 바뀌는지 설명합니다.
2. IP 목적지와 Ethernet 다음 홉을 구분하고, 최장 프리픽스 일치로 경로를 선택합니다.
3. MTU·ICMP·NAT·연결 추적·방화벽의 서로 다른 책임과 실패 신호를 구분합니다.
4. UDP 데이터그램과 TCP 바이트 스트림의 계약을 기준으로 전송 선택을 설명합니다.
5. TCP 상태, 순서 번호, 누적 ACK, RTO, `rwnd`와 `cwnd`를 하나의 송신 상태로 추적합니다.
6. DNS, 경로, 이웃, MTU, 전송, TLS와 HTTP 단계에서 마지막 성공과 첫 실패를 결정합니다.
7. 결정적 모델의 결과와 실제 캡처·네임스페이스 실험의 관찰 범위를 구분합니다.

## 이 저장소가 소유하는 범위

이 저장소는 다음 개념의 주 설명을 소유합니다.

```text
Ethernet과 링크 계층 전달
ARP와 IPv6 Neighbor Discovery
IP 주소·프리픽스·전달·MTU·ICMP
NAT·연결 추적·방화벽의 관계
라우팅 데이터 평면과 제어 평면
UDP와 TCP의 전송 계약
TCP 상태·재전송·흐름 제어·혼잡 제어
DNS·TLS·QUIC의 네트워크 연결 경계
패킷과 계층별 증거를 이용한 장애 분리
```

다음 주제는 필요한 연결 설명만 제공하고 다른 가이드가 더 깊게 소유합니다.

| 영역 | 이 가이드의 경계 | 더 깊은 소유자 |
|---|---|---|
| 소켓 구현 | 전송 계약과 관찰 가능한 실패를 설명합니다. | C·C++ 가이드 |
| HTTP 애플리케이션 | 전송 버전과 프로토콜 의미의 경계를 설명합니다. | 웹 애플리케이션 가이드 |
| 인증·인가 | TLS 인증과 애플리케이션 권한을 구분합니다. | 웹 애플리케이션·Spring 가이드 |
| DNS·TLS 운영 | 프로토콜 동작과 실패 증거를 설명합니다. | 웹 인프라 가이드 |
| 재시도·멱등성 | 네트워크가 결과를 확정하지 못하는 상황을 설명합니다. | 분산 서비스 가이드 |
| 사용자 공간 진단 | 패킷과 경로의 네트워크 의미를 설명합니다. | Unix 시스템 가이드 |

## 필수·선택 학습 경로

Part I–IV와 다섯 실습은 **필수 경로**입니다. 이미 특정 계층을 알고 있다면 장애 분석 목적에 맞춰 `protocol-inspector → path-diagnosis` 또는 전송 상태 목적에 맞춰 `window-model → packet-observation`을 먼저 보는 **선택 경로**를 사용할 수 있지만, 가이드 완료를 주장하려면 필수 경로와 privileged Linux 실습을 모두 완료해야 합니다.

### Part I. 링크와 종단 경로

1. [계층, 캡슐화와 종단 경로](01-link-and-path/01-layers-encapsulation-and-path.md)
2. [Ethernet, MAC 주소와 스위칭](01-link-and-path/02-ethernet-mac-and-switching.md)
3. [ARP와 IPv6 Neighbor Discovery](01-link-and-path/03-arp-and-neighbor-discovery.md)

이 Part를 마치면 원격 목적지의 MAC 주소가 아니라 현재 링크의 다음 홉 주소를 해석하는 이유를 설명할 수 있어야 합니다.

### Part II. 인터넷 계층과 경로

1. [IP 주소, subnet과 라우팅 조회](02-internetworking/01-ip-addressing-subnets-and-lpm.md)
2. [IP 전달, MTU와 ICMP](02-internetworking/02-ip-forwarding-mtu-and-icmp.md)
3. [NAT, 연결 추적과 방화벽](02-internetworking/03-nat-connection-tracking-and-firewalls.md)
4. [라우팅 알고리즘과 프로토콜](02-internetworking/04-routing-algorithms-and-protocols.md)

이 Part를 마치면 경로 학습, 경로 선택, 실제 전달, 주소 변환과 정책 판정을 서로 다른 상태로 기록할 수 있어야 합니다.

### Part III. 전송 상태와 손실 복구

1. [UDP와 TCP의 서비스 계약](03-transport/01-udp-and-tcp-service-contracts.md)
2. [TCP 연결 상태와 순서 번호](03-transport/02-tcp-connection-state-and-sequences.md)
3. [재전송, RTT와 슬라이딩 윈도](03-transport/03-retransmission-rtt-and-sliding-windows.md)
4. [흐름 제어와 혼잡 제어](03-transport/04-flow-and-congestion-control.md)

이 Part를 마치면 연결 수립 성공, 바이트 전달 성공과 애플리케이션 처리 성공을 같은 사건으로 취급하지 않아야 합니다.

### Part IV. 응용 연결과 장애 증거

1. [DNS, HTTP, TLS와 QUIC](04-application-security-and-evidence/01-dns-http-tls-and-quic.md)
2. [계층별 네트워크 장애 분리](04-application-security-and-evidence/02-network-failure-localization.md)
3. [컴퓨터 네트워크 표준 지도](90-standards-map.md)

이 Part를 마치면 한 요청의 증거를 시간·위치·계층별로 정리하고, 변경 전에 반증 가능한 가설과 되돌리기 방법을 작성할 수 있어야 합니다.

## 문서와 실습의 대응

| 학습 구간 | 실행 자료 | 확인하는 계약 |
|---|---|---|
| 계층·Ethernet·IP·LPM·TCP 상태 | [프로토콜 검사기](../exercises/protocol-inspector/README.md) | 길이 경계, 체크섬, 캡슐화, 경로 선택, 상태 전이 |
| RTT·재전송·흐름·혼잡 제어 | [송신 창 모델](../examples/window-model/README.md) | `send_base`, `in_flight`, RTO, `rwnd`, `cwnd` |
| TCP 패킷 증거 | [패킷 관찰](../exercises/packet-observation/README.md) | 핸드셰이크, 순서 번호, 재전송 후보 |
| 실제 경로·NAT·손실 | [Linux 라우팅·NAT·손실](../exercises/linux-routing-nat/README.md) | TTL, 기본 경로, SNAT, 실제 SYN 재전송 |
| 전체 계층 통합 | [경로 진단](../exercises/path-diagnosis/README.md) | 마지막 성공, 첫 실패, 증거와 다음 검사 |

권장 순서는 `protocol-inspector → window-model → packet-observation → linux-routing-nat → path-diagnosis`입니다. Docker privileged 환경을 아직 준비하지 못했다면 결정적 fixture를 먼저 학습할 수는 있지만, 네임스페이스 실험과 full verify를 실행하기 전에는 이 가이드의 완료 기준을 충족한 것이 아닙니다.

## 학습자 구현과 reference 사용 규칙

`protocol-inspector`와 `path-diagnosis`는 다음 순서로 사용합니다.

```text
문제 계약과 fixture 확인
→ 결과를 손으로 예상
→ skeleton에서 구현
→ 공개 검사 실행
→ 실패 원인 기록
→ 모든 검사 통과
→ reference와 책임 배치 비교
```

reference를 먼저 복사하면 결과는 얻어도 경계 검사와 상태 모델을 설계하는 능력은 남지 않습니다. `scripts/new-workspace.sh`는 기존 workspace를 덮어쓰지 않고 skeleton의 추적 파일만 복사합니다.

## 검증 명령

최종 저장소를 준비하고 전체 휴대 가능 검사를 실행합니다.

```sh
./prepare.sh
./verify.sh
```

세부 검사가 필요하면 다음 명령을 사용할 수 있습니다.

```sh
make docs-check
make EXERCISE_IMPL=reference protocol-check
make PATH_EXERCISE_IMPL=reference path-diagnosis-check
make skeleton-check
make test-quality-check
make window-check
make observation-check
```

고정 검증 container 안에서는 다음 target이 privileged Linux 실험을 실행합니다. 호스트에서 직접 실행하지 않습니다.

```sh
make docker-e2e
```

정본 `./verify.sh`는 이 target을 digest로 고정한 로컬 이미지에서 필수로 실행하며 환경 부족을 skip으로 처리하지 않습니다.

## 범위 밖 항목

다음은 이 가이드의 완료 조건이 아닙니다.

- 운영용 Ethernet·IPv4·IPv6·TCP 전체 스택 구현
- Wi-Fi PHY와 무선 매체 제어의 상세 구현
- 멀티캐스트 라우팅 데몬과 BGP 운영 정책 전체
- 방화벽 제품별 관리 문법과 클라우드 네트워크 제품 설정
- 애플리케이션 인증·인가·업무 멱등성의 전체 설계
- 실제 공인 DNS·ACME·로드 밸런서 배포

범위 밖 항목을 얕게 추가하기보다 현재 경로의 상태와 실패 조건을 정확히 검증하는 것을 우선합니다.

## 완료 기준

- 다섯 실행 자료의 README에 지정된 관찰 증거를 남기고 reference 결과와 직접 비교합니다.
- `prepare.sh`가 고정 verifier image를 준비한 뒤 `verify.sh`가 `failed=0`, `skipped=0`으로 종료하며 privileged routing·NAT·100% loss 실험을 모두 통과합니다.
- 새로운 장애 사례에서 마지막 성공·첫 실패·반증 명령·수정 뒤 회귀 결과를 계층별로 기록합니다.

## 자동 검증의 한계

자동 검사는 고정 fixture와 격리된 Linux namespace에서 라우팅·NAT·손실 상태를 재현하지만 실제 Wi-Fi, 공인 인터넷 경로, 운영 방화벽, TLS 인증기관과 BGP 정책 전체를 증명하지 않습니다. 통과 결과는 관찰 모델의 증거이며 운영 환경의 시간·위치·권한·캡처 조건을 별도로 기록해야 합니다.
