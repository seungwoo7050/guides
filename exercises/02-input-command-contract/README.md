# 02. 입력과 명령 계약

## 목표

device event, local user, context와 action map을 읽고 simulation이 소비할 command trace를 설계한다. UI focus, remapping, focus loss와 여러 local user가 gameplay state를 오염시키지 않게 한다.

## 입력

- [`inputs/action-map.json`](inputs/action-map.json)
- [`inputs/device-events.json`](inputs/device-events.json)
- [`inputs/context-timeline.json`](inputs/context-timeline.json)

## 제출

- [`template/input-contract.md`](template/input-contract.md)
- [`template/command-trace.json`](template/command-trace.json)

template의 빈 표와 `TODO` 문자열은 의도적인 미완성 starter다. 그대로 JSON parse가 되더라도 command 계약을 구현한 것이 아니다. 자신의 trace를 먼저 작성한 뒤 다음 완성 예시와 비교한다.

- [`reference/input-contract.md`](reference/input-contract.md): identifier·context·cleanup·UI 경계의 기준 판단
- [`reference/command-trace.json`](reference/command-trace.json): 모든 fixture event의 판정과 device-independent command evidence

## 필수 결정

- device와 local user의 association
- context 우선순위와 event consumption
- action→command 변환과 tick/sequence
- continuous axis sampling과 edge buffering
- focus loss/device disconnect의 held-state cleanup
- camera/UI가 authoritative state에 제출하는 정보

## 기계 검증 가능한 evidence

검증기는 reference JSON에서 다음 공개 결과를 확인할 수 있다.

- 10개 raw event가 `event_decisions`에서 누락·중복 없이 `consumed` 또는 `ignored`로 분류된다.
- gameplay/UI command tick은 `6, 9, 14, 56, 72, 114, 114, 141, 144`이고 command sequence는 1부터 9까지 유일하다.
- sequence 4의 shared `Gamepad.South`는 Menu `Confirm` 하나만 만들고 `Dash`를 만들지 않는다.
- sequence 6은 TextEntry가 소비해 `Interact` command가 없고, sequence 7은 OS focus loss 상태에서 ignored다.
- focus loss는 tick 114에 player-a와 player-b의 held Move를 모두 `[0,0]`으로 만들며, 뒤의 gamepad-2 disconnect는 중복 movement command를 만들지 않는다.
- sequence 9와 10은 focus 복귀 뒤 각각 player-a의 Move와 Interact로 생성된다.

JSON의 구조 검사는 binding 변경 UX, IME 동작이나 optimistic correction 품질까지 자동 증명하지 않는다.

## 대표 오답

- `Space`를 gameplay의 `Dash()` 함수에 직접 연결한다.
- UI와 gameplay가 같은 Confirm event를 동시에 소비한다.
- render FPS마다 Move command를 생성한다.
- device id, local account와 player entity id를 하나로 사용한다.
- focus loss 때 held Move가 그대로 남는다.

## 사람 검토 질문

1. binding을 바꿔도 command semantics가 유지되는가?
2. text input/IME가 gameplay shortcut보다 우선하는가?
3. command가 결과가 아니라 intent를 표현하는가?
4. replay와 network가 device 종류를 알 필요가 없는가?
5. disconnect 뒤 어떤 synthetic release/reset event가 생기는가?

## 사람 검토 루브릭

| 항목 | 합격 evidence | 보완이 필요한 상태 |
|---|---|---|
| identifier/association | 세 id의 owner·lifetime을 구분하고 모든 device를 정확한 local user와 player에 연결한다. | device id를 player entity id로 직접 사용한다. |
| context resolution | shared binding, Menu 우선순위, TextEntry 선점과 OS focus loss를 event별로 설명한다. | UI와 gameplay가 sequence 4 또는 6을 동시에 소비한다. |
| command semantics | tick·sequence·axis·edge가 device-independent intent이고 raw event 10개가 모두 판정된다. | render FPS마다 command를 만들거나 결과를 command로 제출한다. |
| cleanup/recovery | focus loss·disconnect·user removal·scene unload가 idempotent하고 stuck input을 남기지 않는다. | 늦은 release에 의존하거나 다른 device의 held state까지 잘못 지운다. |
| camera/UI boundary | local presentation intent와 authoritative result owner 및 correction 경로를 구분한다. | camera/widget이 gameplay 정본을 직접 수정한다. |

다섯 항목 모두와 사람 검토 질문에 근거가 있어야 완료다. reference와 같은 JSON을 복사한 것만으로 설계 판단을 완료했다고 보지 않는다.

## 완료 기준

- 모든 event를 consumed, buffered, ignored 중 하나로 분류한다.
- simulation command를 device-independent schema로 제출한다.
- focus/context 전환의 실패와 cleanup을 기록한다.
