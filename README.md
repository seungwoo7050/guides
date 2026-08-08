# 컴퓨터 네트워크 원리와 검증 가이드

애플리케이션이 이름을 주소로 바꾸고, 다음 홉을 선택하고, 프레임과 패킷을 전달하며, 전송 연결을 복구하고, 암호화된 응답을 받기까지의 경로를 설명합니다. 명령 사용법만 나열하지 않고 헤더, 상태 전이, 경로 선택, 손실 복구와 장애 증거를 작은 코드와 격리된 실험으로 검증합니다.

이 저장소의 주 소유 영역은 Ethernet, ARP·Neighbor Discovery, IP 전달과 라우팅, NAT·연결 추적, UDP·TCP, DNS·TLS·QUIC 및 계층별 장애 분리입니다. 소켓 API 구현은 C·C++ 가이드가, HTTP 애플리케이션 계약과 인증은 웹 애플리케이션 가이드가, 실제 DNS·TLS 배포와 방화벽 운영은 웹 인프라 가이드가 더 깊게 다룹니다.

## 준비와 전체 검증

Python 3.12 이상과 Docker daemon을 준비한 뒤 다음 두 명령을 순서대로 실행합니다.

```sh
./prepare.sh
./verify.sh
```

`prepare.sh`는 source와 Git index를 바꾸지 않고 Python·Docker를 확인하고, digest로 고정한 Python 3.12 기반 Linux 검증 이미지를 준비합니다. 준비 상태는 `.guide/computer-networks/prepared.json`에 source·index 지문과 실제 이미지 ID로 기록합니다. `verify.sh`는 저장소 밖 임시 복사본에서 문서·링크·Python·셸·기준 구현·skeleton·오답 거부 검사와 privileged Linux 실험을 실행합니다.

전체 검증의 Linux 라우팅·NAT·손실 실험은 필수이며 skip하지 않습니다. `verify.sh`는 준비 단계에서 만든 로컬 이미지 ID를 `--pull=never`로 실행하므로 검증 도중 이미지를 내려받지 않습니다. 수동 캡처로 만든 `capture.txt`와 학습자의 `workspace/`는 읽거나 삭제하지 않습니다.

## 준비 환경

휴대 가능한 본문 예제와 프로토콜 실습에는 Python 3.12 이상과 POSIX 셸, `make`가 필요합니다. 실제 패킷 캡처에는 `tcpdump`가 필요합니다. 전체 검증의 Linux 도구와 관리자 권한은 고정 Docker 이미지와 격리된 privileged container 안에서 제공합니다.

```sh
python3 --version
./prepare.sh
VERIFY_LOG=/tmp/guide-computer-networks-verify.log ./verify.sh
```

## 학습 구조

전체 대상, 선행 개념, 종료 능력과 선택 경로는 [학습 로드맵](docs/00-roadmap.md)에서 확인합니다.

### Part I. 링크와 종단 경로

1. [계층, 캡슐화와 종단 경로](docs/01-link-and-path/01-layers-encapsulation-and-path.md)
2. [Ethernet, MAC 주소와 스위칭](docs/01-link-and-path/02-ethernet-mac-and-switching.md)
3. [ARP와 IPv6 Neighbor Discovery](docs/01-link-and-path/03-arp-and-neighbor-discovery.md)

### Part II. 인터넷 계층과 경로

1. [IP 주소, subnet과 라우팅 조회](docs/02-internetworking/01-ip-addressing-subnets-and-lpm.md)
2. [IP 전달, MTU와 ICMP](docs/02-internetworking/02-ip-forwarding-mtu-and-icmp.md)
3. [NAT, 연결 추적과 방화벽](docs/02-internetworking/03-nat-connection-tracking-and-firewalls.md)
4. [라우팅 알고리즘과 프로토콜](docs/02-internetworking/04-routing-algorithms-and-protocols.md)

### Part III. 전송 상태와 손실 복구

