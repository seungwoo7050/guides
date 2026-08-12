# TCP 연결 상태와 순서 번호

TCP 연결은 소켓 두 개가 존재한다는 사실만으로 설명되지 않습니다. 각 종단점은 SYN, ACK, FIN, RST와 타이머 사건에 따라 상태를 전이하고, 순서 번호로 바이트 스트림의 위치를 식별합니다. 상태와 번호를 함께 보아야 핸드셰이크, 단방향 종료와 재전송을 이해할 수 있습니다.

## 학습 목표

- TCP 사건에 따른 양쪽 endpoint 상태 전이를 추적합니다.
- SYN·FIN의 sequence 소비와 누적 ACK의 byte 범위를 계산합니다.

## 선행 개념

[UDP와 TCP 서비스 계약](01-udp-and-tcp-service-contracts.md)의 바이트 스트림 의미와 기본 TCP header field를 알고 있어야 합니다.

## 순서 번호는 바이트 위치를 나타냅니다

TCP 헤더의 Sequence Number는 세그먼트 페이로드 첫 바이트의 번호를 나타냅니다. Acknowledgment Number는 상대에게서 다음에 기대하는 순서 번호입니다.

```text
상대가 seq 1000에서 100바이트 전송
→ 수신자가 1000..1099를 모두 받음
→ ACK 1100
```

ACK는 기본적으로 누적입니다. `ACK 1100`은 그 이전 바이트가 모두 연속적으로 도착했다는 뜻이며, 이후의 순서가 뒤바뀐 바이트 수신 여부는 SACK 옵션 같은 추가 정보로 표현할 수 있습니다.

SYN과 FIN은 페이로드가 없어도 순서 번호 공간에서 각각 1을 소비합니다. 클라이언트 SYN이 `seq 5000`이면 정상 SYN/ACK의 ACK는 `5001`입니다. RST 처리와 Challenge ACK 같은 세부 규칙은 전체 TCP 명세를 따라야 하며 실습 상태 머신은 핵심 정상 경로만 다룹니다.

## 일반적인 3단계 핸드셰이크

능동 연결을 여는 클라이언트:

```text
CLOSED
  active open, SYN 전송
SYN-SENT
  SYN/ACK 수신, ACK 전송
ESTABLISHED
```

수동 연결을 기다리는 서버:

```text
CLOSED
  passive open
LISTEN
  SYN 수신, SYN/ACK 전송
SYN-RECEIVED
  ACK 수신
ESTABLISHED
```

서버의 일반 흐름을 `LISTEN → SYN-SENT → ESTABLISHED`로 표현하면 능동 열기와 수동 열기를 섞은 것입니다. `SYN-SENT`는 로컬 종단점이 먼저 SYN을 보낸 상태이고, 서버가 LISTEN에서 SYN을 받은 정상 경로는 `SYN-RECEIVED`로 갑니다.

세 번째 ACK가 필요한 이유는 서버가 보낸 SYN도 클라이언트가 받았음을 확인하고 양쪽 초기 순서 번호 공간을 동기화하기 위해서입니다. SYN/ACK만 본 캡처로 양쪽 애플리케이션이 연결을 사용할 수 있다고 단정하지 않습니다.

## 동시에 open할 수도 있습니다

두 종단점이 동시에 능동 열기를 수행하면 양쪽이 `SYN-SENT`에서 순수 SYN을 받아 `SYN-RECEIVED`로 갈 수 있습니다. 일반적인 클라이언트-서버 흐름은 아니지만 상태 머신이 단순한 선형 목록이 아닌 이유를 보여 줍니다.

방화벽, NAT와 테스트 도구가 일반 handshake만 가정하면 simultaneous open이나 SYN retransmission을 이상 동작으로 잘못 분류할 수 있습니다.

## 연결 종료는 양방향이 독립적입니다

한 종단점이 더 보낼 데이터가 없어 FIN을 보내도 상대 방향의 바이트 스트림은 계속 열려 있을 수 있습니다.

능동 종료 측의 대표 경로:

```text
ESTABLISHED
→ FIN-WAIT-1
→ FIN-WAIT-2
→ TIME-WAIT
→ CLOSED
```

수동 종료 측의 대표 경로:

```text
ESTABLISHED
→ CLOSE-WAIT
→ LAST-ACK
→ CLOSED
```

