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
./verify.sh
```

`verify.sh`의 기본 로그 이름에는 시각과 process ID가 포함됩니다. 별도 `VERIFY_LOG`를 지정할 때도 저장소 밖의 실행별 고유 절대 경로를 사용합니다.

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

## 정본 학습 순서

문서를 한꺼번에 읽은 뒤 실습을 몰아서 하지 않습니다. 아래 순서로 관련 문서와 실행 자료를 교차하고, 두 구현 실습은 반드시 `workspace/`에서 진행합니다. `reference/` source는 자신의 workspace 검사가 모두 통과한 뒤에만 책임 배치를 비교합니다. 실행 자료에 `reference/`가 없으면 표에 적은 기대 증거가 완료 기준입니다.

| 순서 | 문서 | 관찰 예제 | 직접 수행 | 수정 위치 | 검증 | 완료 뒤 비교·다음 |
|---:|---|---|---|---|---|---|
| 0 | [학습 로드맵](docs/00-roadmap.md) | — | 필수 환경과 두 workspace 경계를 확인합니다. | — | `python3 scripts/preflight.py` | Part I로 진행합니다. |
| 1 | [계층·캡슐화](docs/01-link-and-path/01-layers-encapsulation-and-path.md), [Ethernet·스위칭](docs/01-link-and-path/02-ethernet-mac-and-switching.md) | — | [`protocol-inspector`](exercises/protocol-inspector/README.md) workspace를 만들고 읽기 전용 [`syn-frame.hex`](exercises/protocol-inspector/fixtures/syn-frame.hex)의 field offset을 손으로 예상합니다. | 아직 source를 수정하지 않음 | Ethernet, IPv4, TCP 시작 위치를 공개 field 계약과 수동 대조 | ARP·ND로 진행하며 checksum을 배우기 전 packet 구현을 시작하지 않습니다. |
| 2 | [ARP·Neighbor Discovery](docs/01-link-and-path/03-arp-and-neighbor-discovery.md) | — | [Linux 실습 §1](exercises/linux-routing-nat/README.md#1-라우팅과-ttl)의 topology에서 route 제거 전후 다음 홉 증거를 예상합니다. | 수정 없음—제공된 실험 | 실제 격리 실행은 순서 9의 `run-all.sh`와 마지막 `verify.sh` | 기대 증거를 기록하고 Part II로 진행합니다. |
| 3 | [IP 주소·subnet·LPM](docs/02-internetworking/01-ip-addressing-subnets-and-lpm.md) | — | 읽기 전용 [`routes.json`](exercises/protocol-inspector/fixtures/routes.json)에서 prefix·metric·입력 순서 결과를 먼저 계산합니다. | 아직 source를 수정하지 않음 | 예상 route를 실습 README의 공개 계약과 수동 대조 | checksum·packet 단계를 거친 뒤 순서 6에서 routing을 구현합니다. |
| 4 | [IP 전달·MTU·ICMP](docs/02-internetworking/02-ip-forwarding-mtu-and-icmp.md) | — | protocol의 checksum → packet 경계를 구현하고 [`mtu-black-hole.json`](exercises/path-diagnosis/fixtures/mtu-black-hole.json)의 작은 packet 성공·큰 packet 실패·ICMP 부재를 판정합니다. 이어서 protocol README의 classic PCAP 계약을 구현합니다. | protocol workspace의 `checksum.py`, `packet.py`, `pcap.py`; path fixture는 읽기 전용 | `cd exercises/protocol-inspector && PYTHONPATH=workspace python3 -m unittest tests.test_checksum tests.test_packet tests.test_pcap -v` | 세 module 검사 뒤 NAT로 진행하며 reference source는 아직 보지 않습니다. |
| 5 | [NAT·conntrack·firewall](docs/02-internetworking/03-nat-connection-tracking-and-firewalls.md) | — | [Linux 실습 §2](exercises/linux-routing-nat/README.md#2-snat와-역변환)에서 server가 볼 출발지와 응답 역변환을 예상합니다. | 수정 없음—제공된 실험 | 실제 격리 실행은 순서 9의 `run-all.sh`와 마지막 `verify.sh` | 주소 변환과 filter 허용을 구분해 기록합니다. |
| 6 | [라우팅 알고리즘·프로토콜](docs/02-internetworking/04-routing-algorithms-and-protocols.md) | — | routing 구현을 완성하고 [`route-missing.json`](exercises/path-diagnosis/fixtures/route-missing.json)의 마지막 성공·첫 실패를 판정합니다. | protocol workspace의 `routing.py`; path fixture는 읽기 전용 | `cd exercises/protocol-inspector && PYTHONPATH=workspace python3 -m unittest tests.test_routing -v` | route module만 검사하고 전송 계층으로 진행합니다. |
| 7 | [UDP·TCP 서비스 계약](docs/03-transport/01-udp-and-tcp-service-contracts.md) | [송신 창 모델](examples/window-model/README.md) | [`transport-timeout.json`](exercises/path-diagnosis/fixtures/transport-timeout.json)과 모델에서 timeout evidence, `rwnd`, `cwnd`의 소유자를 분리합니다. | 수정 없음—제공된 모델·fixture | `cd examples/window-model && python3 -m unittest test_window_model.WindowSenderTests -v` | 송신 창의 결정적 상태 전이를 기대 증거로 기록합니다. |
| 8 | [TCP 상태·순서 번호](docs/03-transport/02-tcp-connection-state-and-sequences.md) | [송신 창 모델](examples/window-model/README.md) | protocol TCP state와 마지막 CLI 조립을 완성하고 [packet observation](exercises/packet-observation/README.md)의 handshake fixture를 분석합니다. | protocol workspace의 `tcp_state.py`, `cli.py`; observation은 제공된 analyzer | `make protocol-check`; `cd exercises/packet-observation && python3 -m unittest tests.test_analyze_tcpdump.TcpdumpAnalyzerTests.test_complete_handshake_is_detected tests.test_analyze_tcpdump.TcpdumpAnalyzerTests.test_wrong_handshake_ack_is_rejected -v` | protocol 전체 통과 뒤에만 `reference/` 책임 배치를 비교하고 재전송으로 진행합니다. |
| 9 | [재전송·RTT·슬라이딩 윈도](docs/03-transport/03-retransmission-rtt-and-sliding-windows.md) | [송신 창 모델](examples/window-model/README.md) | 반복 SYN 후보를 분석하고 [Linux 실습](exercises/linux-routing-nat/README.md)의 §1–§3을 격리 환경에서 실행합니다. | 수정 없음—제공된 모델·실험 | `make window-check observation-check`; 지원 Linux에서는 `cd exercises/linux-routing-nat && sudo ./scripts/run-all.sh`, 최종은 `./verify.sh` | TTL·route 복구, SNAT, 반복 SYN, 손실 제거와 자원 정리 증거를 함께 남깁니다. |
| 10 | [흐름·혼잡 제어](docs/03-transport/04-flow-and-congestion-control.md) | [송신 창 모델](examples/window-model/README.md) | `rwnd`, `cwnd`, ACK, timeout 전이와 모델의 비보장 범위를 설명합니다. | 수정 없음—제공된 모델 | `make window-check` | 전체 model 회귀와 기대 증거를 마치고 Part IV로 진행합니다. |
| 11 | [DNS·HTTP·TLS·QUIC](docs/04-application-security-and-evidence/01-dns-http-tls-and-quic.md) | — | [`path-diagnosis`](exercises/path-diagnosis/README.md) workspace를 만들고 trace model과 단계별 diagnosis를 구현합니다. | path workspace의 `model.py`, `diagnose.py` | `cd exercises/path-diagnosis && PYTHONPATH=workspace python3 -m unittest tests.test_model tests.test_diagnose -v` | failure localization에서 CLI를 조립합니다. |
| 12 | [네트워크 장애 분리](docs/04-application-security-and-evidence/02-network-failure-localization.md) | — | CLI의 text·JSON·exit status를 완성해 마지막 성공·첫 실패·다음 검사를 통합합니다. | path workspace의 `cli.py` | `make path-diagnosis-check` | 전체 통과 뒤에만 path `reference/` 책임 배치를 비교합니다. |
| 13 | [표준 지도](docs/90-standards-map.md) | — | 표준 판본과 다섯 실행 자료의 수동 기대 증거를 모두 교차 점검합니다. | — | `./prepare.sh` 뒤 `./verify.sh` | 수동 증거가 완성되고 `failed=0`, `skipped=0`일 때만 필수 경로를 종료합니다. |

## 실행 예제와 실습

- [프로토콜 검사기](exercises/protocol-inspector/README.md)는 인터넷 체크섬, Ethernet·IPv4·TCP 헤더, classic PCAP, 최장 프리픽스 일치와 TCP 상태 전이를 구현합니다.
- [송신 창 모델](examples/window-model/README.md)은 `rwnd`, `cwnd`, 비행 중 바이트와 누적 ACK의 관계를 결정적인 상태 모델로 확인합니다.
- [패킷 관찰](exercises/packet-observation/README.md)은 `tcpdump` 텍스트에서 3단계 핸드셰이크와 재전송 후보를 찾습니다.
- [Linux 라우팅·NAT·손실](exercises/linux-routing-nat/README.md)은 세 네임스페이스를 연결해 TTL 만료, SNAT와 실제 SYN 재전송을 재현합니다.
- [경로 진단](exercises/path-diagnosis/README.md)은 DNS부터 HTTP까지 수집한 증거에서 마지막 성공 계층과 첫 실패 계층을 결정합니다.

`protocol-inspector`와 `path-diagnosis`에는 같은 공개 계약을 공유하는 `skeleton`과 `reference`가 있습니다. 저장소 루트에서 각각 `scripts/new-workspace.sh exercises/protocol-inspector`, `scripts/new-workspace.sh exercises/path-diagnosis`를 실행하고 생성된 `workspace/`만 수정합니다. `make protocol-check`와 `make path-diagnosis-check`의 기본 대상도 workspace이므로 workspace가 없으면 성공으로 오인하지 않고 실패합니다. 기준 결과를 손으로 예상하고 workspace 검사를 통과한 뒤에만 reference source와 비교합니다.

`window-model`, `packet-observation`, `linux-routing-nat`에는 답안 directory가 없습니다. 이 자료의 완료 증거는 각각 결정적 상태 전이와 단위 검사, handshake·재전송 후보 및 선택 캡처, TTL·SNAT·반복 SYN과 소유 자원 정리 결과입니다. 저장소 자체의 건강 상태를 검사하는 `make reference-check`와 `./verify.sh`는 학습자 workspace 대신 정본 자료를 명시적으로 검사합니다.

## 조사할 때 보는 자료

root의 `reference/`는 빠르게 찾아보는 보조 문서이며 exercise 답안이 아닙니다. 구현 비교물은 각 구현 exercise 안의 `reference/`에만 있습니다.

- [명령 참고](reference/command-reference.md)는 인터페이스, 라우팅, 소켓과 패킷 캡처 상태를 확인하는 명령을 운영체제별로 정리합니다.
- [용어집](reference/glossary.md)은 계층마다 같은 단어가 다른 뜻으로 쓰이는 경우를 구분합니다.
- [프로토콜 필드 참고](reference/protocol-field-reference.md)는 Ethernet, IPv4, TCP·UDP와 checksum pseudo-header의 크기와 해석 순서를 모았습니다. Classic PCAP의 지원 범위와 record 계약은 [프로토콜 검사기 README](exercises/protocol-inspector/README.md#13-체크섬-패킷과-pcap-경계)가 정본입니다.
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
