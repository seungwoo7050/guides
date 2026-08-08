# ARP와 IPv6 Neighbor Discovery

호스트가 IP 다음 홉을 결정해도 Ethernet 프레임을 보내려면 현재 링크에서 사용할 목적지 MAC 주소가 필요합니다. IPv4는 ARP를 사용하고 IPv6는 ICMPv6 기반 Neighbor Discovery를 사용합니다. 둘은 “최종 목적지의 물리 주소를 인터넷에서 찾는 프로토콜”이 아니라 현재 링크의 다음 홉을 해석하는 절차입니다.

## 학습 목표

- 목적지 IP와 현재 링크의 다음 홉 주소를 분리해 설명합니다.
- ARP·Neighbor Discovery 상태를 경로와 링크 증거에 연결합니다.

## 선행 개념

[Ethernet과 스위칭](02-ethernet-mac-and-switching.md)의 MAC 전달 범위와 기본적인 CIDR 표기를 알고 있어야 합니다.

## 먼저 다음 홉을 선택합니다

호스트 `192.0.2.10/24`가 두 목적지로 보낸다고 가정합니다.

```text
192.0.2.50     → 같은 직접 연결 프리픽스 → 192.0.2.50의 MAC을 해석
198.51.100.20  → 다른 프리픽스           → 기본 게이트웨이 192.0.2.1의 MAC을 해석
```

원격 서버의 MAC 주소는 첫 링크에서 필요하지 않습니다. 첫 라우터는 프레임을 받아 IP 경로를 다시 조회하고, 다음 링크에서 자신의 다음 홉 주소를 별도로 해석합니다.

이 순서를 뒤집으면 “ARP가 되지 않아 원격 인터넷 주소에 연결하지 못한다”처럼 잘못된 진단을 내리기 쉽습니다. 먼저 경로 조회가 직접 연결 대상과 게이트웨이 대상 중 무엇을 선택했는지 확인하세요.

## IPv4 ARP 교환

ARP request는 보통 Ethernet broadcast로 전송되어 “이 IPv4 주소를 가진 인터페이스가 누구인지” 묻습니다. 해당 인터페이스는 자신의 MAC 주소를 담은 reply를 보냅니다.

```text
호스트 A: Who has 192.0.2.1? Tell 192.0.2.10
게이트웨이: 192.0.2.1 is at 02:00:00:00:00:01
```

결과는 neighbor cache에 일정 시간 보관됩니다. 운영체제는 항목을 단순한 존재·부재가 아니라 도달 가능성 확인 중, 지연, 탐색 실패 같은 상태로 관리할 수 있습니다. 캐시가 있다는 사실만으로 현재 통신이 성공한다고 단정하지 않습니다.

ARP는 인증을 제공하지 않습니다. 같은 링크의 공격자가 거짓 reply를 보내면 트래픽 방향을 바꿀 수 있으므로, 신뢰 경계에서는 스위치 보호 기능, 정적 정책, 암호화된 상위 프로토콜과 네트워크 분리를 함께 고려합니다.

## Proxy ARP와 gratuitous ARP

Proxy ARP에서는 라우터나 중간 장비가 다른 대상 대신 자신의 MAC 주소로 응답합니다. 호스트는 대상을 같은 링크에 있는 것처럼 보지만 실제 패킷은 중간 장비가 전달합니다.

Gratuitous ARP는 자신의 주소와 MAC 관계를 요청 없이 알리거나 중복 주소를 감지하고 캐시를 갱신하는 데 사용될 수 있습니다. 고가용성 장비의 active node가 바뀔 때 새 MAC 위치를 알리는 장면에서도 볼 수 있습니다.

이 기능들은 정상적인 사용례가 있지만, 캡처에서 요청과 일대일로 대응하지 않는 ARP reply가 보였다는 이유만으로 공격으로 단정하면 안 됩니다.

## IPv6는 ARP 대신 Neighbor Discovery를 사용합니다

IPv6 Neighbor Discovery는 ICMPv6 메시지로 다음 기능을 묶습니다.

- Neighbor Solicitation과 Neighbor Advertisement
- Router Solicitation과 Router Advertisement
- 프리픽스와 기본 라우터 발견
- 주소 자동 구성에 필요한 정보
- Duplicate Address Detection
- neighbor reachability 확인과 redirect

IPv4 ARP의 전체 브로드캐스트 대신 Solicited-Node Multicast를 사용해 대상 범위를 줄입니다. IPv6에서 ICMPv6를 무차별적으로 차단하면 주소 해석, 라우터 발견과 Path MTU Discovery까지 깨질 수 있습니다.

Neighbor Discovery 메시지는 IPv6 Hop Limit 255 같은 검증 조건을 사용해 링크 밖에서 위조된 일부 메시지를 거부합니다. 그러나 링크 내부의 신뢰 문제가 사라지는 것은 아니므로 RA Guard, SEND 적용 가능성, 포트 보안과 상위 암호화를 별도로 검토합니다.

## 캐시를 관찰하고 해석하기

Linux:

```sh
ip route get 192.0.2.50
ip neighbor show
ping -c 1 192.0.2.50
ip neighbor show
```

macOS:

```sh
route -n get 192.0.2.50
arp -an
ndp -an
```

캐시를 지우는 명령은 현재 연결과 다른 프로세스의 통신에 영향을 줄 수 있습니다. 관리 중인 실습 환경이 아니라면 캐시 삭제부터 실행하지 말고 항목 상태와 패킷 캡처를 먼저 확인하세요.

## 실패를 단계별로 구분하기

다음 순서로 관찰하면 원인을 섞지 않을 수 있습니다.

1. 대상 IP에 선택된 route와 next hop을 확인합니다.
2. 출력 인터페이스가 `UP`이고 올바른 VLAN에 있는지 확인합니다.
3. next hop에 대한 neighbor entry 상태를 확인합니다.
4. ARP Request 또는 Neighbor Solicitation이 실제로 나가는지 캡처합니다.
5. reply가 돌아오는지, 돌아온 뒤 캐시 상태가 바뀌는지 확인합니다.
6. 주소 해석 후에도 실패하면 IP 전달, 정책과 전송 계층으로 이동합니다.

ARP Reply가 없을 때는 대상 호스트 중단, 잘못된 서브넷 마스크, VLAN 분리, 스위치 포트 정책, 무선 격리나 중복 주소 등을 확인해야 합니다. ARP 자체만 수정하려 하지 말고 경로와 링크 구성도 함께 확인하세요.

## 연결 실습

[Linux 라우팅 실습](../../exercises/linux-routing-nat/README.md)에서 route 제거 전후의 이웃 해석 범위와 전달 결과를 관찰합니다.

## 완료 기준

- 로컬 목적지와 원격 목적지에 대해 실제로 해석하는 다음 홉을 각각 계산합니다.
- neighbor 상태와 요청·응답 캡처를 근거로 실패 경계를 좁힙니다.
- ARP와 IPv6 Neighbor Discovery의 공통 책임과 서로 다른 검증 조건을 설명합니다.
