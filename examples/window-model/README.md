# 송신 창 모델 예제

수신자가 광고한 창 `rwnd`와 송신자의 혼잡 창 `cwnd` 가운데 작은 값이 실제 송신 상한이 됩니다. 코드는 누적 ACK, 비행 중 바이트, RTT 평활값과 Reno 혼잡 창의 변화를 결정적으로 계산합니다.

```text
in_flight = next_sequence - send_base
effective_window = min(rwnd, cwnd)
available = max(0, effective_window - in_flight)
```

다음 명령은 세 세그먼트를 보낸 뒤 창이 닫히고, 누적 ACK가 도착하면 다시 보낼 수 있게 되는 흐름을 출력합니다.

```sh
python3 window_model.py
python3 -m unittest -v
```

`rwnd`는 수신 버퍼 보호를 위한 흐름 제어이고 `cwnd`는 네트워크 과부하를 줄이기 위한 혼잡 제어입니다. 둘을 같은 창이라고 부르더라도 목적과 갱신 주체는 다릅니다.

단위 검사는 첫 RTT 표본, RTO 지수 백오프, 느린 시작, 혼잡 회피, 세 번의 중복 ACK, 빠른 복구와 시간 제한 이후의 창 초기화를 확인합니다.

이 모델은 32비트 순서 번호 순환, SACK scoreboard와 실제 패킷 전송을 구현하지 않습니다. `receive_window=0`은 새 데이터 송신을 막지만 실제 TCP의 0 크기 창 탐색까지 재현하지 않습니다.
