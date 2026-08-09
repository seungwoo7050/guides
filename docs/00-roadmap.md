# 게임 개발 시스템 로드맵

게임 개발은 하나의 직무가 아닙니다. gameplay client, engine, rendering, server, tools, build, data, security와 QA automation은 서로 다른 깊이를 요구합니다. 그러나 모든 직무는 같은 제품 안에서 다음 계약을 공유합니다.

```text
사용자의 입력과 플랫폼 사건
→ 시간에 따른 시뮬레이션
→ 게임 규칙과 월드 상태
→ 화면·소리·진동·UI 표현
→ 자산·저장·네트워크·빌드
→ 관측·재현·성능·release
```

이 브랜치는 그 공통 계약을 소유합니다. 특정 엔진의 API를 모두 가르치지 않고, 엔진 문서와 기존 프로젝트를 읽을 수 있는 개념 지도와 검증 순서를 제공합니다.

## 학습 목표

- 게임을 frame마다 호출되는 callback 모음이 아니라 여러 시간축과 수명을 가진 상태 시스템으로 읽습니다.
- 게임 규칙의 정본과 presentation, editor data, save, replay, network view를 분리합니다.
- asset과 object가 “파일이 존재함”에서 “target build의 memory에 resident함”까지 거치는 단계를 추적합니다.
- 긴 frame, 잘못된 pause, input loss, stale reference, replay divergence, save migration 실패와 authority violation을 재현합니다.
- target hardware에서 frame time·memory·loading·bandwidth 예산을 측정합니다.
- 엔진 내부의 편리한 API를 사용하더라도 ownership·failure·verification 계약은 프로젝트가 직접 책임진다는 점을 이해합니다.
- game designer, artist, animator, audio, QA, server, build와 platform 담당자가 공유할 데이터 계약을 작성합니다.

## 종료 능력

가이드를 마친 독자는 다음을 수행할 수 있어야 합니다.

1. executable 시작부터 menu, world load, play session, suspend, shutdown까지 runtime state를 그립니다.
2. render frame, fixed simulation step, real time, game time과 server time을 서로 다른 시간축으로 구분합니다.
3. device signal을 remappable action과 deterministic command로 변환하고 UI focus와 gameplay input 충돌을 처리합니다.
4. world, scene, entity, component, subsystem과 asset의 생성·활성화·비활성화·파괴·unload 조건을 기록합니다.
5. game rule, player progression, economy, presentation과 analytics event의 owner를 분리합니다.
6. asset import·validation·dependency·cooking·streaming·memory residence를 한 manifest로 추적합니다.
7. collision query, physics simulation, character movement, animation root motion과 network correction의 적용 순서를 설명합니다.
8. animation·audio·VFX가 gameplay state를 소유하지 않도록 event와 acknowledgement 경계를 설계합니다.
9. save schema를 versioning하고 migration 실패와 replay divergence를 최소 fixture로 조사합니다.
10. navigation과 behavior가 world query·budget·authoritative rule과 만나는 경계를 설계합니다.
11. networked gameplay에서 client intent, server validation, prediction, reconciliation과 replicated public state를 구분합니다.
12. content validator, editor tool, build pipeline과 release artifact의 정본을 정합니다.
13. headless test, record/replay, telemetry, crash context와 profile capture로 버그를 재현합니다.
14. CPU·GPU·memory·loading·network 예산을 target device와 representative scene에서 검증합니다.
15. 접근성·입력 재매핑·localization·suspend/resume·save safety를 release gate에 포함합니다.
16. 하나의 vertical slice를 여러 직무가 병렬로 변경해도 경계가 무너지지 않게 계획합니다.

## 대상 독자

- C++ 또는 다른 언어로 작은 프로그램을 작성해 본 뒤 게임 프로젝트에 진입하려는 개발자
- 엔진 튜토리얼은 따라 했지만 runtime·state·asset·performance 문제를 체계적으로 설명하기 어려운 개발자
- 웹·서버·인프라·데이터 경험을 게임회사 직무로 연결하려는 개발자
- gameplay·engine·tools·server·data·security 중 어느 길을 선택할지 판단하려는 개발자

프로그래밍 자체의 첫 입문 과정은 아닙니다. 문서 실습은 언어 독립적이지만 실제 client·engine 구현 경로는 `cpp` 또는 선택한 엔진의 scripting language 능력을 전제로 합니다.

## 선행 가이드와 선택 경로

### 공통 최소 기반

