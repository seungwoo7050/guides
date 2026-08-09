# 시간 단계 분석 기준 예시

## 사용한 정책과 가정

- policy id: `relay-time-v1`
- 확인 가능한 사실: fixed step은 `16,667us`, frame delta 상한은 `100,000us`, render frame당 최대 step은 4개다. 상한 뒤 남은 backlog는 whole step만 버리고 fraction은 보존한다.
- 계산을 위해 추가한 가정: `initial_tick: 120`은 **다음에 실행할 tick**이다. frame의 입력을 먼저 context로 분류한 뒤 그 frame의 fixed step에서 sequence 순서로 소비한다. Menu에서 허용된 edge는 fixed clock이 재개될 때까지 보존하고, Menu에서 차단된 event는 도착 시 버린다.
- 미확인 항목: fixture는 Menu용 `Confirm`을 render/UI clock에서 즉시 처리하는 별도 경로를 정의하지 않는다. 따라서 이 예시는 literal rule인 `consume_once_at_first_eligible_fixed_tick`을 적용해 sequence 4를 tick 128에 소비한다. 실제 제품이 UI clock에서 처리한다면 sequence 4는 gameplay command trace에서 제거하고 그 별도 trace를 남겨야 한다.

전체 frame 계산은 [`frame-analysis.csv`](frame-analysis.csv)에 있다. 실행된 tick은 `120`부터 `129`까지 10개이며 마지막 상태의 다음 tick은 `130`이다.

```text
fixed-clock delta 합계 = 204000us
10 steps              = 166670us
dropped backlog       =  33334us
remaining fraction    =   3996us
합계                   = 204000us
```

## clock 표

| 상태/동작 | clock | pause reason별 동작 | 근거 |
|---|---|---|---|
| match timer | `game_time` | `menu`, `focus_loss`, `suspend`에서 멈춘다. | `time-policy.json`의 `game_time.uses`와 `pauses_for` |
| network deadline | `real_monotonic` | 어떤 pause reason에서도 계속 진행한다. | `real_monotonic.pauses_for`가 빈 배열이다. |
| movement | `fixed_tick` | `menu`, `focus_loss`, `suspend`에서 accumulator에 시간을 더하지 않는다. | `fixed_tick.uses`와 `pauses_for` |
| camera blend | `render_time` | `menu`에서는 진행하고 `suspend`에서만 멈춘다. | `render_time.uses`와 `pauses_for` |

frame 5와 6의 `clamped_delta_us`는 real delta clamp 결과인 `16,667`이지만 fixed clock이 Menu로 멈췄으므로 accumulator 증분은 0이다. real monotonic network deadline과 render-time camera blend는 같은 두 frame에도 진행한다.

## 입력 보존과 소비

- continuous action sampling: sequence 1의 `Move=[1000,0]`은 frame 1에서 보존되어 tick 120에 적용되고, 새 sample이 올 때까지 held state로 유지된다. sequence 6의 `[0,0]`은 frame 7에서 이전 sample을 교체하고 tick 128에 적용된다.
- edge queue: sequence 2 `Dash`는 tick 120, sequence 3 `Interact`는 catch-up의 첫 tick인 124, sequence 4 `Confirm`은 pause 뒤 첫 tick인 128에서 각각 한 번 소비된다.
- menu/focus context: Menu는 `Dash`, `Interact`, `Move`를 차단하므로 frame 6의 sequence 5는 queue에 넣지 않는다. `Confirm`은 허용하므로 sequence 4를 보존한다.
- catch-up 중 중복 방지: edge를 queue에서 꺼낸 즉시 consumed로 표시한다. frame 3과 4가 여러 step을 실행해도 sequence 2와 3은 뒤 tick에 다시 나타나지 않는다.

step이 없는 frame 1과 7은 입력을 버리지 않는다. CSV의 `consumed_sequences=none`은 “입력이 없었다”가 아니라 “아직 simulation이 소비하지 않았다”는 뜻이다.

## overload 판정

- 첫 overload frame: 4
- 실행한 step 수: 4 (`124-127`)
- 보존한 accumulator: `3,330us`
- 버리거나 느려진 시간: `33,334us`, 즉 정확히 fixed step 2개
- telemetry event: `fixed_step_overload(frame=4, raw_delta_us=200000, clamped_delta_us=100000, steps=4, dropped_us=33334, remaining_us=3330)`
- replay/player experience 영향: 무제한 catch-up은 피하지만 simulation clock이 real time보다 `33,334us` 뒤처진다. replay가 tick command로 재현 가능하려면 clamp·drop 정책과 overload event를 build/content version과 함께 기록해야 한다.

frame 4 계산은 다음과 같다.

```text
3332 + 100000 = 103332
103332 - 4 * 16667 = 36664
36664 - 2 * 16667 = 3330
```

## 실패 검증

| 실패 주입 | 보호할 invariant | 예상 evidence | recovery |
|---|---|---|---|
| 200ms hitch | 한 render frame은 4 step보다 많이 실행하지 않고 최종 accumulator는 한 step보다 작다. | frame 4의 `executed_ticks=124-127`, `dropped_us=33334`, `accumulator_after_us=3330` | overload telemetry를 남기고 필요하면 server snapshot resync 또는 품질 저하 정책을 적용한다. |
| pause 중 input | 허용된 edge는 잃거나 반복하지 않고 차단된 action은 gameplay queue를 오염시키지 않는다. | sequence 4는 tick 128에 한 번만 나타나고 sequence 5는 어느 tick에도 나타나지 않는다. | context가 바뀔 때 stale edge를 명시적으로 만료하거나 UI 전용 trace로 이동한다. |
| step 없는 frame | 최신 axis와 edge queue는 다음 eligible tick까지 유지된다. | sequence 1은 frame 1 뒤 tick 120, sequence 6은 frame 7 뒤 tick 128에 소비된다. | queue/sample 상태를 render-frame 지역 변수가 아닌 input owner에 보존한다. |

## 사람이 확인할 판단

- Menu `Confirm`을 fixed tick까지 보존하는 정책이 실제 UI의 responsiveness와 맞는지 결정해야 한다.
- `33,334us`를 버리는 정책이 경쟁 게임의 authoritative server와 허용 가능한 drift인지 별도 playtest와 telemetry로 확인해야 한다.
- 이 계산은 integer microsecond fixture의 계약만 증명하며 실제 engine physics나 cross-platform bit determinism을 증명하지 않는다.
