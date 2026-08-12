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

이 브랜치는 그 공통 계약을 소유하는 **분야 진입(`field-entry`)** 가이드입니다. 특정 엔진의 API를 모두 가르치지 않고, 엔진 문서와 기존 프로젝트를 읽을 수 있는 개념 지도와 검증 순서를 제공합니다.

## 학습 목표

- 게임을 frame마다 호출되는 callback 모음이 아니라 여러 시간축과 수명을 가진 상태 시스템으로 읽습니다.
- 게임 규칙의 정본과 presentation, editor data, save, replay, network view를 분리합니다.
- asset과 object가 “파일이 존재함”에서 “target build의 memory에 resident함”까지 거치는 단계를 추적합니다.
- 긴 frame, 잘못된 pause, input loss, stale reference, replay divergence, save migration 실패와 authority violation을 재현합니다.
- target hardware에서 frame time·memory·loading·bandwidth 예산을 측정합니다.
- 엔진 내부의 편리한 API를 사용하더라도 ownership·failure·verification 계약은 프로젝트가 직접 책임진다는 점을 이해합니다.
- game designer, artist, animator, audio, QA, server, build와 platform 담당자가 공유할 데이터 계약을 작성합니다.

## 정본 종료 능력

`main`의 완료 계약은 다음 세 가지입니다.

1. 기존 엔진 프로젝트의 update·render·asset·tool 경계를 복원한다.
2. 입력부터 상태·표현·저장까지 이어지는 작은 게임플레이 기능을 구현한다.
3. frame·resource·simulation 실패를 재현하고 profiling 근거로 수정한다.

다음은 세 종료 능력을 만들고 검토하기 위한 세부 학습 결과이며, 별도의 카탈로그 종료 능력을 추가하지 않습니다.

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

브랜치 카탈로그의 직접 필수 관계는 비어 있습니다. 따라서 문서·fixture 기반 Profile A는 다른 가이드 완료 없이 시작할 수 있습니다. 다만 프로그래밍 자체를 처음부터 가르치지는 않으며, 두 번째 종료 능력의 실제 구현 근거를 만들 때는 `cpp` 또는 선택한 엔진의 scripting language 능력이 필요합니다.

## 선행 가이드와 선택 경로

### 브랜치 자체 관계

| 관계 | 정본 값 |
|---|---|
| `requires` | 없음 |
| `recommends` | `algorithms`, `cpp`, `operating-systems`, `computer-networks` |
| `connects` | `computer-graphics`, `distributed-services`, `machine-learning`, `cybersecurity`, `platform-engineering` |
| `continues_to` | `computer-graphics`, `distributed-services`, `machine-learning`, `cybersecurity` |

`requires`는 이 브랜치 자체의 직접 전제이고, 아래 `linear_paths`는 목표 직무까지 처음부터 진행할 때의 권장 순서입니다. 선형 경로에 들어 있다는 사실만으로 `game-development`의 직접 필수가 되지는 않습니다.

### 카탈로그의 일곱 트랙과 선형 경로

#### 게임 클라이언트·게임플레이 (`game-client-gameplay`)

```text
beginner: git → c → cpp → algorithms → game-development
experienced: git → cpp → algorithms → game-development
```

#### 엔진·코어 시스템 (`game-engine-core`)

```text
git → c → cpp → algorithms → computer-architecture → operating-systems → game-development
```

#### 렌더링·그래픽스 (`game-rendering`)

```text
git → c → cpp → algorithms → computer-architecture → game-development → computer-graphics
```

현재 브랜치는 renderer가 소비하는 장면·자산·표현·frame budget 접점을 다루며, rasterization·shader·GPU pipeline은 `computer-graphics`가 소유합니다.

#### Java/Spring 게임 서버 (`game-server`)

```text
git → web-app → java → backend-spring-boot → database-systems → game-development → computer-networks → distributed-services → web-infra
```

이 트랙에서 `game-development`는 `recommended`이지만 선형 경로에는 게임 상태 문맥을 위해 포함됩니다. 이 브랜치의 11장은 match runtime authority와 replication만 다루고, 서비스 상태 수렴은 `distributed-services`가 소유합니다.

#### 개발 도구·빌드·플랫폼 (`game-tools-platform`)

```text
git → python → unix-systems → game-development → web-infra → platform-engineering
```

이 트랙에서도 `game-development`는 `recommended`이며 asset·editor·build 입력의 게임 문맥을 제공합니다.

#### 게임 데이터·머신러닝 (`game-data-ml`)

```text
git → python → algorithms → game-development → database-systems → data-engineering → machine-learning
```

이 트랙에서도 `game-development`는 `recommended`이며 gameplay event와 runtime identity의 의미 문맥을 제공합니다.

#### 보안·안티치트 (`game-security-anticheat`)

```text
git → c → cpp → algorithms → game-development → computer-architecture → operating-systems → unix-systems → computer-networks → cybersecurity
```

이 브랜치는 authoritative rule과 trust boundary의 게임 맥락을 제공하지만 vulnerability analysis와 incident response 자체는 `cybersecurity`가 소유합니다.

