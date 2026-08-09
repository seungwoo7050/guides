# Fixed-step replay 예제

Python 표준 라이브러리만으로 render frame과 fixed simulation tick을 분리하고, 서로 다른 frame schedule이 같은 ordered command trace를 같은 gameplay state로 만드는지 확인합니다.

이 예제는 실제 physics·renderer·engine을 구현하지 않습니다. 다음 계약만 작게 관찰합니다.

```text
frame delta clamp
→ accumulator
→ bounded fixed step
→ tick별 command 한 번 소비
→ fixed-point state update
→ canonical JSON
→ SHA-256 state hash
```

## 파일

- [`config.json`](config.json): fixed step, catch-up와 simulation 상수
- [`input-trace.json`](input-trace.json): tick command와 세 render frame schedule
- [`expected-state.json`](expected-state.json): 모든 schedule이 도달해야 하는 canonical state와 hash
- [`sim.py`](sim.py): 실행기와 검증기

## 실행

```sh
python3 sim.py --verify
```

사람이 결과를 읽으려면 다음을 실행합니다.

```sh
python3 sim.py --pretty
```

## 관찰할 점

- `smooth`, `jittered`, `overload`는 wall-clock frame 구성이 다릅니다.
- simulation command는 render frame이 아니라 integer tick에 연결됩니다.
- `overload`는 한 frame에서 실행할 step 수를 제한하고 버린 backlog를 따로 기록합니다.
- 세 schedule이 목표 tick까지 진행되면 gameplay state hash는 같습니다.
- `dropped_simulation_us`가 같다는 뜻은 아닙니다. 같은 gameplay tick 결과와 wall-time experience를 구분합니다.

## 의도적으로 단순화한 것

- 정수 fixed-point 좌표를 사용합니다.
- collision, physics engine, threading과 platform floating point 차이는 다루지 않습니다.
- command가 이미 tick과 sequence로 정렬됐다고 가정합니다.
- cross-platform bit-identical determinism을 주장하지 않습니다.

실제 프로젝트에서는 build/content version, random stream, subsystem checkpoint와 first-divergence report를 추가해야 합니다.
