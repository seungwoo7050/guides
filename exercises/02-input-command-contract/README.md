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

## 필수 결정

- device와 local user의 association
- context 우선순위와 event consumption
- action→command 변환과 tick/sequence
- continuous axis sampling과 edge buffering
- focus loss/device disconnect의 held-state cleanup
- camera/UI가 authoritative state에 제출하는 정보

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

## 완료 기준

- 모든 event를 consumed, buffered, ignored 중 하나로 분류한다.
- simulation command를 device-independent schema로 제출한다.
- focus/context 전환의 실패와 cleanup을 기록한다.
