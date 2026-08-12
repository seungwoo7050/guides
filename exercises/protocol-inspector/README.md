# 프로토콜 검사기

패킷 분석기는 길이 필드 하나를 잘못 믿어도 다음 헤더를 엉뚱한 위치에서 읽습니다. 이 문제에서는 인터넷 체크섬, Ethernet·IPv4·TCP 헤더, classic PCAP 레코드, 최장 프리픽스 경로 선택과 TCP 상태 전이를 작은 기준 입력으로 구현합니다. 원시 소켓이나 외부 패키지는 사용하지 않습니다.

## 목표

신뢰하지 않는 packet byte와 route·event 입력을 경계부터 검증하고, 지원하지 않는 형식은 다른 protocol로 오해하지 않는 작은 검사기를 구현합니다.

```text
skeleton/protocol_inspector/   수정하지 않는 미완성 시작점과 공개 함수·타입
workspace/protocol_inspector/  생성 뒤 학습자가 수정하는 유일한 구현
reference/protocol_inspector/  기준 구현
tests/                          두 구현에 공통으로 적용하는 동작 검사
fixtures/                       SYN 프레임과 경로 표
tools/                          기준 입력 생성기
```

## 권장 구현 순서

아래 번호는 `reference/protocol_inspector/` 프로젝트 전체의 학습 지향 권장 구현 순서입니다. 파일의 줄 순서나 실제 과거 작성 순서를 뜻하지 않습니다. 학습자는 같은 책임을 `workspace/`에 직접 설계하고, 모든 검사가 통과한 뒤 이 index와 reference source의 annotation을 비교합니다.

| 번호 | 파일·symbol | 먼저 고정하는 책임 |
|---:|---|---|
| 1 | `checksum.py::internet_checksum` | 16비트 word, 홀수 길이 padding과 end-around carry |
| 1-1 | `checksum.py::tcp_checksum_ipv4` | IPv4 pseudo-header와 TCP 길이 경계 |
| 2 | `packet.py::parse_ethernet` | 최소 frame 길이, VLAN offset과 EtherType |
| 2-1 | `packet.py::parse_ipv4` | version, IHL, total length와 header checksum |
| 2-2 | `packet.py::parse_tcp` | data offset, flags, option·payload와 checksum 조건 |
| 2-3 | `packet.py::decode_ethernet_ipv4_tcp` | 상위 protocol과 fragment 여부에 따른 조립 경계 |
| 3 | `pcap.py::parse_pcap` | byte order, timestamp 해상도와 record 길이 |
| 4 | `routing.py::Route` | route 입력을 검증된 network·next-hop 상태로 변환 |
| 4-1 | `routing.py::RoutingTable.lookup` | prefix, metric, 입력 순서의 선택 우선순위 |
| 5 | `tcp_state.py::_TRANSITIONS` | state/event가 공유하는 정상 전이 표 |
| 5-1 | `tcp_state.py::TCPEndpoint.apply` | RST 예외, invalid transition과 state 소유권 |
| 6 | `cli.py::command_*` | domain 결과를 안정적인 CLI 출력과 상태로 변환 |
| 6-1 | `cli.py::build_parser`, `main` | 하위 명령 계약과 최종 adapter 조립 |

먼저 저장소 루트에서 workspace를 한 번 만듭니다. 기존 workspace는 덮어쓰지 않습니다.

```sh
scripts/new-workspace.sh exercises/protocol-inspector
```

## 1–3. 체크섬, 패킷과 PCAP 경계

인터넷 체크섬은 홀수 길이 입력의 오른쪽을 0으로 채운 뒤 16비트 큰 엔디언 단위로 더합니다. TCP 체크섬에는 IPv4 의사 헤더가 포함됩니다.

패킷 파서는 최소 헤더 길이, 헤더가 선언한 길이와 실제 입력 길이를 순서대로 검사합니다. 조각난 IPv4 데이터는 완전한 TCP 세그먼트로 해석하지 않습니다.

```sh
cd exercises/protocol-inspector
PYTHONPATH=workspace python3 -m unittest tests.test_checksum tests.test_packet -v
```

기준 프레임은 `192.0.2.10:49152`에서 `198.51.100.20:443`으로 향하는 SYN입니다. IPv4·TCP 체크섬과 MSS 1460 옵션이 모두 일치해야 합니다.

