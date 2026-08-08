# 흐름 제어와 혼잡 제어

TCP의 흐름 제어와 혼잡 제어는 모두 sender가 한 번에 내보낼 수 있는 바이트를 제한하지만 보호 대상이 다릅니다. 흐름 제어는 느린 수신자의 buffer를 보호하고, 혼잡 제어는 경로의 queue와 다른 flow가 공유하는 네트워크를 보호합니다.

## 학습 목표

- `rwnd`와 `cwnd`가 보호하는 자원과 유효 송신 창을 구분합니다.
- ACK, loss와 application queue가 전송률에 미치는 영향을 연결합니다.

## 선행 개념

[재전송과 슬라이딩 윈도](03-retransmission-rtt-and-sliding-windows.md)의 비행 중 byte와 누적 ACK 상태가 필요합니다.

## 두 window를 분리하기

```text
rwnd: receiver가 광고한 수신 가능량
cwnd: sender가 경로 상태에서 추정한 혼잡 허용량
실제 상한: min(rwnd, cwnd)
```

이미 비행 중인 바이트를 빼면 지금 새로 보낼 수 있는 양이 됩니다.

```text
available = max(0, min(rwnd, cwnd) - in_flight)
```

수신 애플리케이션이 읽지 않아 버퍼가 차면 `rwnd`가 줄어들 수 있습니다. 경로에서 손실이나 ECN 혼잡 신호가 보이면 송신자의 `cwnd`가 줄어들 수 있습니다. 두 값의 원인을 로그에서 구분해야 합니다.

## 수신 창과 0 크기 창

TCP 헤더의 Window 필드는 ACK를 보내는 종단점이 현재 더 받을 수 있는 범위를 광고합니다. Window Scale 옵션을 핸드셰이크에서 협상하면 더 큰 수신 창을 표현할 수 있습니다.

receiver가 zero window를 광고하면 sender는 일반 데이터를 멈추고 window가 다시 열렸는지 확인하는 probe를 보낼 수 있습니다. zero-window가 길게 유지되면 네트워크 대역폭보다 수신 application의 처리 정체, pause 또는 memory pressure를 먼저 봅니다.

애플리케이션 버퍼를 무한히 키울 수는 없습니다. 큰 버퍼는 일시적 폭주를 흡수하지만 지속적인 생산·소비 속도 차이를 숨기고 지연과 메모리 사용량을 늘립니다. 상위 큐와 역압 정책이 필요합니다.

## congestion window는 ACK와 혼잡 신호로 변합니다

연결 초기에 경로 용량을 모르면 sender는 작은 window에서 시작해 ACK를 받으며 전송량을 늘립니다. 전통적인 설명은 다음 단계로 나뉩니다.

- 느린 시작: ACK된 데이터에 따라 빠르게 창을 늘립니다.
- 혼잡 회피: 더 완만하게 증가합니다.
- 손실 또는 ECN: 혼잡 신호로 보고 전송량을 줄입니다.
- 빠른 복구: 일부 손실 뒤 모든 비행 데이터를 비우지 않고 회복하려고 합니다.

정확한 증가·감소 수식은 Reno, CUBIC와 다른 congestion control에 따라 다릅니다. 현대 Linux에서 특정 알고리즘이 기본이라고 모든 OS와 배포판에 일반화하지 말고 `sysctl`과 socket 상태를 확인하세요.

CUBIC은 window를 시간의 cubic 함수로 성장시켜 bandwidth-delay product가 큰 경로에서 Reno보다 빠르게 이전 전송률 근처로 돌아가도록 설계되었습니다. RFC 9438은 CUBIC을 표준화하지만 실제 구현은 pacing, HyStart와 kernel 버전의 추가 동작을 가질 수 있습니다.

## loss는 혼잡의 완벽한 증거가 아닙니다

