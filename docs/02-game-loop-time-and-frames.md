# 게임 루프, 시간과 프레임

## 문제

게임은 “매 프레임 `update(delta)`를 호출한다”는 설명만으로는 정확히 동작하지 않습니다. 렌더링 주기와 simulation 주기가 다르고, physics·animation·audio·network·UI가 서로 다른 clock과 update phase를 사용합니다. 긴 frame, pause, background, slow motion과 server correction이 들어오면 하나의 `deltaTime`으로 모든 상태를 갱신하는 구현은 쉽게 깨집니다.

시간 설계의 목적은 FPS 숫자를 높이는 것이 아니라 다음을 결정하는 것입니다.

- 어떤 상태가 어느 clock을 사용합니까?
- 한 입력은 몇 개의 simulation step에서 소비됩니까?
- render가 느려져도 규칙 결과가 어떻게 유지됩니까?
- catch-up을 언제 포기하거나 simulation을 느리게 합니까?
- pause와 suspend에서 어떤 timer가 계속 진행됩니까?
- replay와 network가 같은 tick을 어떻게 식별합니까?

## 핵심 상태

### 여러 clock

| clock | 용도 | pause 영향 | 대표 실패 |
|---|---|---|---|
| monotonic real time | timeout, profile duration, telemetry | 보통 없음 | wall clock 변경에 영향 받음 |
| wall clock | 달력, daily event 표시 | 없음 | timezone·사용자 변경 |
| game time | gameplay timer, slow motion | 정책에 따라 있음 | UI·network timeout에 사용 |
| fixed simulation tick | physics·rule·replay | 명시적 | render frame과 혼동 |
| render time | interpolation·visual effect | frame마다 | 규칙 정본에 사용 |
| audio/DSP time | 정확한 audio scheduling | 별도 | frame clock과 drift |
| server time | authoritative event 순서 | client pause와 무관 | local clock을 신뢰 |

### variable frame와 fixed step

대표적인 fixed-step loop는 accumulator를 사용합니다.

```text
real frame delta를 측정
→ 허용 가능한 최대 delta로 clamp
→ accumulator에 더함
→ accumulator >= fixed_dt 동안 simulation step 실행
→ 남은 비율로 presentation interpolation
→ render
```

중요한 것은 코드 모양이 아니라 다음 invariant입니다.

- simulation은 정수 tick으로 진행됩니다.
- 같은 tick의 command는 정의된 순서로 한 번만 소비됩니다.
- 한 render frame에 0개, 1개 또는 여러 simulation step이 실행될 수 있습니다.
- catch-up step 수에는 상한이 있습니다.
- 상한을 넘었을 때 어떤 시간이 버려졌는지 telemetry로 알 수 있습니다.

### frame budget

목표 60 FPS의 nominal frame budget은 약 16.67ms이지만, 이를 subsystem마다 16.67ms씩 쓸 수 있다는 뜻으로 해석하면 안 됩니다. main thread, render submission, GPU, streaming, audio와 background job이 서로 의존합니다. 평균 frame time만으로는 hitch를 숨깁니다.

필요한 측정은 예를 들면 다음과 같습니다.

- median, p95, p99 frame time
- longest hitch와 발생 scene
- fixed steps per frame
- main/render/GPU critical path
- input-to-photon 또는 input-to-state latency
- loading 중 frame spike
- thermal throttling 이후 지속 성능

## 설계 계약

### step 입력을 명시합니다

```text
Step(tick, fixed_dt, ordered_commands, previous_state) -> next_state, events
```

simulation step이 global clock, renderer, random device와 file I/O를 직접 읽지 않게 할수록 replay와 테스트가 쉬워집니다.

### command sampling과 consumption을 분리합니다

raw input은 render frame 사이에 여러 번 들어올 수 있습니다. input layer는 event를 수집하고 simulation은 tick 경계에서 command snapshot을 소비합니다.

- continuous axis는 sampling 정책을 정합니다.
- pressed/released edge는 소비될 tick을 정합니다.
- 한 render frame에 여러 step이 실행돼도 edge가 중복 적용되지 않게 합니다.
- frame에 step이 없더라도 입력을 잃지 않습니다.

### catch-up 정책을 문서화합니다

긴 frame 뒤 무제한 step을 실행하면 더 긴 frame을 만들어 악순환이 생깁니다. 다음 중 하나 또는 조합을 선택합니다.

