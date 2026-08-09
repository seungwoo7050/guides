# Vertical Slice Capstone

## 목적

`Relay Arena`라는 작은 top-down arena game의 한 match를 설계합니다. 이 Capstone은 완성 게임이나 범용 엔진을 만드는 과제가 아닙니다. 문서에서 배운 상태·수명·실패·검증을 한 playable feature 경로로 연결하는 과제입니다.

```text
boot/menu
→ arena content load
→ player input
→ fixed-step movement and interaction
→ match rule and result
→ presentation
→ save/replay
→ optional network authority
→ profile and release decision
```

프로젝트 입력, 제출 템플릿과 fixture는 [`projects/relay-arena-vertical-slice`](../projects/relay-arena-vertical-slice/README.md)에 있습니다.

## 제품 brief

- 1명의 player가 작은 arena에서 relay core 세 개를 활성화합니다.
- player는 이동, dash와 interact command를 가집니다.
- moving hazard와 간단한 agent가 방해합니다.
- 모든 core를 활성화하면 match result가 확정됩니다.
- local best time과 accessibility/input setting을 저장합니다.
- replay profile은 command trace에서 match result와 state hash를 재현합니다.
- network profile은 두 client가 server-authoritative match에 참여한다고 가정합니다.

아트 품질과 콘텐츠 양은 평가하지 않습니다. placeholder로 충분합니다.

## 필수 Profile A — 계약과 검증 산출물

엔진이나 대규모 구현 없이 완료할 수 있습니다. 다음 파일을 제출합니다.

### 1. `runtime-state-map.md`

- process, user, frontend, world, match, entity 수명
- state transition과 owner
- world load 취소와 partial cleanup
- suspend/resume와 shutdown

### 2. `time-and-input-contract.md`

- real/game/fixed/render/server clock
- fixed timestep, accumulator와 max catch-up
- Move, Dash, Interact action/command schema
- input buffer, pause와 focus policy

### 3. `state-ownership.csv`

최소 field:

```text
state_id,scope,owner,writer,readers,serialized,replicated,lifetime,invariant
```

### 4. `world-and-asset-plan.md`

- scenes/chunks와 entity lifecycle
- asset ids, dependency와 load group
- control-ready와 cosmetic-ready 구분
- memory/loading budget과 fallback

### 5. `gameplay-rules.md`

- match phase state machine
- command accepted/rejected 조건
- core activation, dash cooldown과 result invariant
- persistent best-time commit boundary

### 6. `save-and-replay.md`

- save envelope와 schema version
- v1→v2 migration
- replay command stream와 periodic state hash
- determinism scope와 first-divergence report

### 7. `authority-and-latency.md`

- local profile에서도 future network boundary를 표시
- network 선택 profile에서는 authority table, prediction/correction와 fault matrix
- client가 제출하는 intent와 server result 구분

### 8. `test-and-observability-plan.md`

- pure rule, simulation, scene, platform tests
- build/content/session/tick 식별자
- structured events와 bounded replay trace
- known-bad fixture와 meta-test

### 9. `performance-and-release.md`

- target device와 frame/memory/loading budget
- representative workload
- accessibility/input/localization/suspend checks
- build/content/save/protocol identity
- release gate, known issue와 rollback

### 10. `traceability-matrix.csv`

각 requirement를 owner, implementation/profile, test, telemetry와 release evidence에 연결합니다.

## 선택 Profile B — Local playable slice

Unity, Unreal Engine, Godot 또는 자체 framework를 사용할 수 있습니다.

### 최소 기능

- menu와 arena transition
- remappable Move/Dash/Interact
- fixed-step 또는 명시적 simulation policy
- player, relay core, hazard와 restart
- pause/focus loss 처리
- save 또는 replay 중 하나의 실제 구현
- target build와 profile capture

### 구현 제한

- 엔진 sample을 그대로 복사하지 않습니다.
- gameplay state를 widget/animation에 소유시키지 않습니다.
- asset path를 persistent id로 사용하지 않습니다.
- frame rate에 따라 dash 거리나 cooldown이 달라지지 않게 합니다.
- missing cosmetic에서 gameplay가 계속되는 fallback을 둡니다.

### 검증

- 30/60/120 render FPS 또는 가능한 서로 다른 frame condition에서 같은 command trace 결과
- pause/focus loss 뒤 stuck input 없음
- arena 재진입 반복 뒤 entity/subscription/resource 증가 없음
- corrupt/old save의 안전한 처리 또는 replay first-divergence 탐지
- target-device frame/memory/loading capture

## 선택 Profile C — Networked slice

### 최소 기능

- authoritative server 또는 host
- client Move/Dash/Interact intent
- server validation과 match result
- state snapshot/acknowledgement
- latency·loss·reordering fixture
- reconnect 또는 explicit session abandonment

### 검증

- duplicate command에 side effect가 한 번만 적용됩니다.
- old snapshot이 latest state를 덮지 않습니다.
- non-owner command가 거부됩니다.
- correction 뒤 presentation one-shot이 중복되지 않습니다.
- incompatible content/protocol join이 actionable하게 거부됩니다.

## 공통 실패 주입

다음 중 최소 여섯 개를 선택합니다.

1. 200ms render hitch
2. fixed-step catch-up 상한 초과
3. focus loss while input held
4. world load 중 cancel
5. async asset completion after owner destroyed
6. missing optional cosmetic
7. scene unload during agent path request
8. save write 중 storage failure
9. old save schema
10. replay hash divergence
11. 100ms latency + 5% loss
12. duplicate/reordered command
13. low-memory quality degradation
14. suspend during result commit

각 실패는 예상 state, 보호할 invariant, evidence와 recovery를 기록합니다.

## 평가 기준

### 상태와 소유권

- 하나의 state에 최종 writer가 명확합니다.
- presentation/cache/editor/telemetry를 authoritative state와 구분합니다.
- process/world/match/entity/frame 수명이 섞이지 않습니다.

### 실패와 복구

- 정상 경로만 설명하지 않습니다.
- 취소·timeout·stale completion·duplicate·corruption을 실제 입력으로 다룹니다.
- partial state와 cleanup owner를 기록합니다.

### 검증

- 문장 “정상 동작한다” 대신 실행·trace·test·profile 조건이 있습니다.
- known-bad fixture가 실제로 거부됩니다.
- replay 또는 state transition에서 first wrong point를 찾을 수 있습니다.

### 프로젝트 진입성

- 특정 엔진 API로만 설명하지 않고 다른 engine concept에 매핑할 수 있습니다.
- 문서만 읽은 다른 개발자가 작은 구현 issue를 나눌 수 있습니다.
- 미구현 범위와 후속 전문 트랙이 명확합니다.

## 제출하지 않아도 되는 것

- 상용 수준 그래픽과 audio
- full physics engine
- custom renderer
- global matchmaking/backend
- anti-cheat system
- live economy와 payment
- multi-region dedicated server platform
- 완성된 reference answer

## 완료 뒤 확장

- gameplay/client: 실제 엔진 project에서 한 feature PR
- engine: custom subsystem, memory/streaming/tool 개선
- rendering: `computer-graphics`로 이동
- server: `distributed-services`, `web-infra`로 이동
- tools/build: `python`, `platform-engineering`으로 이동
- data/ML: `data-engineering`, `machine-learning`으로 이동
- security/anti-cheat: `cybersecurity`로 이동

Capstone의 목표는 모든 직무를 한 사람이 수행하는 것이 아니라, 각 직무가 같은 game state와 release를 어떻게 공유하는지 이해한 뒤 자신의 경로에서 깊이를 만드는 것입니다.
