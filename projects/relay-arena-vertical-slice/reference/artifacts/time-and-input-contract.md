# Time and input contract — reference exemplar

## clocks

| clock | owner | states using it | pause/suspend policy | evidence |
|---|---|---|---|---|
| real monotonic | platform/runtime | frame delta, profile duration, reconnect deadline | menu pause와 무관; suspend gap을 별도 사건으로 기록 | headless schedule delta는 monotonic duration 역할 |
| game time | match rules | best-time UI와 gameplay duration | menu/focus/suspend reason에 따라 정지 | actual pause route는 headless에서 미구현 |
| fixed tick | simulation | movement, dash cooldown, command/replay ordering | gameplay pause면 step하지 않음 | `FIXED_STEP_US=16667`, target tick 90 |
| render time | presentation | interpolation, animation/audio/VFX/UI | simulation과 분리; suspend 시 정지/재초기화 | headless는 render하지 않고 event만 산출 |
| server time/tick | network authority | tick window, snapshot/ack ordering | local pause에 종속되지 않음 | network fixture tick 99/101; transport clock은 미구현 |

## fixed-step policy

- fixed step: `16667us`.
- accumulator: clamped frame delta를 더하고 가능한 동안 fixed step을 실행한다.
- frame clamp: headless 상한 `250000us`.
- max catch-up: render frame당 `4` step.
- overload: 네 step 뒤 남은 whole-step backlog를 버리고 fraction만 보존하며 `dropped_simulation_us`를 기록한다.
- interpolation: 실제 renderer가 previous/current authoritative transforms를 읽어야 한다. canonical state와 gameplay collision에는 interpolation pose를 쓰지 않는다; headless에서는 측정하지 않는다.

## action → command

| action | context | value/edge | command schema | tick assignment | buffer/repeat | rejection |
|---|---|---|---|---|---|---|
| Move | Gameplay, p1 owner | integer vec2 axes `[-1000,1000]` | `{tick,player,sequence,kind:"move",value:[x,y]}` | fixture tick 1, 30 | latest continuous sample; fixed tick마다 현재 값 적용 | owner/phase/axis invalid |
| Dash | Gameplay, p1 owner | pressed edge `true` | `{...,kind:"dash",value:true}` | fixture tick 4 | edge 한 번; cooldown 8 ticks, nonzero move 필요 | duplicate/stale, phase, cooldown, zero move |
| Interact | Gameplay, p1 owner | target stable id | `{...,kind:"interact",value:"core-a|b|c"}` | fixture tick 12,45,70 | sequence별 한 번 | non-owner, duplicate/stale, phase, unknown/already-active target |

Headless reference는 device→action/context mapping 이후의 command부터 받는다. REQ-001 keyboard/gamepad remap과 REQ-003 focus cleanup은 CLI hash만으로 증명할 수 없다.

## focus/device cleanup

- focus loss: held Move를 zero sample로 만들고 buffered gameplay edge를 취소하며 UI/OS context가 control을 가진다.
- menu open: fixed simulation/game timer pause policy를 적용하고 Confirm/Pause 외 gameplay command를 만들지 않는다.
- device disconnect: 해당 local user의 held axes/buttons를 synthetic release로 정리한다.
- local user reassignment: old `(local_user, player)` command sequence/generation을 닫고 새 owner binding을 명시적으로 시작한다.

## Evidence and limits

| case | max steps | dropped | remainder | canonical result |
|---|---:|---:|---:|---|
| smooth/normal | 1 | 0us | 0us | hash `08b46cfd…6d0e` |
| jittered/normal | 2 | 0us | 7970us | same hash |
| hitch/normal | 4 | 116669us | 16663us | same hash |
| duplicate | 1 | 0us | 0us | sequence 3 rejected; same hash |

Manual review must inject actual OS focus/device events, confirm one edge is not consumed twice across catch-up steps, and verify camera interpolation does not change collision/rules. Hash equality proves only the headless integer simulation scope.
