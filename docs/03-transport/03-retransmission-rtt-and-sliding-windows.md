# 재전송, RTT와 슬라이딩 윈도

TCP 송신자는 보냈지만 아직 누적 ACK되지 않은 바이트를 추적합니다. 손실을 직접 보는 것이 아니라 ACK 패턴과 타이머로 추론하고, 너무 이른 재전송과 너무 늦은 복구 사이에서 재전송 제한 시간을 조정합니다.

## 학습 목표

- `send_base`, 비행 중 byte와 누적 ACK로 송신 창 상태를 계산합니다.
- RTT 표본, RTO와 중복 ACK를 서로 다른 재전송 근거로 해석합니다.

## 선행 개념

[TCP 상태와 순서 번호](02-tcp-connection-state-and-sequences.md)의 byte 범위와 ACK 의미를 먼저 이해해야 합니다.

## 송신 상태를 바이트 구간으로 보기

```text
send_base      가장 오래 ACK되지 않은 바이트
next_sequence  다음 새 byte에 사용할 번호
in_flight      next_sequence - send_base
```

수신 ACK가 `send_base`보다 커지면 그 사이 바이트가 새로 확인되고 창이 열립니다. 이전 ACK가 반복되면 새 바이트가 확인되지 않았다는 뜻이지만, 패킷 순서 뒤바뀜과 ACK 중복도 가능하므로 한 번의 중복 ACK만으로 즉시 손실을 확정하지 않습니다.

순서 번호는 32비트에서 순환합니다. 단순 정수 대소 비교로 오래된 번호와 새 번호를 판단하면 순환 경계에서 오류가 생길 수 있으므로 모듈러 순서 번호 연산 규칙이 필요합니다.

## 슬라이딩 윈도는 여러 바이트를 동시에 비행시킵니다

Stop-and-wait처럼 한 segment ACK 뒤 다음을 보내면 bandwidth-delay product가 큰 경로를 채우지 못합니다. 슬라이딩 윈도는 일정 범위의 미확인 바이트를 동시에 보내 지연 중에도 링크를 사용할 수 있게 합니다.

```text
[이미 ACK됨][보냈지만 미확인][지금 보낼 수 있음][창 밖]
            ^ send_base       ^ next_sequence
```

실제 송신 상한은 수신자가 광고한 `rwnd`와 혼잡 제어의 `cwnd`를 함께 받습니다. 이 관계는 다음 장과 [송신 창 모델](../../examples/window-model/README.md)에서 실행합니다.

## 누적 ACK와 SACK

누적 ACK만 사용하면 중간 구간 하나가 빠졌을 때 그 뒤 바이트를 받았는지 Acknowledgment Number 하나로 표현할 수 없습니다. 수신자는 같은 누적 ACK를 반복하고, SACK 옵션을 협상했다면 별도로 도착한 바이트 블록을 알릴 수 있습니다.

```text
수신: 1000..1999, 3000..3999
누적 ACK: 2000
SACK block: 3000..4000
```

sender는 빠진 `2000..2999`를 우선 재전송하고 이미 도착한 block을 불필요하게 다시 보내지 않을 수 있습니다. SACK 정보도 신뢰 경계와 구현 상태를 고려해 검증해야 합니다.

## RTT 표본과 RTO 계산

Round-Trip Time은 segment를 보낸 시점부터 이를 확인하는 ACK를 받은 시점까지의 관찰입니다. 경로 queue와 ACK 정책 때문에 매번 달라지므로 단일 값 대신 평활된 추정치를 사용합니다.

RFC 6298의 기본 계산은 첫 표본 `R`에 대해 다음처럼 시작합니다.

```text
SRTT = R
RTTVAR = R / 2
RTO = SRTT + max(G, 4 * RTTVAR)
```

이후 표본 `R'`에는 일반적으로 `alpha = 1/8`, `beta = 1/4`를 사용합니다.

```text
RTTVAR = (1 - beta) * RTTVAR + beta * |SRTT - R'|
SRTT   = (1 - alpha) * SRTT + alpha * R'
RTO    = SRTT + max(G, 4 * RTTVAR)
```

`G`는 시계 해상도입니다. 표준의 초기값과 하한은 보수적으로 정해져 있으며 실제 운영체제는 후속 표준과 구현 정책을 함께 적용할 수 있습니다. 패킷 한두 개로 커널의 최종 RTO를 역산했다고 주장하지 마세요.

## 재전송된 segment의 RTT는 모호합니다

