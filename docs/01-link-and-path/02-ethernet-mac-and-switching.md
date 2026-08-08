# Ethernet, MAC 주소와 스위칭

Ethernet은 같은 링크 계층 도메인에서 프레임을 다음 인터페이스로 전달하는 형식을 제공합니다. IP 주소가 여러 링크를 잇는 논리적 위치라면 Ethernet 주소는 현재 링크에서 프레임을 어느 인터페이스 방향으로 보낼지 결정하는 데 사용됩니다.

## 학습 목표

- Ethernet II 프레임 경계와 주요 필드를 길이 기준으로 해석합니다.
- 스위치 학습, flooding과 VLAN 경계를 IP 라우팅과 구분합니다.

## 선행 개념

[계층과 종단 경로](01-layers-encapsulation-and-path.md)의 캡슐화 단위와 링크·인터넷 계층 경계를 먼저 이해해야 합니다.

## Ethernet II 프레임 읽기

캡처 도구가 흔히 보여 주는 Ethernet II 프레임은 다음 순서입니다.

| 필드 | 크기 | 역할 |
|---|---:|---|
| Destination MAC | 6바이트 | 현재 링크의 수신 대상 |
| Source MAC | 6바이트 | 현재 링크의 송신 출처 |
| EtherType | 2바이트 | 페이로드 프로토콜 식별 |
| Payload와 padding | 가변 | IP, ARP 등의 데이터 |
| FCS | 4바이트 | 링크 전송 오류 검출 |

Preamble과 Start Frame Delimiter는 물리 전송에 필요하지만 일반적인 패킷 캡처의 프레임 바이트에 포함되지 않습니다. FCS도 NIC가 검증하고 제거한 뒤 운영체제에 전달하는 경우가 많아 캡처 파일에서 보이지 않을 수 있습니다. FCS가 없다는 관찰만으로 프레임에 오류 검사가 없었다고 판단하지 않습니다.

## MAC 주소가 의미하는 범위

48비트 MAC 주소의 첫 옥텟에는 개별·그룹 주소와 전역·로컬 관리 여부를 나타내는 비트가 있습니다. 가상 인터페이스, 컨테이너와 개인 정보 보호 기능은 로컬 관리 주소를 만들 수 있습니다.

다음 단정은 피해야 합니다.

- 모든 MAC 주소가 제조 시 영구적으로 고정된다는 단정
- MAC 주소가 인터넷 전체에서 라우팅된다는 단정
- 출발지 MAC만 보고 물리 장비의 신원을 확정하는 단정

브로드캐스트 주소 `ff:ff:ff:ff:ff:ff`는 같은 브로드캐스트 도메인의 모든 수신자에게 전달하려는 의도입니다. 멀티캐스트 주소는 특정 그룹을 나타내며, 유니캐스트 주소는 하나의 논리적 인터페이스를 가리킵니다.

## 스위치는 출발지에서 학습합니다

학습형 스위치는 프레임의 **출발지 MAC과 들어온 포트**를 전달 데이터베이스에 기록합니다. 목적지에 대한 동작은 다음처럼 나뉩니다.

```text
목적지 MAC을 알고 있음 → 기록된 포트로 전달
목적지 MAC을 모름      → 입력 포트를 제외하고 같은 VLAN에 flooding
브로드캐스트·일부 멀티캐스트 → 같은 VLAN에 flooding
목적지가 입력 포트에 있음 → 전달하지 않음
```

스위치는 목적지 IP의 prefix로 일반적인 Ethernet 전달을 결정하지 않습니다. 반대로 라우터는 링크 프레임을 받은 뒤 IP 목적지에 따라 다음 경로를 선택합니다. L2 스위칭과 L3 라우팅을 같은 테이블 조회로 합치지 마세요.

학습 항목에는 aging 시간이 있어 오래 관찰되지 않은 위치는 제거됩니다. 장비가 다른 포트로 이동하거나 가상 머신이 마이그레이션하면 새 출발지 프레임으로 위치를 다시 학습합니다.