전통 TCP는 손실을 혼잡 신호로 사용하지만 패킷은 무선 오류, 정책에 따른 폐기와 경로 전환으로도 사라질 수 있습니다. 반대로 큐가 과도하게 길어져 지연이 커져도 아직 패킷이 폐기되지 않을 수 있습니다.

Explicit Congestion Notification은 ECN-capable endpoint와 장비가 packet을 버리지 않고 congestion experienced 표시를 전달하게 합니다. sender는 이를 loss와 유사한 congestion signal로 반응할 수 있습니다. 경로의 모든 장비가 ECN을 제대로 전달하지 않으면 fallback과 진단이 필요합니다.

## bandwidth-delay product와 pipe 채우기

경로 용량이 `100 Mbps`, RTT가 `100 ms`라면 한 RTT 동안 약 `10 Mb`, 즉 약 `1.25 MB`가 경로에 비행할 수 있습니다. window가 이보다 훨씬 작으면 링크를 채우기 어렵고, 지나치게 큰 queue에 모두 넣으면 latency가 증가합니다.

```text
BDP = bottleneck bandwidth × RTT
```

BDP는 순간적으로 고정된 값이 아닙니다. 무선 전송률, 공유 트래픽과 경로가 바뀌면 병목과 RTT가 달라집니다. 한 번의 속도 측정으로 영구적인 창 값을 정하지 않습니다.

## 버퍼블로트와 능동 큐 관리

큰 queue는 drop을 줄여 throughput이 좋아 보일 수 있지만 오래된 packet이 줄을 서며 interactive latency가 크게 늘어납니다. 이를 bufferbloat라고 부릅니다.

CoDel, FQ-CoDel과 PIE 같은 능동 큐 관리는 큐 지연을 제어하고, 공정 큐잉은 흐름 사이의 간섭을 줄이는 데 사용됩니다. 종단점 혼잡 제어만 바꾸는 것으로 모든 병목 큐 문제를 해결할 수 없습니다.

## 실행 가능한 송신 창 모델

```sh
cd examples/window-model
python3 window_model.py
python3 -m unittest -v
```

예제는 `cwnd=3000`, `rwnd=4000`, MSS 1000에서 세 segment를 보낸 뒤 `in_flight=3000`이 되어 멈춥니다. 누적 ACK가 1500바이트를 새로 확인하면 같은 양을 다시 보낼 수 있습니다.

실제 TCP에서는 세그먼트 크기, 지연 ACK, SACK, 페이싱과 손실 복구가 추가됩니다. 이 모델의 목적은 두 창과 비행 중 바이트의 관계를 분리하는 것입니다.

## 애플리케이션 backpressure까지 연결하기

TCP가 송신 소켓 쓰기를 늦추거나 버퍼를 채워도 애플리케이션이 생산을 계속하면 사용자 공간 큐가 무한히 커질 수 있습니다. 다음 경계를 함께 설계하세요.

1. 한 요청과 한 연결의 최대 대기 byte를 정합니다.
2. queue가 가득 찼을 때 producer를 늦추거나 요청을 거부합니다.
3. 제한 시간과 취소가 큐 안의 작업까지 제거하는지 확인합니다.
4. retry가 congestion 중 traffic을 더 늘리지 않도록 backoff와 jitter를 둡니다.
5. 처리량뿐 아니라 큐 깊이, RTT, 재전송과 꼬리 지연을 측정합니다.

네트워크 역압과 업무 큐의 역압은 같은 메커니즘이 아니지만, 제한된 소비 속도를 생산자에게 전달해야 한다는 공통 구조를 가집니다.

## 연결 실습

[송신 창 모델](../../examples/window-model/README.md)에서 `min(rwnd, cwnd)`와 slow start·timeout 전이를 실행합니다.

## 완료 기준

- 주어진 `rwnd`, `cwnd`, 비행 중 byte에서 추가 전송 가능량을 계산합니다.
- zero window와 congestion loss가 요구하는 복구 행동을 구분합니다.
- 처리량 주장에 RTT, queue depth, loss와 반복 조건을 함께 기록합니다.
