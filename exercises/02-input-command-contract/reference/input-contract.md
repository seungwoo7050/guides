# 입력과 명령 계약 기준 예시

## 식별자와 소유권

| 식별자 | 의미 | owner | lifetime | 다른 id와 같지 않은 이유 |
|---|---|---|---|---|
| device id | 물리 연결 하나(`keyboard-1`, `gamepad-1`, `gamepad-2`) | platform input service | 연결부터 disconnect까지 | 재연결·교체될 수 있고 여러 device가 한 local user에 속할 수 있다. |
| local user id | 이 process 안의 입력·UI 사용자(`local-1`, `local-2`) | local user/input association service | local session 참가부터 제거까지 | account나 entity가 없어도 존재하며 device 재배정 뒤에도 유지될 수 있다. |
| player entity id | authoritative match object(`player-a`, `player-b`) | match/world state | entity spawn부터 match teardown까지 | scene reload나 respawn으로 runtime object가 바뀌며 local user와 1:1이라는 보장이 없다. |

fixture association은 다음과 같다.

```text
keyboard-1 ─┐
gamepad-1  ─┴→ local-1 → player-a
gamepad-2  ───→ local-2 → player-b
```

command와 UI intent에는 물리 device가 아니라 `local_user`와 필요한 경우 `player`만 남긴다. replay와 network consumer는 원래 key나 controller 종류를 알 필요가 없다.

## context resolver

| active contexts | focus owner | 허용 action | 차단 action | consumption order |
|---|---|---|---|---|
| Gameplay | `game-view` | `Move`, `Dash`, `Interact`, `Pause` | `Navigate`, `Confirm` | `Gameplay` |
| Gameplay + Menu | `pause-menu` | `Navigate`, `Confirm`, `Pause` | gameplay `Move`, `Dash`, `Interact` | `Menu`가 먼저 소비하고 남은 event만 `Gameplay`가 본다. |
| Gameplay + Menu + TextEntry | `profile-name` | text/IME, 그 뒤 Menu navigation·confirm | text key의 gameplay shortcut | `TextEntry → Menu → Gameplay` |
| OS focus loss | `os-lost` | synthetic cleanup과 device lifecycle만 허용 | 모든 새 gameplay/UI action | held state를 먼저 neutralize하고 이후 raw action event는 무시한다. |

`Gamepad.South`는 `Dash`와 `Confirm`에 함께 binding되어 있다. sequence 4는 Menu가 더 높은 active context이므로 `Confirm` 하나만 만들며 `Dash`를 동시에 만들지 않는다. sequence 6의 `E`는 TextEntry가 소비하므로 `Interact`를 만들지 않는다.

## command schema

- tick assignment: event가 도착한 시각 이후 첫 60Hz 경계에 `ceil((time_ms - session_start_ms) * 60 / 1000)`으로 배정한다. 이 규칙에서 raw event 1·2·3·4·5·9·10은 각각 tick `6`, `9`, `14`, `56`, `72`, `141`, `144`다.
- sequence scope: command trace 전체에서 단조 증가한다. 동일 tick 114의 focus-loss cleanup은 sequence 6, 7 순서로 player-a, player-b에 적용한다.
- axis quantization/sampling: fixture의 `W`를 normalized `[0.0,1.0]`, LeftStick을 제공된 `[0.6,0.0]`으로 해석하고 local user별 최신 sample 하나만 tick 경계에 낸다. production integer quantization은 별도 schema version으로 고정해야 한다.
- edge buffer: `Dash`, `Interact`, `Confirm`, `Pause` press는 해당 context에서 한 command만 생성하며 render frame repeat를 만들지 않는다.
- rejected command evidence: 모든 raw event는 [`command-trace.json`](command-trace.json)의 `event_decisions`에서 `consumed` 또는 `ignored`로 끝난다. sequence 6은 TextEntry가 소비해 command가 없고 sequence 7은 focus가 없어 ignored다.

`commands[].channel=gameplay`은 simulation intent이고 `channel=ui`는 UI navigation intent다. UI command도 device-independent지만 authoritative gameplay 결과를 직접 쓰지 않는다.

## cleanup 정책

- focus loss: 1900ms/tick 114에서 두 local user의 held `Move`를 `[0,0]`으로 만들고 pending gameplay edge를 비운다. cleanup은 여러 번 호출해도 같은 neutral state다.
- device disconnect: 해당 device의 axis contribution과 association만 제거한다. sequence 8의 `gamepad-2` 제거 시 player-b는 focus-loss cleanup으로 이미 neutral이므로 두 번째 Move command를 만들지 않는다.
- local user removal: 연결된 모든 device association, held sample, buffered edge와 UI focus token을 제거한 뒤 player mapping을 해제한다.
- scene unload: command producer를 먼저 닫고 미소비 command를 generation별로 폐기한 뒤 player entity handle을 해제한다. local user와 device association 자체는 process/session 정책에 따라 남을 수 있다.

release event가 OS focus loss 뒤 늦게 도착해도 이미 정리된 state를 되살리지 않는다. focus regain 뒤에는 sequence 9처럼 새로운 press가 있어야 Move가 다시 non-zero가 된다.

## camera/UI 경계

- camera가 생성하는 intent: camera ray 또는 aim direction·selection candidate처럼 local presentation에서 계산한 입력값
- UI가 생성하는 intent: `ui_confirm`, pause 요청, menu selection과 settings 변경 요청
- authoritative result의 owner: local authoritative simulation 또는 server의 match state
- optimistic presentation correction: UI/camera는 pending 표시를 할 수 있지만 reject/correction을 받으면 authoritative snapshot으로 되돌리고 device event를 결과처럼 재전송하지 않는다.

camera transform, widget animation과 물리 device 종류는 gameplay state의 정본 필드가 아니다. aim이나 selection에 필요하면 stable command field로 변환한 뒤 authoritative query가 결과를 결정한다.

## fixture 판정 요약

| source sequence | 판정 | evidence |
|---:|---|---|
| 1 | consumed | player-a Move, tick 6 |
| 2 | consumed | player-b Move, tick 9 |
| 3 | consumed | player-a Dash, tick 14 |
| 4 | consumed | Menu Confirm만 생성, tick 56 |
| 5 | consumed | Menu Confirm, tick 72 |
| 6 | consumed without command | TextEntry/IME가 E를 선점 |
| 7 | ignored | OS focus 없음; tick 114 cleanup이 이미 적용됨 |
| 8 | consumed without gameplay command | gamepad-2 association 제거, cleanup은 idempotent |
| 9 | consumed | focus 복귀 뒤 player-a Move, tick 141 |
| 10 | consumed | player-a Interact, tick 144 |

## 사람이 확인할 판단

- keyboard `W`의 축 방향과 float quantization은 action-map fixture에 세부 schema가 없어 이 예시가 명시적으로 추가한 가정이다.
- UI intent를 fixed tick 번호로 기록하는 것은 ordering/replay를 위한 선택이다. 실제 UI가 render-time queue를 사용한다면 gameplay command와 별도 trace에서 같은 source sequence를 보존해야 한다.
- 자동 비교는 context 선택과 cleanup trace를 확인할 수 있지만 remapping UX, IME 품질과 correction의 시각적 안정성은 직접 검토해야 한다.