| 기반 | 필요한 종료 능력 |
|---|---|
| [`git`](https://github.com/seungwoo7050/guides/tree/git) | binary asset과 generated file을 구분하고 작은 변경을 리뷰 가능한 단위로 제출합니다. |
| 한 구현 언어 | 함수·타입·collection·오류·파일·테스트를 사용해 작은 상태 시스템을 구현합니다. |
| [`algorithms`](https://github.com/seungwoo7050/guides/tree/algorithms)의 기초 | 상태 전이, graph, queue, spatial query의 비용과 정확성을 비교합니다. |

### 직무별 권장 기반

#### Gameplay·client

```text
cpp
→ algorithms
→ game-development
```

엔진 scripting language를 이미 사용한다면 `cpp` 전체를 필수로 다시 학습하지 않아도 됩니다. 그러나 object lifetime, ownership, data layout과 debugging을 설명할 수 있어야 합니다.

#### Engine·core systems

```text
c 또는 cpp
→ computer-architecture
→ operating-systems
→ game-development
```

#### Rendering

```text
cpp
→ algorithms
→ computer-architecture
→ game-development
→ computer-graphics
```

현재 브랜치는 camera·visibility·presentation·frame budget의 접점을 다루고 rasterization·shader·GPU pipeline은 `computer-graphics`에 맡깁니다.

#### Game server

```text
web-app
→ java 또는 다른 server language
→ backend-spring-boot
→ database-systems
→ computer-networks
→ game-development
→ distributed-services
→ web-infra
```

이 브랜치의 11장은 match runtime의 authority와 replication을 다룹니다. 계정·inventory·상점·결제·matchmaking·운영 이벤트의 서비스 수렴은 `distributed-services`가 소유합니다.

#### Tools·build·platform

```text
python
→ unix-systems
→ game-development
→ web-infra
→ platform-engineering
```

#### Data·ML

```text
python
→ database-systems
→ game-development
→ data-engineering
→ machine-learning
```

#### Security·anti-cheat

```text
c 또는 cpp
→ computer-architecture
→ operating-systems
→ computer-networks
→ game-development
→ cybersecurity
```

이 브랜치에서는 authoritative rule과 trust boundary를 표시하지만 anti-cheat, vulnerability analysis와 incident response 자체는 `cybersecurity`가 소유합니다.

## 이 가이드가 반복하지 않는 것

- C++ 문법, RAII, smart pointer와 build system
- 벡터·행렬·shader와 GPU pipeline의 전체 원리
- TCP·UDP·NAT와 packet loss의 네트워크 기초
- transaction, database storage와 분산 서비스 수렴
- Linux host, container, CI/CD와 incident response
- 보안 취약점 분석과 reverse engineering
- machine learning model 학습

현재 문서에서는 게임 경계에 필요한 최소 상태만 요약하고 원래 브랜치로 연결합니다.

## 필수 학습 지도

### Part I. 게임 runtime과 상태

1. [게임 제품과 runtime 계약](01-game-product-and-runtime-contract.md)
2. [게임 루프, 시간과 프레임](02-game-loop-time-and-frames.md)
3. [입력, 명령, 카메라와 게임 UI](03-input-command-camera-and-ui.md)
4. [월드, 장면, 엔티티와 컴포넌트 수명](04-world-scene-entity-component-lifecycles.md)
5. [게임 규칙, 진행 상태와 data-driven 설계](05-gameplay-rules-progression-and-data.md)

Part I이 끝나면 다음 흐름을 상태와 owner로 설명할 수 있어야 합니다.

```text
platform event
→ input action
→ gameplay command
→ fixed simulation
→ authoritative state transition
→ presentation snapshot
→ rendered frame
```

### Part II. 콘텐츠와 시뮬레이션

6. [자산 import, cooking, loading과 memory residence](06-assets-import-cooking-loading-and-memory.md)
7. [충돌, 물리, 이동과 좌표 계약](07-collision-physics-movement-and-space.md)
8. [애니메이션, 오디오, VFX와 표현 경계](08-animation-audio-vfx-and-presentation.md)
9. [저장, migration, replay와 determinism](09-save-migration-replay-and-determinism.md)
10. [게임 AI, navigation과 behavior 통합](10-game-ai-navigation-and-behavior.md)

Part II가 끝나면 “asset을 load한다”, “physics가 움직인다”, “animation을 재생한다”는 표현을 다음처럼 구체화할 수 있어야 합니다.

```text
어떤 정본 data가 존재하는가
→ 어떤 build transform을 거치는가
→ 누가 handle과 lifetime을 소유하는가
→ 어떤 simulation event가 발생하는가
→ presentation이 무엇을 소비하는가
→ unload·save·replay 때 무엇을 보존하는가
```

### Part III. 온라인·품질·생산

11. [네트워크 권위, replication과 latency](11-network-authority-replication-and-latency.md)
12. [에디터 도구, 빌드와 콘텐츠 검증](12-tools-editor-builds-and-content-validation.md)
13. [테스트, 디버깅, telemetry와 재현](13-testing-debugging-telemetry-and-reproduction.md)
14. [성능 예산, profiling과 scalability](14-performance-budgets-profiling-and-scalability.md)
15. [플랫폼 입력, 접근성, 저장 수명과 release](15-platform-accessibility-lifecycle-and-release.md)
16. [게임 팀 경계와 안전한 변경](16-game-team-interfaces-and-change-management.md)
17. [Vertical Slice Capstone](17-capstone.md)

Part III가 끝나면 기능 완료를 다음 수명 주기로 관리할 수 있어야 합니다.

```text
playable rule
→ deterministic or observable test
→ content validation
→ target-device profile
→ save/network compatibility
→ accessibility and platform checks
→ release artifact
→ telemetry and rollback decision
```

## 문서와 실습 연결

| 문서 영역 | 단계 실습 | 대표 실패 |
|---|---|---|
| 시간·frame·simulation | [01 시간 단계 분석](../exercises/01-time-step-analysis/README.md) | 긴 frame에서 무한 catch-up, pause 중 timer 진행, input 중복 소비 |
| 입력·command·focus | [02 입력과 명령](../exercises/02-input-command-contract/README.md) | device key를 game rule에 직접 결합, UI와 gameplay가 동시에 입력 소비 |
| world·entity 수명 | [03 월드 수명 검토](../exercises/03-world-lifecycle-review/README.md) | unload된 scene 객체를 참조, destroy event 뒤 callback 실행 |
| asset·loading·memory | [04 asset loading 계획](../exercises/04-asset-loading-plan/README.md) | hard reference로 전체 bundle resident, async completion 후 owner 소멸 |
| save·replay | [05 save와 replay migration](../exercises/05-save-and-replay-migration/README.md) | schema version 부재, 비결정 순서, float·random seed 차이 |
| multiplayer | [06 authority와 latency](../exercises/06-authority-and-latency/README.md) | client가 reward·hit를 확정, stale correction이 최신 state를 덮음 |
| performance | [07 성능 예산 검토](../exercises/07-performance-budget-review/README.md) | editor profile을 target device 결과로 오인, 평균만 보고 spike 무시 |
| release | [08 release readiness](../exercises/08-release-readiness/README.md) | save compatibility·remap·suspend·crash context 없이 ship |

## Capstone profile

[`relay-arena-vertical-slice`](../projects/relay-arena-vertical-slice/README.md)는 다음 세 profile로 확장할 수 있습니다.

### Profile A. 계약과 검증 산출물 — 필수

- runtime state와 owner map
- fixed-step·input trace
- world/entity lifecycle
- asset manifest와 loading budget
- save migration과 replay hash
- authority table과 latency UX
- test·telemetry·performance·release plan

엔진이 없어도 완료할 수 있습니다. 이 profile이 문서 중심 가이드의 필수 완료 기준입니다.

### Profile B. Local playable slice — 선택

- menu에서 arena 진입
- 한 명의 player와 두 종류의 obstacle 또는 agent
- input remapping
- pause·restart·save 또는 replay
- target frame budget과 profile capture

### Profile C. Networked slice — 선택 심화

- dedicated 또는 authoritative host
- client intent와 server validation
- prediction·correction 또는 지연 허용 설계
- packet loss·latency fixture
- replay 또는 authoritative event log

Profile B와 C의 구현 엔진은 자유지만 같은 상태 계약과 실패 검증을 사용합니다.

## 완료 판정

다음 질문에 근거와 함께 답할 수 있어야 합니다.

- frame과 simulation step이 다를 때 입력은 몇 번 소비됩니까?
- pause, loading, background와 network stall에서 어떤 clock이 멈춥니까?
- entity와 asset의 identity·lifetime·reference는 어떻게 다릅니까?
- gameplay state와 animation/audio/VFX의 presentation state는 어디에서 분리됩니까?
- save와 replay가 직렬화하는 정보는 왜 같지 않을 수 있습니까?
- client가 제출할 수 있는 것은 intent입니까, 결과입니까?
- 어떤 profile capture가 target player experience를 대표합니까?
- content와 code가 다른 cadence로 바뀔 때 compatibility를 어떻게 검증합니까?
- release 뒤 crash, desync, corrupted save를 조사할 식별자와 trace가 있습니까?

자동 검사 통과는 교육적 완성을 대신하지 않습니다. 다른 개발자가 Capstone 산출물에서 owner, failure, evidence와 미구현 범위를 추적할 수 있는지 검토해야 합니다.

## 실제 프로젝트로 이동하기

1. 사용하려는 엔진의 작은 sample을 실행하고 이 문서의 개념을 실제 class·node·system에 매핑합니다.
2. 최근 issue 하나를 골라 재현 trace를 만듭니다.
3. content validator, test fixture, error message 또는 작은 gameplay bug부터 기여합니다.
4. 같은 subsystem에서 반복 기여하며 editor workflow와 asset/release 제약을 학습합니다.
5. feature를 구현한 뒤 target device profile과 save/network compatibility까지 확인합니다.

완성된 개인 게임의 크기보다, 기존 게임 코드베이스에서 한 상태 경계를 정확히 읽고 안전하게 변경하는 능력을 우선합니다.
