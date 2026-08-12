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

## 권장 구현 순서

이 예제 전체가 하나의 annotation scope입니다. 다음 번호는 Git history나 runtime call order가 아니라, 같은 관찰 프로그램을 처음부터 만든다고 가정한 **학습용 권장 구현 순서**입니다. Python 표준 라이브러리 파일을 바로 실행하므로 project generator, dependency 설치나 framework 초기화에 해당하는 Implementation 0은 없습니다. JSON fixture는 주석을 허용하지 않으므로 관련 책임은 이 표와 `sim.py`의 단일 authoritative anchor에서 설명합니다.

| 순서 | 파일·symbol | 먼저 고정할 책임 | 다음 단계가 의존하는 결과 |
|---:|---|---|---|
| 1 | `config.json`, `input-trace.json`, `load_json()`, `validate_inputs()` | 외부 입력 schema와 command identity를 state 변경 전에 거부 | 검증된 정수 시간·명령·schedule |
| 2 | `canonical_bytes()`, `state_hash()` | gameplay state의 canonical JSON byte/hash 계약 | schedule 간 비교 가능한 state identity |
| 3 | `commands_by_tick()` | command를 tick과 sequence 순서로 색인 | frame과 분리된 입력 소비 순서 |
| 3-1 | `apply_command()` | move/dash의 accepted·rejected 전이 | 한 tick에서 적용할 결정적 command 결과 |
| 4 | `step()` | command→fixed-point 이동→cooldown→tick의 단일 writer 순서 | 독립적으로 반복 가능한 fixed tick |
| 5 | `run_schedule()` | clamp·accumulator·catch-up 상한·backlog 폐기 | hitch를 포함한 bounded simulation run |
| 6 | `run_all()` | 동일 trace를 schedule별로 독립 실행 | schedule별 state와 frame evidence |
| 6-1 | `verify()` | expected state/hash, schedule 동등성과 overload 방향 검사 | 관찰 예제가 주장할 수 있는 deterministic 범위 |
| 7 | `main()` | 기본 fixture, 출력과 실패 exit status를 CLI로 조립 | `python3 sim.py --verify` public command |

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