같은 내용을 역할별 우선 문서와 함께 보려면 [게임 개발 직무별 진입 지도](../reference/role-entry-map.md)를 사용합니다.

## 소유와 비소유 범위

### `owns`

1. 고정·가변 시간 단계와 game loop
2. 입력·카메라·장면·엔티티·컴포넌트의 상태 경계
3. 자산 로딩·직렬화·resource lifetime과 editor workflow
4. 물리·애니메이션·오디오·렌더링 하위 시스템의 게임 계층 통합
5. 게임플레이 기능의 상태 전이·저장·재현·테스트
6. frame budget·profiling·client/server authoritative 경계의 게임 맥락

### `excludes`

1. GPU 렌더링 파이프라인과 shader 내부구조
2. 운영체제·네트워크 프로토콜·분산 합의의 일반 원리
3. 특정 상용 엔진 API 전체
4. 게임 기획·아트·사운드 제작 직무 교육

게임 AI·navigation은 하위 시스템과 gameplay command의 통합 사례이고, 접근성·release는 target platform 검증 근거이며, 팀 변경은 editor workflow와 상태 계약을 안전하게 유지하는 지원 절입니다. 이 주제들은 별도의 `owns`를 추가하지 않습니다.

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

[`90-engine-and-source-map.md`](90-engine-and-source-map.md)는 별도 18단계가 아니라, 01~17의 개념을 선택 엔진과 공식 자료에 대응할 때 사용하는 지원 reference입니다.

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

root README의 [정본 진행 순서](../README.md#정본-진행-순서)가 실행 명령·수정 위치·reference 시점을 포함한 canonical workflow입니다. 아래 표는 roadmap에서 같은 01~17 순서를 개념과 직접 수행의 관계로 요약합니다.

| 문서 | 관찰·단계 실습 | Capstone 누적 산출물 |
|---|---|---|
| 01 제품·runtime | — | `runtime-state-map.md` |
| 02 game loop·시간 | `fixed-step-replay` → [01 시간 단계 분석](../exercises/01-time-step-analysis/README.md) | `time-and-input-contract.md` |
| 03 입력·command·focus | [02 입력과 명령](../exercises/02-input-command-contract/README.md) | `time-and-input-contract.md` |
| 04 world·entity 수명 | [03 월드 수명 검토](../exercises/03-world-lifecycle-review/README.md) | `runtime-state-map.md`, `state-ownership.csv`, `world-and-asset-plan.md` |
| 05 gameplay rule·progression | — | `gameplay-rules.md`, `state-ownership.csv` |
| 06 asset·loading·memory | [04 asset loading 계획](../exercises/04-asset-loading-plan/README.md) | `world-and-asset-plan.md` |
| 07 collision·movement·space | — | `movement-and-space.md` |
| 08 animation·audio·VFX | — | `presentation-contract.md` |
| 09 save·migration·replay | `fixed-step-replay` hash 재해석 → [05 save와 replay migration](../exercises/05-save-and-replay-migration/README.md) | `save-and-replay.md` |
| 10 AI·navigation 통합 | 필수 concept; AI 전용 분석만 선택 | 기존 movement·presentation·authority 산출물, 선택 `optional/ai-and-navigation.md` |
| 11 authority·replication·latency | [06 authority와 latency](../exercises/06-authority-and-latency/README.md) | `authority-and-latency.md` |
| 12 tool·build·content validation | 실습 04 결과 재사용 | `world-and-asset-plan.md`, `traceability-matrix.csv` |
| 13 test·debug·telemetry | 모든 실습의 known-bad와 evidence 연결 | `test-and-observability-plan.md` |
| 14 performance·profiling | [07 성능 예산 검토](../exercises/07-performance-budget-review/README.md) | `performance-and-release.md` |
| 15 platform·accessibility·release | [08 release readiness](../exercises/08-release-readiness/README.md) | `performance-and-release.md` |
| 16 팀 경계·안전한 변경 | — | `traceability-matrix.csv`, `change-plan.md` |
| 17 Vertical Slice Capstone | Profile A 13개 + Profile B 구현 evidence 통합 | learner 구현 뒤 reference code/artifact 비교 |

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

엔진이 없어도 작성할 수 있습니다. 이 profile은 문서 중심의 필수 계약 묶음이지만, 아래 Profile B 구현 evidence 없이 브랜치 전체를 완료한 것은 아닙니다.

### Profile B. 실행 가능한 구현 evidence — 필수

- menu에서 arena 진입
- 한 명의 player와 두 종류의 obstacle 또는 agent
- input remapping
- pause·restart·save 또는 replay
- target frame budget과 profile capture

두 번째 종료 능력을 완료하려면 실행 가능한 구현 evidence가 반드시 필요합니다. 기본 Python headless path 대신 기존 Unity, Unreal Engine, Godot 또는 자체 framework 프로젝트에서 입력→상태→표현→저장을 연결한 동등한 작은 기능 변경과 assertion mapping을 제출할 수 있습니다. 선택 가능한 것은 구현 엔진과 물리 경로이며, 구현 evidence 자체는 선택이 아닙니다.

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