`pcap.py`는 classic PCAP 2.4의 큰 엔디언·작은 엔디언 및 마이크로초·나노초 매직 값을 구분합니다. 저장 길이는 `snaplen`과 원래 길이를 넘을 수 없으며, 잘린 레코드는 `PacketFormatError`로 거부합니다. repository에는 임의의 `capture.pcap`을 두지 않습니다. 공개 검사가 작은 PCAP byte열을 임시로 만들어 정상·절단 경계를 확인합니다.

```sh
PYTHONPATH=workspace python3 -m unittest tests.test_pcap -v
```

## 4–5. 경로와 연결 상태

경로 표는 프리픽스 길이, 메트릭, 입력 순서 차례로 비교합니다. 더 구체적인 `/24` 경로는 메트릭이 작지 않더라도 `/16`보다 먼저 선택되어야 합니다.

```sh
PYTHONPATH=workspace python3 -m unittest tests.test_routing -v
```

TCP 상태 기계는 능동 열기와 수동 열기를 구분합니다. 허용되지 않은 사건은 상태를 바꾸지 않고 `InvalidTransition`을 발생시킵니다.

```sh
PYTHONPATH=workspace python3 -m unittest tests.test_tcp_state -v
```

## 6. CLI 조립과 전체 회귀

1–5의 domain module 검사가 모두 통과한 뒤 `workspace/protocol_inspector/cli.py`에서 하위 명령을 연결합니다. 이렇게 해야 CLI가 아직 없는 중간 단계에서도 module별 실패를 정확히 읽을 수 있습니다.

```sh
PYTHONPATH=workspace python3 -m protocol_inspector checksum 0001f203f4f5f6f7
PYTHONPATH=workspace python3 -m protocol_inspector decode fixtures/syn-frame.hex
PYTHONPATH=workspace python3 -m protocol_inspector route \
  --table fixtures/routes.json \
  --destination 10.20.30.8
PYTHONPATH=workspace python3 -m protocol_inspector tcp \
  --role server \
  --events passive-open,receive-syn,receive-ack,receive-fin,app-close,receive-ack
PYTHONPATH=workspace python3 -m unittest tests.test_cli -v
```

`tests.test_cli`의 PCAP 사례는 임시 파일을 만들고 종료 뒤 정리하므로 별도 capture 파일이 필요하지 않습니다.

## 완료 기준

- 홀수 길이 checksum, VLAN offset, IPv4 조각과 잘린 PCAP record를 계약대로 처리합니다.
- route는 prefix 길이, metric, 입력 순서로 결정하고 default route 부재도 표현합니다.
- TCP endpoint는 role과 현재 상태에 따라 RST·FIN 사건을 전이하거나 명시적으로 거부합니다.

## 자기 설명

- packet이 선언한 길이를 실제 buffer보다 먼저 믿으면 어떤 다음 header 오해가 생기나요?
- route metric을 prefix 길이보다 먼저 비교하면 어떤 목적지가 잘못 전달되나요?
- 같은 RST가 `LISTEN`과 `ESTABLISHED`에서 다른 결과를 가져야 하는 이유는 무엇인가요?

## 검증

```sh
PYTHONPATH=workspace python3 -m unittest discover -s tests -v
python3 ../../scripts/check_skeleton.py
```

공개 검사는 VLAN 오프셋, IP 조각, PCAP 절단, 기본 경로, TCP RST의 상태별 처리까지 확인합니다. 미완성 구현은 `NotImplementedError`가 있는 지점에서 실패해야 합니다.

저장소 루트에서는 같은 workspace 검사를 다음처럼 실행합니다.

```sh
EXERCISE_IMPL=workspace make protocol-check
```

workspace가 모두 통과한 뒤에만 기준 구현의 책임 배치와 출력 계약을 비교합니다.

```sh
make EXERCISE_IMPL=reference protocol-check
diff -ru exercises/protocol-inspector/workspace \
  exercises/protocol-inspector/reference
```

fixture를 다시 만들었다면 생성 결과가 기존 입력과 같은지 확인합니다.

```sh
cd exercises/protocol-inspector
python3 tools/generate_fixtures.py
git diff -- fixtures/syn-frame.hex
```

이 코드는 Ethernet FCS, 여러 겹 VLAN, IPv6 재조립과 임의 TCP 옵션을 모두 처리하지 않습니다. 신뢰할 수 없는 운영 트래픽을 받는 보안 도구로 사용해서는 안 됩니다.
