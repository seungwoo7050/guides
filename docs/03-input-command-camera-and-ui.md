# 입력, 명령, 카메라와 게임 UI

## 문제

키보드의 `Space`, gamepad의 South button과 touch gesture는 게임 규칙이 아닙니다. 장치 signal을 직접 `Jump()`에 연결하면 remapping, multiple local user, UI focus, replay, network, accessibility와 automated test가 모두 어려워집니다.

입력 시스템은 다음 변환을 소유해야 합니다.

```text
physical device event
→ logical action
→ context and focus resolution
→ gameplay command
→ simulation consumption
→ feedback and presentation
```

카메라와 UI 역시 player intention을 읽지만 gameplay 정본을 소유하면 안 됩니다. camera가 보지 못한 object가 존재하지 않는 것으로 처리되거나 HUD widget이 ammo 값을 소유하는 순간 기능 경계가 뒤집힙니다.

## 핵심 상태

### 입력의 층

| 층 | 예 | 저장·replay 여부 |
|---|---|---|
| device signal | key code, stick axis, touch id | 보통 아님 |
| control | button, axis, pointer position | 진단용 가능 |
| action | Jump, Confirm, Navigate, Look | mapping에 저장 |
| context | Gameplay, Menu, Vehicle, Spectator | 상태로 기록 |
| command | JumpPressed@tick42, Move(0.5,-1) | replay/network에 적합 |
| rule result | jump accepted, stamina reduced | authoritative state |

### local user와 device ownership

하나의 process에 여러 controller와 local user가 있을 수 있습니다. device id, local player id, online account id와 in-world player entity를 같은 id로 사용하지 않습니다.

### focus와 capture

- UI focus: navigation/confirm/cancel을 어떤 widget이 받는지
- pointer capture: drag 중 pointer가 경계 밖으로 나가도 누가 계속 받는지
- gameplay capture: mouse look 등 상대 입력을 누가 소유하는지
- text entry: IME와 system keyboard가 game hotkey보다 우선하는지
- modal context: pause/menu가 gameplay action을 block하는지

### camera state

카메라는 보통 다음 상태를 가집니다.

- target 또는 anchor
- desired transform
- constraints와 collision response
- smoothing history
- FOV·zoom·shake
- cut/blend state
- local-only presentation options

camera transform은 aim 또는 selection에 영향을 줄 수 있지만, authoritative ray와 rule input을 어떻게 만들지 명시해야 합니다.

## 설계 계약

### action mapping을 data로 만듭니다

```text
Action: Jump
Value: button edge
Contexts: Gameplay, Spectator
Bindings: Keyboard.Space, Gamepad.South
Rebindable: true
Consumes: true
```

binding과 rule을 분리하면 platform icon, remapping, conflict detection과 accessibility preset을 구현할 수 있습니다.

### command를 simulation 언어로 정의합니다

좋은 command는 device와 presentation을 모릅니다.

```json
{
  "tick": 412,
  "player": "p1",
  "sequence": 991,
  "kind": "move",
  "value": [0.5, -1.0]
}
```

server 또는 local simulation은 command가 현재 state에서 허용되는지 검증합니다. command가 “damage 100 적용”처럼 결과를 제출하지 않게 합니다.

### 입력 buffer 정책을 정합니다

게임 feel을 위해 edge를 짧게 buffer하거나 grace period를 둘 수 있습니다.

- jump buffer: landing 직전 입력을 몇 tick 보존하는가
- coyote time: edge를 떠난 뒤 몇 tick jump를 허용하는가
- combo queue: animation window와 command queue가 어떻게 만나는가
- repeat: UI navigation key repeat를 누가 생성하는가

이 값은 presentation trick이 아니라 gameplay rule이므로 authoritative state 또는 replayable command에 포함해야 합니다.

### camera와 rule query를 분리합니다

화면 중앙 조준이라도 다음을 구분합니다.

```text
camera ray
→ local candidate
→ gameplay aim command
→ authoritative query
→ accepted target/result
→ hit marker and camera feedback
```

카메라 clipping이나 frame interpolation이 hit rule을 바꾸지 않도록 합니다.

### UI는 projection입니다

HUD는 gameplay state의 projection이며 user intent를 command로 변환합니다.

- health widget이 health를 수정하지 않습니다.
- menu animation 완료가 transaction commit을 뜻하지 않습니다.
- optimistic UI를 사용하면 reject/correction path를 둡니다.
- gameplay state가 사라진 뒤 callback이 widget을 갱신하지 않게 subscription lifetime을 관리합니다.

## 대표 실패

### key code를 gameplay code에 직접 비교합니다

remap, gamepad, keyboard layout, accessibility와 automated input이 깨집니다.

### button 상태를 여러 subsystem이 polling합니다

UI와 gameplay가 동시에 confirm을 소비하거나 press edge를 여러 번 처리합니다. context resolver와 consumption order가 필요합니다.

### render frame마다 command를 생성합니다

120 FPS client가 30 FPS client보다 더 많은 fire/move command를 보낼 수 있습니다. simulation tick 또는 rate-limited sequence에 맞춥니다.

### camera smoothing state를 save 또는 server에 보냅니다

local presentation history가 authoritative state를 오염시킵니다. 필요한 aim intent와 camera option만 구분해 저장합니다.

### disconnect 뒤 stuck input이 남습니다

device removal, focus loss, background에서 held state를 release하거나 context reset하지 않으면 이동이 계속됩니다.

## 관찰과 검증

### input trace

```json
{
  "time_ms": 18342,
  "device": "gamepad-2",
  "local_user": "local-1",
  "context": "Gameplay",
  "control": "southButton",
  "phase": "pressed",
  "action": "Jump",
  "consumed_by": "PlayerCommandRouter",
  "command_tick": 1102
}
```

개인정보가 들어가는 text input은 그대로 기록하지 않습니다.

### 필수 테스트

- binding 변경 뒤 동일 action이 발생합니다.
- 두 local user의 device가 바뀌어도 entity ownership이 섞이지 않습니다.
- menu가 열린 동안 gameplay command가 생성되지 않습니다.
- focus loss와 device disconnect에서 held state가 해제됩니다.
- 한 press edge가 여러 fixed step에서 한 번만 소비됩니다.
- low FPS와 high FPS에서 같은 command sequence를 만듭니다.
- camera interpolation이 authoritative hit result를 바꾸지 않습니다.

### 접근성 검토

- 모든 주요 action을 remap할 수 있는가
- hold를 toggle로 대체할 수 있는가
- 동시에 눌러야 하는 chord를 줄일 수 있는가
- stick dead zone과 sensitivity를 조절할 수 있는가
- visual cue를 audio/haptic cue로 보완할 수 있는가
- 설정 화면 자체가 gameplay 전에 접근 가능한가

## 실습 연결

[입력과 명령 실습](../exercises/02-input-command-contract/README.md)에서 device event trace를 action·context·command로 변환하고 focus conflict를 해결합니다.

## 기존 브랜치와 경계

- browser event와 일반 UI 접근성은 `web-app`·`web-front-react-nextjs`가 소유합니다.
- 네트워크 command transport는 `computer-networks`가 소유합니다.
- 현재 문서는 게임 입력의 tick consumption, local user, camera와 gameplay command 경계를 소유합니다.

## 완료 기준

- device, action, context, command와 result를 구분합니다.
- remapping·focus·local multiplayer·disconnect를 포함한 입력 계약을 작성합니다.
- camera와 HUD를 authoritative gameplay state의 소비자로 유지합니다.
- frame rate와 device 종류가 달라도 동일한 command semantics를 검증합니다.
