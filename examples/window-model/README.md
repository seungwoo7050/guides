# 송신 창 모델 예제

수신자가 광고한 창 `rwnd`와 송신자의 혼잡 창 `cwnd` 가운데 작은 값이 실제 송신 상한이 됩니다. 코드는 누적 ACK, 비행 중 바이트, RTT 평활값과 Reno 혼잡 창의 변화를 결정적으로 계산합니다.

```text
in_flight = next_sequence - send_base
effective_window = min(rwnd, cwnd)
available = max(0, effective_window - in_flight)
```

## 권장 구현 순서

아래 번호는 이 예제 프로젝트 전체의 학습 지향 권장 구현 순서입니다. 파일의 줄 순서나 실제 과거 작성 순서를 뜻하지 않으며, 각 단계는 `window_model.py`의 source annotation 한 곳과 연결됩니다.

| 번호 | 파일·symbol | 먼저 고정하는 책임 |
|---:|---|---|
| 1 | `window_model.py::WindowSender` | 송신 sequence와 두 창의 소유 상태·입력 불변식 |
| 1-1 | `window_model.py::in_flight`, `effective_window`, `available` | 저장 상태에서 계산하는 파생 송신 가능량 |
| 1-2 | `window_model.py::send_one_segment`, `acknowledge` | 송신과 누적 ACK가 sequence 경계를 바꾸는 규칙 |
| 2 | `window_model.py::RttEstimator` | RTT 표본, 평활값, RTO 하한·상한과 backoff |
| 3 | `window_model.py::RenoController` | congestion window와 slow-start threshold 상태 |
| 3-1 | `window_model.py::RenoController.acknowledge` | 새 ACK·중복 ACK·fast recovery 전이 |
| 3-2 | `window_model.py::RenoController.timeout` | timeout 뒤 혼잡 상태 초기화 |
| 4 | `window_model.py::demo`, `main` | 작은 결정적 사건 순서와 관찰 출력 조립 |

다음 명령은 세 세그먼트를 보낸 뒤 창이 닫히고, 누적 ACK가 도착하면 다시 보낼 수 있게 되는 흐름을 출력합니다.

```sh
python3 window_model.py
python3 -m unittest -v
```

`rwnd`는 수신 버퍼 보호를 위한 흐름 제어이고 `cwnd`는 네트워크 과부하를 줄이기 위한 혼잡 제어입니다. 둘을 같은 창이라고 부르더라도 목적과 갱신 주체는 다릅니다.

단위 검사는 첫 RTT 표본, RTO 지수 백오프, 느린 시작, 혼잡 회피, 세 번의 중복 ACK, 빠른 복구와 시간 제한 이후의 창 초기화를 확인합니다.

이 예제에는 별도 reference 답안이 없습니다. 위 출력과 단위 검사에서 `in_flight`, RTO와 Reno 상태가 예상한 사건 뒤에만 바뀌는지가 기대 증거입니다.

이 모델은 32비트 순서 번호 순환, SACK scoreboard와 실제 패킷 전송을 구현하지 않습니다. `receive_window=0`은 새 데이터 송신을 막지만 실제 TCP의 0 크기 창 탐색까지 재현하지 않습니다.
