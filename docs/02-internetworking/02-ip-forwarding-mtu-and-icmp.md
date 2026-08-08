# IP 전달, MTU와 ICMP

라우터는 패킷을 받으면 목적지 주소를 다른 포트로 복사하는 데 그치지 않습니다. 헤더가 처리 가능한지 확인하고, 수명을 줄이고, 경로를 선택하며, 출력 링크의 MTU와 이웃 상태를 확인한 뒤 새 링크 프레임으로 보냅니다. 전달하지 못할 때는 가능한 경우 ICMP로 원인을 알립니다.

## 학습 목표

- 라우터의 입력 검증부터 출력 프레임 생성까지 전달 단계를 추적합니다.
- TTL, MTU와 ICMP 증거를 서로 다른 실패 계약으로 해석합니다.

## 선행 개념

[IP 주소와 경로 조회](01-ip-addressing-subnets-and-lpm.md), IPv4 header의 길이·TTL·checksum 필드를 먼저 알아야 합니다.

## 개념적인 전달 경로

```text
입력 프레임 수신
→ 링크 헤더와 IP 버전 확인
→ IP 헤더 길이·전체 길이·체크섬 검증
→ TTL 또는 Hop Limit 감소
→ 정책과 경로 조회
→ 출력 MTU 검사
→ next-hop neighbor lookup
→ 새 링크 프레임 생성과 전송
```

실제 장비는 빠른 처리 경로, ACL, QoS, 터널과 하드웨어 오프로딩을 포함하지만 각 단계가 해결하는 질문은 같습니다. 패킷이 어디서 사라지는지 찾을 때 입력 카운터, 경로, 정책, MTU와 출력 카운터를 차례로 봅니다.

## IPv4 헤더에서 전달에 필요한 필드

- Version과 IHL은 헤더 형식과 길이를 정합니다.
- Total Length는 header와 payload의 전체 바이트 수를 정합니다.
- Identification, Flags와 Fragment Offset은 단편화와 재조립에 사용됩니다.
- TTL은 라우팅 loop에서 패킷이 영원히 남지 않도록 홉마다 감소합니다.
- Protocol은 TCP, UDP, ICMP 같은 상위 payload를 식별합니다.
- Header Checksum은 IPv4 **헤더만** 보호합니다.
- Source와 Destination은 종단 주소를 나타냅니다.

TTL이 바뀌므로 IPv4 라우터는 헤더 체크섬도 다시 계산해야 합니다. TCP와 UDP 체크섬은 의사 헤더에 IP 주소를 포함하지만 TTL은 포함하지 않으므로 일반 라우팅만으로 다시 계산하지 않습니다. NAT가 주소나 포트를 바꾸면 관련 체크섬도 갱신해야 합니다.

IPv6 기본 헤더는 고정 40바이트이고 헤더 체크섬이 없습니다. 선택 기능은 확장 헤더로 연결하며 TTL에 해당하는 필드는 Hop Limit입니다.

## MTU는 링크 한 번에 실을 수 있는 상한입니다

Maximum Transmission Unit은 링크 계층 payload로 전달할 수 있는 최대 크기입니다. 경로에는 여러 링크가 있으므로 종단이 사용할 수 있는 크기는 가장 작은 구간의 영향을 받습니다.

IPv4에서는 DF가 설정되지 않았다면 중간 라우터가 패킷을 단편화할 수 있습니다. DF가 설정되었거나 단편화할 수 없으면 라우터는 패킷을 버리고 ICMP “fragmentation needed” 정보를 보낼 수 있습니다.

IPv6 라우터는 전달 중 패킷을 단편화하지 않습니다. 너무 크면 ICMPv6 Packet Too Big을 보내고, 출발지가 더 작은 패킷을 만들거나 Fragment 확장 헤더를 사용합니다.

단편은 각자 손실될 수 있고 수신자가 원래 패킷을 재조립해야 하므로 비용과 공격 표면이 늘어납니다. 가능하면 송신자가 Path MTU를 알아내 적절한 크기로 보내는 편이 낫습니다.

## Path MTU Discovery가 실패하는 경우

전통적 PMTUD는 너무 큰 패킷에 대한 ICMP 오류를 사용합니다. 중간 방화벽이 관련 ICMP를 모두 막으면 작은 요청은 되지만 큰 응답이나 특정 TLS record에서 멈추는 MTU black hole이 생길 수 있습니다.

Packetization Layer PMTUD는 전송 또는 애플리케이션 계층에서 다양한 크기를 probe해 ICMP에만 의존하지 않는 방법을 제공합니다. 어떤 방법을 사용하더라도 “ping이 되므로 모든 크기의 TCP가 된다”는 결론은 성립하지 않습니다.