`CLOSE-WAIT`가 오래 남는다면 피어의 FIN을 커널이 받았지만 로컬 애플리케이션이 소켓을 닫지 않은 가능성을 먼저 봅니다. 네트워크가 FIN을 잃었다는 뜻이 아닙니다.

`TIME-WAIT`는 마지막 ACK를 다시 보낼 수 있게 하고 이전 연결의 지연 segment가 같은 tuple의 새 연결과 섞이는 위험을 줄입니다. 서버에서 TIME-WAIT 수가 많다는 사실만으로 누수라고 단정하지 말고 어느 쪽이 active close했는지와 연결 생성률을 확인합니다.

## RST는 정상 종료와 다른 의미입니다

RST는 연결 상태가 없거나 즉시 중단해야 함을 알립니다. unread data가 남은 socket을 특정 방식으로 닫거나, listen하지 않는 port에 SYN이 도착하거나, 존재하지 않는 연결의 segment를 받는 상황에서 관찰할 수 있습니다.

수신 측은 RST를 무조건 `CLOSED`로 바꾸지 않습니다. 순서 번호와 ACK가 현재 상태에서 허용되는지 먼저 검증하고, `LISTEN`에서는 RST를 무시하며, 수동 열기에서 온 `SYN-RECEIVED`는 유효한 RST 뒤 `LISTEN`으로 돌아갈 수 있습니다. 동기화된 연결의 유효한 RST는 연결을 중단합니다. 실습 모델은 순서 번호 검증을 생략하지만 이 상태별 결과는 구분합니다.

RST의 원인은 캡처 방향과 이전 패킷을 함께 보아야 합니다. 중간 방화벽이 RST를 생성할 수도 있으므로 출발지 IP만 보고 애플리케이션 프로세스가 직접 보냈다고 확정하지 않습니다.

## 상태 머신 실습

프로토콜 검사기는 정상 open·close와 일부 동시 종료를 명시적 transition table로 표현합니다. root README 순서 8에서 state module을 먼저 검사하고, 그 뒤 CLI를 조립합니다.

```sh
cd exercises/protocol-inspector
PYTHONPATH=workspace python3 -m unittest tests.test_tcp_state -v
```

공개 검사가 확인하는 active client의 핵심 상태 순서:

```text
CLOSED
SYN-SENT
ESTABLISHED
FIN-WAIT-1
FIN-WAIT-2
TIME-WAIT
CLOSED
```

허용하지 않은 전이는 상태를 억지로 바꾸지 않고 `InvalidTransition`을 발생시킵니다. 실제 TCP는 재전송 타이머, 반쯤 열린 연결 정리, 창 탐색과 많은 예외 전이를 더 가집니다. 학습 모델을 운영용 TCP 검증기로 사용하지 마세요.

## 캡처에서 번호를 따라가기

[패킷 관찰 실습](../../exercises/packet-observation/README.md)의 기준 입력에서 다음을 확인합니다.

1. 첫 SYN의 sequence와 SYN/ACK의 ACK 차이가 1인지 확인합니다.
2. SYN/ACK의 sequence와 마지막 ACK 차이가 1인지 확인합니다.
3. 데이터 세그먼트의 `seq start:end` 길이가 페이로드 길이와 같은지 확인합니다.
4. 상대 ACK가 연속적으로 받은 마지막 바이트 다음을 가리키는지 확인합니다.
5. 같은 SYN sequence가 다시 보이면 timestamp 차이와 손실 위치를 기록합니다.

상대 번호를 임의로 0부터 다시 표시하는 패킷 분석기 기능을 사용할 수 있습니다. 보고서에는 상대 순서 번호를 썼는지 실제 전송된 절대 32비트 값을 썼는지 명시하세요.

## 연결 실습

[프로토콜 검사기](../../exercises/protocol-inspector/README.md)의 상태 기계와 [패킷 관찰](../../exercises/packet-observation/README.md)의 handshake fixture를 같은 사건 순서로 비교합니다.

## 완료 기준

- 능동 열기와 수동 열기의 상태를 endpoint별로 표로 작성합니다.
- SYN·FIN·payload가 소비한 sequence 범위와 다음 ACK를 계산합니다.
- RST를 현재 상태와 role을 무시한 단일 전이로 처리하지 않습니다.
