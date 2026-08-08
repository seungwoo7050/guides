# 프로토콜 필드 빠른 참조

패킷 캡처에서 자주 확인하는 필드의 위치와 의미를 모았습니다. 이 표는 전체 표준을 대체하지 않으며 option, extension header, 터널과 구현별 metadata는 각 RFC와 도구 문서를 확인해야 합니다.

## Ethernet II와 802.1Q

```text
0               6              12             14
+---------------+---------------+--------------+
| destination   | source        | EtherType    |
+---------------+---------------+--------------+
| payload ...                                  |
+----------------------------------------------+
```

| 필드 | 크기 | 확인할 내용 |
|---|---:|---|
| Destination | 6바이트 | unicast, multicast 또는 broadcast 대상 |
| Source | 6바이트 | 현재 링크의 송신 주소 |
| EtherType | 2바이트 | `0x0800` IPv4, `0x86dd` IPv6, `0x0806` ARP |
| FCS | 4바이트 | 캡처에서 NIC가 제거할 수 있음 |

802.1Q 태그가 있으면 `0x8100` 뒤에 2바이트 TCI와 inner EtherType이 옵니다. TCI는 PCP 3비트, DEI 1비트와 VLAN ID 12비트로 구성됩니다.

## IPv4 최소 헤더

```text
0                   1                   2                   3
+----+----+-----------+-----------------+-------------------+
|Ver |IHL | DSCP/ECN  | Total Length                        |
+---------------------+-----------------+-------------------+
| Identification      |Flags| Fragment Offset               |
+---------------------+-----+-------------------------------+
| TTL | Protocol      | Header Checksum                     |
+-----------------------------------------------------------+
| Source Address                                              |
+-----------------------------------------------------------+
| Destination Address                                         |
+-----------------------------------------------------------+
| Options if IHL > 5                                         |
+-----------------------------------------------------------+
```

- IHL은 32비트 word 단위이며 최솟값은 5입니다.
- Total Length는 header와 payload를 합친 바이트 수입니다.
- Fragment Offset은 8바이트 단위입니다.
- Header Checksum은 header만 포함합니다.
- Protocol `1`은 ICMP, `6`은 TCP, `17`은 UDP를 뜻합니다.

## IPv6 고정 헤더

| 필드 | 크기 | 역할 |
|---|---:|---|
| Version, Traffic Class, Flow Label | 4바이트 | 버전과 traffic 식별 정보 |
| Payload Length | 2바이트 | 고정 header 뒤 길이 |
| Next Header | 1바이트 | extension 또는 상위 protocol |
| Hop Limit | 1바이트 | 홉마다 감소하는 수명 |
| Source | 16바이트 | 출발지 IPv6 주소 |
| Destination | 16바이트 | 목적지 IPv6 주소 |

IPv6 고정 헤더에는 header checksum과 router fragment 필드가 없습니다. extension header 순서와 처리 규칙은 RFC 8200을 확인하세요.

## TCP 최소 헤더

| 필드 | 크기 | 역할 |
|---|---:|---|
| Source Port | 2바이트 | 송신 endpoint port |
| Destination Port | 2바이트 | 수신 endpoint port |
| Sequence Number | 4바이트 | 첫 payload byte 또는 SYN/FIN 위치 |
| Acknowledgment Number | 4바이트 | 다음에 기대하는 byte 번호 |
| Data Offset와 Flags | 2바이트 | header 길이와 제어 비트 |
| Window | 2바이트 | 수신자가 광고하는 window |
| Checksum | 2바이트 | 의사 헤더, TCP header와 payload 검증 |
| Urgent Pointer | 2바이트 | URG 의미에 따른 위치 |
| Options | 가변 | MSS, window scale, SACK, timestamp 등 |

Data Offset은 32비트 word 단위이며 최솟값은 5입니다.

| flag | 의미를 해석할 때 볼 사건 |
|---|---|
| SYN | 연결 시작과 초기 sequence 동기화 |
| ACK | acknowledgment field가 유효함 |
| FIN | 해당 방향 byte stream의 정상 종료 |
| RST | 연결 거부 또는 즉시 중단 |
| PSH | 수신 application에 전달하라는 힌트 |
| URG | urgent pointer가 유효함 |
| ECE/CWR | ECN 협상과 congestion signal |
| NS | ECN nonce에 할당되었던 bit이며 현재 해석은 명세를 확인해야 함 |

`tcpdump`는 흔히 `S`를 SYN, `.`을 ACK, `F`를 FIN, `R`을 RST, `P`를 PSH로 표시합니다. `S.`는 SYN과 ACK가 함께 설정된 패킷입니다.

## UDP 헤더

| 필드 | 크기 | 역할 |
|---|---:|---|
| Source Port | 2바이트 | 선택적 송신 port |
| Destination Port | 2바이트 | 수신 port |
| Length | 2바이트 | header를 포함한 전체 데이터그램 길이 |
| Checksum | 2바이트 | 의사 헤더, UDP header와 payload 검증 |

UDP 최소 길이는 8바이트입니다. IPv4와 IPv6의 checksum 요구가 다르므로 0 값을 같은 의미로 처리하지 않습니다.

## 체크섬 의사 헤더

IPv4 TCP·UDP 의사 헤더는 wire에 독립 header로 전송되지 않지만 checksum 계산에 포함됩니다.

```text
source IPv4 | destination IPv4 | zero | protocol | transport length
```

IPv6는 128비트 주소, 32비트 길이와 Next Header를 포함한 다른 의사 헤더를 사용합니다. 실습 구현은 IPv4 TCP만 계산합니다.