- frame delta clamp
- maximum steps per frame
- simulation slowdown
- low-priority system skip
- network snapshot resync
- overload state와 quality degradation

정책은 정확도, 사용자 경험과 CPU 예산의 trade-off입니다.

### timer의 clock을 타입 또는 API로 드러냅니다

`Timer(5.0)`만으로는 부족합니다.

```text
GameplayTimer(game_time, pauses=true)
NetworkDeadline(monotonic_time, pauses=false)
UiAnimation(render_time, respects_menu_pause=false)
DailyReset(wall_clock + server authority)
```

### deterministic이라는 범위를 제한합니다

“결정적”은 다음을 모두 자동 보장하지 않습니다.

- 다른 CPU·compiler·build에서도 bit-identical
- physics engine 결과 동일
- thread scheduling 독립
- floating-point 연산 순서 독립
- content와 schema version 독립

프로젝트는 필요한 범위를 정합니다. 같은 build와 platform에서 replay 가능한 수준인지, cross-platform lockstep이 필요한지 구분합니다.

## 대표 실패

### variable delta를 반복 곱해 중요한 규칙을 갱신합니다

낮은 FPS에서 collision tunneling, cooldown drift와 순서 차이가 커집니다. fixed step 또는 closed-form integration이 필요한 상태를 구분합니다.

### pause가 한 boolean입니다

menu pause, cinematic pause, network wait, photo mode와 OS suspend는 서로 다른 system을 멈춥니다. pause reason의 set과 system별 policy를 사용합니다.

### wall clock으로 duration을 측정합니다

사용자가 시간을 바꾸거나 NTP가 조정하면 timeout이 뒤로 갑니다. duration은 monotonic clock을 사용합니다.

### random seed만 기록하면 replay 가능하다고 가정합니다

iteration order, thread completion, physics contact order와 content version이 다르면 seed가 같아도 결과가 달라집니다.

### render frame id를 simulation tick으로 사용합니다

variable refresh, frame skip과 headless server에서 의미가 달라집니다. 두 식별자를 분리합니다.

## 관찰과 검증

### trace 필드

```json
{
  "render_frame": 812,
  "real_delta_ms": 48.2,
  "clamped_delta_ms": 33.3,
  "steps_executed": 2,
  "first_tick": 1640,
  "last_tick": 1641,
  "accumulator_ms": 7.4,
  "dropped_simulation_ms": 0.0
}
```

### 결정적 fixture

- initial state를 canonical JSON 또는 binary로 고정합니다.
- tick별 ordered command를 기록합니다.
- 각 tick 또는 checkpoint의 state hash를 비교합니다.
- hash mismatch가 나면 첫 diverging tick을 찾습니다.
- random stream과 content version을 subsystem별로 기록합니다.

### overload 테스트

- 8ms, 16ms, 40ms, 200ms frame sequence를 주입합니다.
- max step count를 넘겼을 때 무한 catch-up하지 않는지 봅니다.
- pause 중 gameplay timer와 network timeout의 차이를 검사합니다.
- frame rate가 달라도 일정 tick 뒤 gameplay 결과가 같은지 확인합니다.

[`fixed-step-replay`](../examples/fixed-step-replay/README.md)가 가장 작은 실행 예제를 제공합니다.

## 실습 연결

[시간 단계 분석 실습](../exercises/01-time-step-analysis/README.md)에서 frame trace를 fixed-step 정책에 따라 계산하고 overload decision을 작성합니다. Capstone에서는 동일 input trace의 replay hash와 pause policy를 제출합니다.

## 기존 브랜치와 경계

- scheduling, timer interrupt와 process clock의 원리는 `operating-systems`가 소유합니다.
- CPU pipeline과 cache cost는 `computer-architecture`가 소유합니다.
- 현재 문서는 game time, fixed tick, render frame과 player experience의 계약을 소유합니다.

## 완료 기준

- 최소 다섯 종류의 clock과 사용처를 구분합니다.
- variable frame과 fixed simulation을 accumulator·상한·interpolation까지 설명합니다.
- input edge가 0개 또는 여러 step이 있는 frame에서 한 번만 소비되게 설계합니다.
- pause, overload와 replay divergence를 fixture로 검증합니다.