## VLAN은 하나의 물리 링크를 논리 도메인으로 나눕니다

802.1Q 태그는 원래 EtherType 위치에 Tag Protocol Identifier를 두고, 우선순위·Drop Eligible Indicator·VLAN ID를 담은 Tag Control Information을 추가합니다. 실제 payload의 EtherType은 태그 뒤로 이동합니다.

```text
목적지 | 출발지 | 0x8100 | TCI | 내부 EtherType | 페이로드
```

같은 스위치에 연결되어도 서로 다른 VLAN이면 기본적으로 같은 브로드캐스트 도메인이 아닙니다. VLAN 사이 통신에는 L3 라우팅이 필요합니다. VLAN은 네트워크 분리 도구지만 인증이나 암호화를 자동으로 제공하지 않습니다.

## MTU와 최소 프레임 크기

Ethernet의 일반적인 IP MTU는 1500바이트이지만 링크와 터널 구성에 따라 달라질 수 있습니다. 작은 payload는 최소 프레임 크기를 맞추기 위해 padding될 수 있습니다. 상위 프로토콜은 자신의 길이 필드를 사용해 padding과 실제 데이터를 구분합니다.

Jumbo frame은 모든 경로 장비와 인터페이스가 같은 MTU를 지원해야 합니다. 한 구간만 크게 설정하면 큰 패킷이 특정 경계에서 손실되거나 분할될 수 있습니다.

## 프레임 파서로 경계 확인하기

프로토콜 검사기는 일반 Ethernet II와 한 개의 802.1Q 또는 802.1ad 태그를 읽습니다.

```sh
cd exercises/protocol-inspector
PYTHONPATH=reference python3 -m unittest tests.test_packet.PacketParserTests.test_vlan_tag_changes_the_payload_offset -v
```

파서가 확인하는 핵심 조건은 다음과 같습니다.

1. 기본 헤더 14바이트가 실제로 있는지 확인합니다.
2. 태그 EtherType이면 추가 4바이트가 있는지 확인합니다.
3. 태그 뒤의 inner EtherType을 상위 프로토콜 선택에 사용합니다.
4. 지원하지 않는 EtherType은 억지로 IPv4로 해석하지 않습니다.

운영용 파서는 여러 겹의 VLAN 태그, LLC/SNAP 형식, 캡처 메타데이터와 NIC 오프로딩 영향까지 고려해야 합니다. 실습 구현은 경계 검사와 계층 선택이라는 최소 계약만 다룹니다.

## 스위칭 문제를 좁히는 관찰

Linux에서는 다음 명령으로 인터페이스와 링크 정보를 확인할 수 있습니다.

```sh
ip -details link show
bridge fdb show
```

macOS에서는 `ifconfig`로 인터페이스와 MAC 주소를 확인할 수 있지만, 외부 스위치의 FDB는 해당 장비의 관리 인터페이스에서 확인해야 합니다.

문제를 조사할 때 VLAN, 입력 포트, 학습된 MAC 위치, flooding 범위와 링크 상태를 따로 기록하세요. 다음 장에서는 IP가 선택한 다음 홉을 실제 MAC 주소로 바꾸는 ARP와 IPv6 Neighbor Discovery를 연결합니다.

## 연결 실습

[프로토콜 검사기](../../exercises/protocol-inspector/README.md)의 프레임 decoder로 길이, EtherType, VLAN offset과 비 IPv4 payload 처리를 확인합니다.

## 완료 기준

- 캡처 바이트에서 목적지·출발지 MAC, EtherType과 payload 시작 위치를 계산합니다.
- 알 수 없는 목적지 flooding과 broadcast를 같은 현상으로 설명하지 않습니다.
- VLAN과 포트 상태를 포함한 링크 계층 조사 증거를 기록합니다.