1. [UDP와 TCP의 서비스 계약](docs/03-transport/01-udp-and-tcp-service-contracts.md)
2. [TCP 연결 상태와 순서 번호](docs/03-transport/02-tcp-connection-state-and-sequences.md)
3. [재전송, RTT와 슬라이딩 윈도](docs/03-transport/03-retransmission-rtt-and-sliding-windows.md)
4. [흐름 제어와 혼잡 제어](docs/03-transport/04-flow-and-congestion-control.md)

### Part IV. 응용 연결과 장애 증거

1. [DNS, HTTP, TLS와 QUIC](docs/04-application-security-and-evidence/01-dns-http-tls-and-quic.md)
2. [계층별 네트워크 장애 분리](docs/04-application-security-and-evidence/02-network-failure-localization.md)
3. [컴퓨터 네트워크 표준 지도](docs/90-standards-map.md)

## 실행 예제와 실습

- [프로토콜 검사기](exercises/protocol-inspector/README.md)는 인터넷 체크섬, Ethernet·IPv4·TCP 헤더, classic PCAP, 최장 프리픽스 일치와 TCP 상태 전이를 구현합니다.
- [송신 창 모델](examples/window-model/README.md)은 `rwnd`, `cwnd`, 비행 중 바이트와 누적 ACK의 관계를 결정적인 상태 모델로 확인합니다.
- [패킷 관찰](exercises/packet-observation/README.md)은 `tcpdump` 텍스트에서 3단계 핸드셰이크와 재전송 후보를 찾습니다.
- [Linux 라우팅·NAT·손실](exercises/linux-routing-nat/README.md)은 세 네임스페이스를 연결해 TTL 만료, SNAT와 실제 SYN 재전송을 재현합니다.
- [경로 진단](exercises/path-diagnosis/README.md)은 DNS부터 HTTP까지 수집한 증거에서 마지막 성공 계층과 첫 실패 계층을 결정합니다.

`protocol-inspector`와 `path-diagnosis`에는 같은 공개 계약을 공유하는 `skeleton`과 `reference`가 있습니다. 기준 결과를 손으로 예상한 뒤 skeleton을 구현하고, 통과한 뒤에만 reference와 비교합니다.

## 조사할 때 보는 자료

- [명령 참고](reference/command-reference.md)는 인터페이스, 라우팅, 소켓과 패킷 캡처 상태를 확인하는 명령을 운영체제별로 정리합니다.
- [용어집](reference/glossary.md)은 계층마다 같은 단어가 다른 뜻으로 쓰이는 경우를 구분합니다.
- [프로토콜 필드 참고](reference/protocol-field-reference.md)는 Ethernet, IPv4, TCP와 classic PCAP 필드의 크기와 해석 순서를 모았습니다.
- [네트워크 설계 점검표](reference/network-design-checklist.md)는 주소, 경로, 전송과 장애 관측 항목을 설계 검토에 사용할 수 있게 정리합니다.
- [안전한 실험 범위](reference/network-safety.md)는 패킷 캡처, 네임스페이스와 방화벽 명령을 실행하기 전에 확인할 권한과 복구 절차를 설명합니다.

## 범위와 종료 기준

이 자료는 운영용 패킷 분석기, 완전한 TCP 스택, 동적 라우팅 데몬이나 방화벽 관리 도구를 만드는 과정이 아닙니다. 완료 뒤 다음 작업을 근거와 함께 수행할 수 있어야 합니다.

1. 한 요청이 각 계층에서 사용하는 식별자와 변경되는 헤더를 추적합니다.
2. 목적지 주소에 선택된 경로와 현재 링크의 다음 홉을 구분합니다.
3. TCP 상태·순서 번호·ACK·재전송·흐름 제어·혼잡 제어를 서로 다른 상태로 설명합니다.
4. DNS, IP, 전송, TLS와 HTTP 성공 여부를 하나의 “연결 성공”으로 뭉치지 않습니다.
5. 증상에서 원인을 추측하지 않고 마지막 성공 지점과 첫 실패 지점을 증거로 좁힙니다.
6. 결정적 fixture와 격리된 Linux 실험의 보장 범위를 구분합니다.

표준은 개정될 수 있습니다. 본문과 표준이 다르면 [표준 지도](docs/90-standards-map.md)의 판본과 RFC Editor의 현재 상태를 함께 확인합니다.