터널, VPN과 캡슐화는 추가 헤더만큼 유효 MTU를 줄입니다. 오버레이를 추가한 뒤 특정 페이로드 크기에서만 실패한다면 인터페이스 MTU, 경로 MTU, MSS 조정과 ICMP 전달을 함께 확인하세요.

## ICMP는 오류만이 아니라 IP 동작의 일부입니다

ICMP와 ICMPv6는 Echo Request/Reply 외에도 다음 정보를 전달합니다.

- Destination Unreachable
- time exceeded
- parameter problem
- redirect
- IPv6 Packet Too Big
- IPv6 Neighbor Discovery 메시지

오류 메시지는 원래 패킷의 일부를 포함해 어느 흐름에서 문제가 났는지 식별하도록 돕습니다. ICMP 자체도 전달 보장이 없고, 다른 ICMP 오류에 다시 오류를 만드는 것을 피하는 규칙이 있습니다.

보안상 모든 ICMP를 허용할 필요는 없지만 필요한 type과 code까지 무차별적으로 차단하면 PMTUD, IPv6 NDP와 장애 진단이 깨집니다. 정책은 “ICMP 전체 차단”보다 요구 기능과 rate limit을 기준으로 설계합니다.

## 인터넷 체크섬 구현하기

IPv4 헤더 체크섬과 TCP·UDP 체크섬은 16비트 1의 보수 합을 사용합니다. 홀수 길이 데이터는 계산할 때 오른쪽에 0바이트를 붙이고, 상위 올림은 하위 16비트에 다시 더합니다.

```sh
cd exercises/protocol-inspector
PYTHONPATH=reference python3 -m protocol_inspector checksum 0001f203f4f5f6f7
```

TCP checksum은 TCP header와 payload만 계산하지 않습니다. IPv4 출발지·목적지, 0, protocol과 TCP 길이로 만든 의사 헤더를 앞에 붙입니다. 이 의사 헤더는 잘못된 주소나 protocol로 전달된 세그먼트를 검출하는 데 도움을 줍니다.

NIC checksum offload가 켜진 송신 캡처에서는 운영체제가 아직 checksum을 채우기 전에 패킷을 관찰해 “bad checksum”처럼 보일 수 있습니다. 수신 지점의 캡처, offload 설정과 캡처 방향을 함께 확인하세요.

## 격리된 TTL 실험

Linux 실습은 클라이언트와 서버 사이에 라우터 네임스페이스 하나를 둡니다.

```sh
cd exercises/linux-routing-nat
sudo ./scripts/run-routing.sh
```

TTL 1인 echo request는 라우터에서 0이 되어 목적지에 도착하지 않고, TTL 2는 한 홉을 지나 서버에 도착합니다. 같은 실습이 기본 route를 제거했을 때 실패하고 복구 뒤 성공하는지도 확인합니다.

## 전달 실패를 기록하는 표

| 관찰 위치 | 확인할 증거 | 대표 원인 |
|---|---|---|
| 입력 인터페이스 | 패킷 카운터와 캡처 | 이전 홉·VLAN·링크 문제 |
| IP 검증 | 폐기 이유, 체크섬 | 잘린 패킷, 잘못된 헤더 |
| TTL/Hop Limit | ICMP time exceeded | loop, 지나치게 긴 경로 |
| 경로 조회 | 선택된 프리픽스와 다음 홉 | 경로 누락, 정책 불일치 |
| MTU | 패킷 크기, DF, ICMP | 터널 오버헤드, PMTUD 차단 |
| 출력 인터페이스 | 이웃 상태와 카운터 | ARP/NDP, 출력 정책, 링크 중단 |

각 단계의 입력과 출력을 구분하면 “라우터가 패킷을 먹었다”는 추측을 구체적인 실패 조건으로 바꿀 수 있습니다.

## 연결 실습

[Linux 라우팅·손실 실습](../../exercises/linux-routing-nat/README.md)에서 TTL 1/2와 경로 제거를 비교하고, [경로 진단](../../exercises/path-diagnosis/README.md)에서 MTU black hole 증거를 분류합니다.

## 완료 기준

- 입력 패킷에서 TTL 감소, route 선택과 새 링크 header 생성을 순서대로 설명합니다.
- 크기별 성공·실패와 ICMP 관찰로 MTU 문제를 반증 가능하게 기록합니다.
- ICMP 부재를 곧바로 중간 방화벽 원인으로 확정하지 않습니다.
