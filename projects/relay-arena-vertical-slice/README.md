# Relay Arena Vertical Slice

## 과제 목적

작은 top-down arena match를 대상으로 게임 runtime의 공통 계약을 하나의 trace로 연결한다. 필수 Profile A는 엔진 구현이 아니라 **소유권·실패·검증 산출물**을 완성한다. 선택 Profile B/C에서 실제 playable 또는 networked slice를 구현할 수 있다.

```text
boot/menu
→ arena load
→ input command
→ fixed simulation
→ game rule and world state
→ presentation
→ save/replay or network view
→ profile
→ release decision
```

상세 평가 범위는 [Capstone 문서](../../docs/17-capstone.md)를 먼저 읽는다.

## 제품 brief

- player는 작은 arena에서 relay core 세 개를 순서와 무관하게 활성화한다.
- Move, Dash, Interact command를 사용한다.
- moving hazard와 두 종류의 agent가 있다.
- core 세 개가 모두 활성화되면 match result가 한 번만 확정된다.
- local best time과 input/accessibility setting을 저장한다.
- replay는 command stream과 checkpoint hash로 결과를 재현한다.
- network 선택 profile은 authoritative server가 command를 검증한다.
- placeholder art/audio로 충분하며 콘텐츠 양과 그래픽 품질은 평가하지 않는다.

## 제공 입력

| 입력 | 역할 |
|---|---|
| [`inputs/system-brief.md`](inputs/system-brief.md) | 제품·runtime·team 제약 |
| [`inputs/requirements.csv`](inputs/requirements.csv) | 추적해야 할 요구사항 |
| [`inputs/runtime-events.json`](inputs/runtime-events.json) | load·cancel·restart·suspend 사건 |
| [`inputs/gameplay-rules.json`](inputs/gameplay-rules.json) | match phase와 command 기본 계약 |
| [`inputs/content-manifest.json`](inputs/content-manifest.json) | stable asset와 dependency·budget |
| [`inputs/save-v1.json`](inputs/save-v1.json) | 이전 save fixture |
| [`inputs/save-v2-contract.json`](inputs/save-v2-contract.json) | 현재 save 계약 |
| [`inputs/replay-trace.json`](inputs/replay-trace.json) | tick command와 checkpoint hash |
| [`inputs/network-session.json`](inputs/network-session.json) | authority·duplicate·stale fixture |
| [`inputs/target-profile.json`](inputs/target-profile.json) | target device 성능 근거 |
| [`inputs/release-evidence.json`](inputs/release-evidence.json) | candidate build의 검증 상태 |

입력은 구현 정답이 아니다. 일부는 의도적으로 incomplete하거나 실패를 포함한다. 사실·가설·결정을 분리해 누락을 찾아야 한다.

## 필수 Profile A 제출

`template/`을 개인 작업 디렉터리에 복사한 뒤 작성한다.

| 제출 파일 | 확인할 계약 |
|---|---|
| [`runtime-state-map.md`](template/runtime-state-map.md) | process→world→match→entity 상태와 전이 |
| [`time-and-input-contract.md`](template/time-and-input-contract.md) | clock, fixed step, action·command 소비 |
| [`state-ownership.csv`](template/state-ownership.csv) | state owner·writer·reader·수명·직렬화 |
| [`world-and-asset-plan.md`](template/world-and-asset-plan.md) | scene/entity lifecycle와 load gate |
| [`gameplay-rules.md`](template/gameplay-rules.md) | command acceptance와 match invariant |
| [`movement-and-space.md`](template/movement-and-space.md) | 좌표·collision·movement 적용 순서 |
| [`presentation-contract.md`](template/presentation-contract.md) | animation/audio/VFX/UI의 event 소비 |
| [`save-and-replay.md`](template/save-and-replay.md) | migration과 replay divergence |
| [`ai-and-navigation.md`](template/ai-and-navigation.md) | agent sensing·decision·path lifetime |
| [`authority-and-latency.md`](template/authority-and-latency.md) | intent·validation·prediction·correction |
| [`test-and-observability-plan.md`](template/test-and-observability-plan.md) | test pyramid, trace와 known-bad fixture |
| [`performance-and-release.md`](template/performance-and-release.md) | target budget·accessibility·release gate |
| [`traceability-matrix.csv`](template/traceability-matrix.csv) | requirement→owner→test→evidence 연결 |
| [`change-plan.md`](template/change-plan.md) | 구현 issue 순서, migration과 rollback |

