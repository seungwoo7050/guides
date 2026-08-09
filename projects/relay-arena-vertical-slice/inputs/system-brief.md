# Relay Arena system brief

## 제품

- top-down camera의 3~5분 local match가 기본 profile이다.
- Windows x64와 low-end handheld Linux를 첫 target으로 한다.
- local profile은 offline에서 완전히 플레이할 수 있어야 한다.
- network profile은 두 client와 authoritative host/server를 가정한다.
- placeholder content로 기능과 실패 계약을 검증한다.

## runtime

- process는 Frontend와 Arena world를 전환한다.
- Arena load는 취소 가능하며 critical content가 준비되면 control-ready가 된다.
- cosmetic와 agent navigation은 control-ready 뒤 늦게 준비될 수 있다.
- restart는 새 match generation을 만들고 이전 match의 callback/subscription을 정리해야 한다.
- pause menu, OS focus loss, suspend는 서로 다른 이유다.

## gameplay

- player는 Move, Dash, Interact를 사용한다.
- Dash는 8 fixed tick cooldown과 3 world-unit displacement를 제안한다.
- core는 `inactive → activating → active` 상태를 가진다.
- 세 core가 active가 되면 result가 한 번만 확정된다.
- moving hazard 접촉은 player를 checkpoint로 되돌리지만 core 진행 상태는 유지한다.
- agent는 player를 추적하되 navigation이 준비되지 않으면 안전하게 idle한다.

## 저장과 replay

- best time, binding과 accessibility setting은 durable하다.
- active match의 exact world snapshot 저장은 필수가 아니다.
- replay는 initial rule/content identity, tick command와 checkpoint hash를 기록한다.
- v1 save의 second 단위 best time과 old cosmetic id를 v2로 옮겨야 한다.

## team과 release

- designer는 rule table과 arena content를 편집한다.
- artist/animator/audio는 presentation asset을 제공한다.
- gameplay developer는 rule, command와 state transition을 소유한다.
- tools/build developer는 content validator와 reproducible build를 소유한다.
- QA는 deterministic fixture, target-device path와 known-bad case를 유지한다.
- server/security/data는 선택 profile에서 같은 state/event schema를 소비한다.