같은 순서 번호 범위를 두 번 보낸 뒤 ACK가 오면 첫 전송과 두 번째 전송 중 어느 것을 확인했는지 누적 ACK만으로 알기 어렵습니다. Karn의 알고리즘은 재전송된 세그먼트에서 모호한 RTT 표본을 사용하지 않고 제한 시간 초과 뒤 RTO를 지수적으로 늘립니다.

TCP Timestamp 옵션이 있으면 더 많은 정보를 얻을 수 있지만 옵션 협상과 구현 규칙을 따라야 합니다.

## timeout과 빠른 손실 복구

RTO가 만료되면 가장 오래 확인되지 않은 데이터를 재전송합니다. 제한 시간이 반복해서 초과되면 지수 백오프로 재시도 간격을 늘려 장애 중 트래픽 폭증을 막습니다.

여러 중복 ACK와 SACK은 타이머 만료 전 손실을 추정해 빠른 재전송과 복구를 시작할 수 있습니다. 필요한 중복 ACK 수와 복구 세부 동작은 혼잡 제어 알고리즘과 최신 TCP 확장에 따라 달라집니다.

RTO는 애플리케이션 요청 제한 시간과 다릅니다. 커널이 TCP 세그먼트를 계속 재전송하는 동안 애플리케이션은 더 짧은 마감 시간으로 요청을 포기할 수 있고, 반대로 긴 요청 제한 시간 하나만 두면 사용자에게 너무 늦게 실패를 알릴 수 있습니다.

## 결정적 송신 모델로 상태를 확인하기

[송신 창 모델](../../examples/window-model/README.md)은 RTT 평활값, RTO 백오프, 느린 시작, 혼잡 회피와 세 번의 중복 ACK를 순수한 상태 전이로 계산합니다.

```sh
cd examples/window-model
python3 -m unittest -v
```

첫 RTT 표본에서 `SRTT`와 `RTTVAR`가 어떻게 시작되는지, 제한 시간 초과 때 RTO가 두 배로 늘어나는지, 세 번째 중복 ACK에서 빠른 재전송 상태로 들어가는지 확인합니다. 모델의 벽시계 시간은 사용하지 않으므로 실행 환경이 달라도 같은 결과가 나옵니다.

## 실제 SYN 재전송 만들기

Linux 실습은 라우터의 서버 방향 egress를 잠시 100% loss로 설정합니다.

```sh
cd exercises/linux-routing-nat
sudo ./scripts/run-loss-retransmission.sh
```

클라이언트 인터페이스에서 같은 출발지·목적지·SYN 순서 번호가 두 번 보일 때 손실을 제거합니다. 다음 재시도가 서버에 도달하면 연결과 애플리케이션 페이로드 교환이 완료됩니다.

이 실험은 SYN 타이머 하나만 관찰합니다. 데이터 재전송, SACK 복구, 지연 ACK와 혼잡 창 변화까지 측정하려면 더 긴 추적 기록과 송신자의 커널 TCP 통계가 필요합니다.

## trace에서 재전송을 판정할 때

같은 순서 번호 범위가 반복되면 강한 후보지만 다음 영향을 확인해야 합니다.

- 캡처 지점이 중복 패킷을 보았나요?
- NIC의 segmentation or receive offload가 표시를 바꿨나요?
- packet이 실제로 손실되었나요, 순서만 바뀌었나요?
- 재전송 전에 중복 ACK 또는 제한 시간 초과가 있었나요?
- 상대가 SACK block으로 이미 받은 범위를 알렸나요?
- NAT나 proxy 때문에 tuple이 다른 위치에서 바뀌었나요?

[패킷 관찰 실습](../../exercises/packet-observation/README.md)의 분석기는 같은 특징을 재전송 **후보**로만 표시합니다. 완전한 TCP 분석기로 과장하지 않는 이유입니다.

## 연결 실습

[송신 창 모델](../../examples/window-model/README.md)에서 ACK와 timeout을 결정적으로 적용하고, [패킷 관찰](../../exercises/packet-observation/README.md)에서 반복 SYN을 후보로 분류합니다.

## 완료 기준

- 송신 byte 범위에서 ACK된 구간과 재전송 가능한 미확인 구간을 표시합니다.
- 첫 RTT 표본과 timeout backoff 뒤 RTO를 계산합니다.
- 반복 packet을 캡처 중복·offload와 구분하지 않은 채 손실로 확정하지 않습니다.