## 작업 순서

### 1. 사실과 미확인 항목 분리

`system-brief`, manifest와 trace에서 직접 확인되는 사실만 기록한다. 다음은 추측하지 않는다.

- 엔진 class 이름
- thread model
- platform storage의 durability
- physics determinism
- network transport 보장
- background/suspend 시간 제한

필요한 결정은 “제안”으로 표시하고 검증 방법을 붙인다.

### 2. runtime과 state owner 확정

가장 먼저 `runtime-state-map.md`와 `state-ownership.csv`를 작성한다. state owner가 불명확하면 save, network, UI, test와 telemetry 문서가 모두 흔들린다.

### 3. 한 command의 vertical trace 작성

`Interact(core-b)` 하나를 다음 경로로 추적한다.

```text
device event
→ action/context
→ command(tick, player, sequence)
→ rule validation
→ core state transition
→ match progression event
→ animation/audio/VFX/UI projection
→ replay/network/telemetry evidence
```

각 단계에서 writer, failure와 id를 기록한다.

### 4. 실패 주입 연결

최소 여섯 개를 선택한다.

- 200ms render hitch
- held input 중 focus loss
- world load cancel
- owner 파괴 뒤 asset completion
- old/corrupt save
- replay divergence
- non-owner 또는 duplicate command
- stale snapshot
- low-memory quality degradation
- suspend during result commit

각 실패에는 expected state, 보호할 invariant, evidence와 recovery가 있어야 한다.

### 5. release 근거까지 추적

기능 구현 완료를 release 완료로 보지 않는다. 정확한 candidate build/content/save/protocol identity와 target-device evidence를 `traceability-matrix.csv`에 연결한다.

## Profile B — Local playable 선택 구현

엔진은 자유다. 최소 범위:

- menu→arena transition
- remappable Move/Dash/Interact
- player, core, hazard와 최소 agent
- pause/focus loss/restart
- save 또는 replay 하나
- target build와 profile capture

구현이 크지 않아도 다음을 실제 검사한다.

- 서로 다른 render frame condition에서 같은 command trace 결과
- arena 반복 진입 뒤 object/subscription/resource 기준선 복귀
- old/corrupt save의 안전한 처리 또는 first replay divergence
- target device의 frame·memory·loading 근거

## Profile C — Networked 선택 구현

- authoritative server 또는 host
- intent command와 server validation
- duplicate/stale/non-owner 거부
- prediction/correction 또는 지연 허용 설계
- latency·loss·reordering fixture
- reconnect 또는 explicit abandonment

transport, dedicated server 운영과 distributed backend 자체는 후속 브랜치가 소유한다.

## 평가 기준

### 상태와 소유권

- authoritative state의 최종 writer가 하나다.
- presentation, editor cache, telemetry와 network view를 정본과 구분한다.
- process/world/match/entity/frame lifetime이 섞이지 않는다.

### 실패와 복구

- cancel, stale completion, duplicate, corruption과 suspend를 정상 입력처럼 다룬다.
- partial state와 cleanup owner를 기록한다.
- fallback이 gameplay invariant와 사용자 데이터를 보존하는지 설명한다.

### 검증

- “정상 동작” 대신 fixture·trace·test·profile 조건을 제시한다.
- known-bad fixture가 실제로 거부되는지 검사 계획이 있다.
- save/replay/network 문제의 first wrong transition을 찾을 수 있다.

### 팀과 변경

- designer/art/QA/server/build/platform 담당자와 공유할 schema가 명확하다.
- 한 번에 전체 시스템을 재작성하지 않고 review 가능한 issue로 나눈다.
- migration, feature flag, compatibility와 rollback이 포함된다.

## 완료 후 실제 프로젝트 이동

1. 선택 엔진의 작은 sample에서 문서의 state를 실제 class/node/system에 매핑한다.
2. content validator, replay fixture, save migration test 또는 작은 gameplay bug를 첫 기여로 고른다.
3. 같은 subsystem에서 반복 기여하며 editor·content·target platform 제약을 배운다.
4. rendering, backend, data, platform, security는 해당 후속 브랜치로 깊이를 확장한다.
