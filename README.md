# 게임 개발 시스템 가이드

게임을 단순히 화면에 무언가를 움직이는 프로그램으로 다루지 않고, **시간에 따라 상태가 변하고 입력·시뮬레이션·표현·자산·저장·네트워크·플랫폼 제약이 한 프레임 안에서 만나는 시스템**으로 다루는 가이드입니다.

```text
플레이어 의도
→ 입력과 명령
→ 게임 규칙과 시뮬레이션
→ 월드·엔티티 상태 변화
→ 애니메이션·오디오·VFX·UI 표현
→ 저장·리플레이·네트워크·텔레메트리
→ 다음 프레임과 다음 빌드
```

이 브랜치의 목적은 Unity, Unreal Engine, Godot 중 하나의 메뉴와 API를 외우게 하는 것이 아닙니다. 어떤 엔진과 프로젝트에 들어가더라도 다음 질문을 할 수 있게 만드는 것이 목적입니다.

- 이 시스템에서 게임의 정본 상태는 무엇입니까?
- 한 프레임과 한 simulation step은 언제 시작하고 끝납니까?
- 입력은 장치 신호에서 게임 명령으로 어디에서 변환됩니까?
- 객체·장면·자산은 누가 만들고 언제 파괴하거나 unload합니까?
- 게임 규칙과 화면 표현은 어느 경계에서 분리됩니까?
- save, replay, network replication은 같은 상태를 어떤 서로 다른 목적으로 직렬화합니까?
- frame time, memory, loading, bandwidth 예산을 어떤 실제 기기에서 검증합니까?
- 디자이너·아티스트·QA·서버·도구 개발자와 어떤 데이터 계약으로 협업합니까?

처음에는 [게임 개발 로드맵](docs/00-roadmap.md)을 읽으세요. 선행 가이드, 직무별 선택 경로, 문서 순서, 실습과 Capstone 완료 기준을 한곳에서 확인할 수 있습니다.

`main` 카탈로그에서 이 가이드는 **분야 진입(`field-entry`)** 브랜치입니다. 한 문장 계약은 다음과 같습니다.

> 게임 루프·시간·입력·장면·엔티티·자산·물리·애니메이션·오디오·네트워크 경계를 연결해 게임 코드베이스에 진입한다.

## 정본 종료 능력

이 가이드가 게임 개발 전문가나 특정 엔진 전문가를 한 번에 완성하지는 않습니다. 완료 판단은 `main`이 선언한 다음 세 능력으로 고정합니다.

1. 기존 엔진 프로젝트의 update·render·asset·tool 경계를 복원한다.
2. 입력부터 상태·표현·저장까지 이어지는 작은 게임플레이 기능을 구현한다.
3. frame·resource·simulation 실패를 재현하고 profiling 근거로 수정한다.

아래 항목은 별도의 종료 능력을 추가하는 목록이 아니라, 위 세 능력을 판단할 때 찾을 세부 근거입니다.

- 처음 보는 게임 저장소에서 부팅, 메뉴, 월드 진입, 플레이, 종료까지 runtime 경계를 추적합니다.
- variable frame과 fixed simulation을 구분하고 긴 frame, pause, slow motion, catch-up 실패를 설명합니다.
- raw input을 재매핑 가능한 action과 결정적인 gameplay command로 변환합니다.
- scene, entity, component, subsystem의 수명과 cross-reference를 조사합니다.
- gameplay rule, progression, economy, presentation state의 owner를 구분합니다.
- asset dependency, import, cooking, asynchronous loading, unload와 memory resident 상태를 설계합니다.
- collision·physics·movement·animation 사이의 정본과 적용 순서를 설명합니다.
- save schema를 versioning하고 replay divergence를 최소 입력으로 재현합니다.
- client prediction과 server authority를 구분하고 latency·loss·reordering에서 사용자 경험과 보안을 검토합니다.
- 자동 테스트, deterministic fixture, record/replay, telemetry와 profiler로 버그와 성능 문제를 재현합니다.
- target hardware에서 frame time·memory·loading·network 예산을 측정하고 품질 단계별 scalability를 결정합니다.
- 하나의 vertical slice를 기능, 실패, 접근성, 빌드와 운영 근거까지 연결합니다.

## 이 브랜치가 소유하는 범위

`main`의 `owns`를 그대로 구현 범위로 사용합니다.

1. 고정·가변 시간 단계와 game loop
2. 입력·카메라·장면·엔티티·컴포넌트의 상태 경계
3. 자산 로딩·직렬화·resource lifetime과 editor workflow
4. 물리·애니메이션·오디오·렌더링 하위 시스템의 게임 계층 통합
5. 게임플레이 기능의 상태 전이·저장·재현·테스트
6. frame budget·profiling·client/server authoritative 경계의 게임 맥락

게임 AI·navigation, 접근성·release, telemetry와 팀 변경 장은 별도의 소유 범위를 추가하지 않습니다. 위 여섯 범위가 agent, target platform, 협업과 실패 상황에서도 유지되는지 확인하는 **통합 사례와 지원 근거**입니다.

### 브랜치 관계

선형 직무 경로와 브랜치 자체의 직접 필수 조건을 구분합니다. 이 브랜치의 `requires`는 비어 있으므로 다른 가이드 완료를 시작 조건으로 강제하지 않습니다.

| 관계 | 브랜치 |
|---|---|
| `requires` | 없음 |
| `recommends` | [`algorithms`](https://github.com/seungwoo7050/guides/tree/algorithms), [`cpp`](https://github.com/seungwoo7050/guides/tree/cpp), [`operating-systems`](https://github.com/seungwoo7050/guides/tree/operating-systems), [`computer-networks`](https://github.com/seungwoo7050/guides/tree/computer-networks) |
| `connects` | [`computer-graphics`](https://github.com/seungwoo7050/guides/tree/computer-graphics), [`distributed-services`](https://github.com/seungwoo7050/guides/tree/distributed-services), [`machine-learning`](https://github.com/seungwoo7050/guides/tree/machine-learning), [`cybersecurity`](https://github.com/seungwoo7050/guides/tree/cybersecurity), [`platform-engineering`](https://github.com/seungwoo7050/guides/tree/platform-engineering) |
| `continues_to` | [`computer-graphics`](https://github.com/seungwoo7050/guides/tree/computer-graphics), [`distributed-services`](https://github.com/seungwoo7050/guides/tree/distributed-services), [`machine-learning`](https://github.com/seungwoo7050/guides/tree/machine-learning), [`cybersecurity`](https://github.com/seungwoo7050/guides/tree/cybersecurity) |

트랙별 선형 경로에는 `computer-architecture`, `web-app`, `database-systems`, `web-infra` 같은 추가 기반이 포함될 수 있습니다. 이는 해당 직무의 권장 순서이지 `game-development`의 직접 필수 관계를 바꾸지 않습니다. 일곱 경로의 정확한 순서는 [직무별 진입 지도](reference/role-entry-map.md)에 있습니다.

### 이 브랜치가 소유하지 않는 범위

`main`의 `excludes`는 다음 네 항목입니다.

1. GPU 렌더링 파이프라인과 shader 내부구조
2. 운영체제·네트워크 프로토콜·분산 합의의 일반 원리
3. 특정 상용 엔진 API 전체
4. 게임 기획·아트·사운드 제작 직무 교육

이 브랜치는 위 원리를 다시 가르치지 않습니다. **게임이라는 실행 환경에서 해당 기반들이 언제 충돌하고 어떤 계약이 필요한지**에 집중합니다.

## 학습 구조

### Part I. 게임 runtime과 상태

1. [게임 제품과 runtime 계약](docs/01-game-product-and-runtime-contract.md)
2. [게임 루프, 시간과 프레임](docs/02-game-loop-time-and-frames.md)
3. [입력, 명령, 카메라와 게임 UI](docs/03-input-command-camera-and-ui.md)
4. [월드, 장면, 엔티티와 컴포넌트 수명](docs/04-world-scene-entity-component-lifecycles.md)
5. [게임 규칙, 진행 상태와 data-driven 설계](docs/05-gameplay-rules-progression-and-data.md)

### Part II. 콘텐츠와 시뮬레이션

6. [자산 import, cooking, loading과 memory residence](docs/06-assets-import-cooking-loading-and-memory.md)
7. [충돌, 물리, 이동과 좌표 계약](docs/07-collision-physics-movement-and-space.md)
8. [애니메이션, 오디오, VFX와 표현 경계](docs/08-animation-audio-vfx-and-presentation.md)
9. [저장, migration, replay와 determinism](docs/09-save-migration-replay-and-determinism.md)
10. [게임 AI, navigation과 behavior 통합](docs/10-game-ai-navigation-and-behavior.md)

### Part III. 온라인·품질·생산

11. [네트워크 권위, replication과 latency](docs/11-network-authority-replication-and-latency.md)
12. [에디터 도구, 빌드와 콘텐츠 검증](docs/12-tools-editor-builds-and-content-validation.md)
13. [테스트, 디버깅, telemetry와 재현](docs/13-testing-debugging-telemetry-and-reproduction.md)
14. [성능 예산, profiling과 scalability](docs/14-performance-budgets-profiling-and-scalability.md)
15. [플랫폼 입력, 접근성, 저장 수명과 release](docs/15-platform-accessibility-lifecycle-and-release.md)
16. [게임 팀 경계와 안전한 변경](docs/16-game-team-interfaces-and-change-management.md)
17. [Vertical Slice Capstone](docs/17-capstone.md)

[`docs/90-engine-and-source-map.md`](docs/90-engine-and-source-map.md)는 18번째 필수 단계가 아니라, 01~17을 선택한 엔진의 symbol·callback·asset/tool entry에 대응할 때 필요에 따라 확인하는 지원 자료입니다.

## 정본 진행 순서

문서를 모두 읽은 뒤 실습을 몰아서 하지 않습니다. 먼저 로드맵을 읽고 외부 learner workspace를 한 번 만든 다음, 아래 표의 문서→관찰→직접 수행→검증→비교 순서를 반복합니다.

```sh
./prepare.sh
WORK_PARENT="$(mktemp -d)"
make workspace DEST="$WORK_PARENT/game-development"
WORK_ROOT="$WORK_PARENT/game-development"
CAP="$WORK_ROOT/relay-arena-vertical-slice"
```

실습 검증은 다음 공통 형태로 실행합니다. 표의 `EXERCISE` 값과 실제 slug를 사용합니다.

```sh
make submission \
  EXERCISE=01 \
  SUBMISSION="$WORK_ROOT/exercises/01-time-step-analysis/submission"
```

| 순서 | 문서 | 관찰 예제 | 직접 수행 | 수정 위치 | 검증 | 완료 뒤 비교·다음 |
|---:|---|---|---|---|---|---|
| 0 | [로드맵](docs/00-roadmap.md) | — | 목표 직무와 Capstone 구현 경로를 고르고 외부 workspace 생성 | `$WORK_ROOT` | `./prepare.sh`; `make workspace DEST=...` | workspace 구조 확인 뒤 01 |
| 1 | [01 제품·runtime 계약](docs/01-game-product-and-runtime-contract.md) | — | process→frontend→world→match→entity 초안 | `$CAP/submission/runtime-state-map.md` | 문서 완료 기준과 사람 검토 | 자신의 초안 뒤 Capstone `reference/artifacts/runtime-state-map.md`; 02 |
| 2 | [02 game loop·시간](docs/02-game-loop-time-and-frames.md) | [fixed-step replay](examples/fixed-step-replay/README.md) | [실습 01](exercises/01-time-step-analysis/README.md)과 clock·fixed-step 계약 | 실습 01 `submission/*`; `$CAP/submission/time-and-input-contract.md` | `make example`; `make submission` (`EXERCISE=01`) | 실습 01 reference와 Capstone artifact; 03 |
| 3 | [03 입력·command·UI](docs/03-input-command-camera-and-ui.md) | — | [실습 02](exercises/02-input-command-contract/README.md)와 action→command·focus 계약 | 실습 02 `submission/*`; `$CAP/submission/time-and-input-contract.md` | `make submission` (`EXERCISE=02`) | 실습 02 reference; 04 |
| 4 | [04 world·entity lifecycle](docs/04-world-scene-entity-component-lifecycles.md) | — | [실습 03](exercises/03-world-lifecycle-review/README.md)과 owner·lifecycle 보완 | 실습 03 `submission/*`; `$CAP/submission/runtime-state-map.md`, `state-ownership.csv`, `world-and-asset-plan.md` | `make submission` (`EXERCISE=03`) | 실습 03 및 대응 Capstone references; 05 |
| 5 | [05 gameplay rule·progression](docs/05-gameplay-rules-progression-and-data.md) | — | command acceptance, match invariant와 persistent owner 작성 | `$CAP/submission/gameplay-rules.md`, `state-ownership.csv` | 문서 완료 기준; release compatibility는 15에서 검증 | 자신의 초안 뒤 대응 Capstone references; 06 |
| 6 | [06 asset·loading·memory](docs/06-assets-import-cooking-loading-and-memory.md) | — | [실습 04](exercises/04-asset-loading-plan/README.md)와 load graph·gate·budget | 실습 04 `submission/*`; `$CAP/submission/world-and-asset-plan.md` | `make submission` (`EXERCISE=04`) | 실습 04 및 Capstone reference; 07 |
| 7 | [07 collision·movement·space](docs/07-collision-physics-movement-and-space.md) | — | transform writer와 collision→movement→correction 순서 | `$CAP/submission/movement-and-space.md` | 문서 완료 기준; authority correction은 11에서 검증 | 자신의 초안 뒤 Capstone reference; 08 |
| 8 | [08 animation·audio·VFX](docs/08-animation-audio-vfx-and-presentation.md) | — | presentation event, acknowledgement와 dedupe 계약 | `$CAP/submission/presentation-contract.md` | 문서 완료 기준과 사람 검토 | 자신의 초안 뒤 Capstone reference; 09 |
| 9 | [09 save·migration·replay](docs/09-save-migration-replay-and-determinism.md) | 앞서 실행한 [fixed-step replay](examples/fixed-step-replay/README.md)의 hash 재해석 | [실습 05](exercises/05-save-and-replay-migration/README.md)와 save/replay 계약 | 실습 05 `submission/*`; `$CAP/submission/save-and-replay.md` | `make submission` (`EXERCISE=05`) | 실습 05 및 Capstone reference; 10 |
| 10 | [10 AI·navigation 통합](docs/10-game-ai-navigation-and-behavior.md) | — | 필수 command·lifecycle·budget 경계를 기존 산출물에 반영; AI 전용 분석은 선택 | 필수 movement·presentation·authority 산출물; 선택 `$CAP/submission/optional/ai-and-navigation.md` | 문서 완료 기준과 사람 검토 | 선택 분석에는 단일 답안을 강제하지 않음; 11 |
| 11 | [11 authority·replication·latency](docs/11-network-authority-replication-and-latency.md) | — | [실습 06](exercises/06-authority-and-latency/README.md)과 intent·validation·correction | 실습 06 `submission/*`; `$CAP/submission/authority-and-latency.md` | `make submission` (`EXERCISE=06`) | 실습 06 및 Capstone reference; 12 |
| 12 | [12 tool·build·content validation](docs/12-tools-editor-builds-and-content-validation.md) | — | build/content identity와 validator evidence 연결 | `$CAP/submission/world-and-asset-plan.md`, `traceability-matrix.csv` | 실습 04 결과 재검토; release gate는 15 | 자신의 초안 뒤 대응 Capstone references; 13 |
| 13 | [13 test·debug·telemetry](docs/13-testing-debugging-telemetry-and-reproduction.md) | — | test pyramid, trace, known-bad와 learner evidence 계획 | `$CAP/submission/test-and-observability-plan.md` | `make meta`로 repository checker 방향 확인 | 자신의 초안 뒤 Capstone reference; 14 |
| 14 | [14 performance·profiling](docs/14-performance-budgets-profiling-and-scalability.md) | — | [실습 07](exercises/07-performance-budget-review/README.md)과 target budget·전후 profile | 실습 07 `submission/*`; `$CAP/submission/performance-and-release.md` | `make submission` (`EXERCISE=07`) | 실습 07 및 Capstone reference; 15 |
| 15 | [15 platform·accessibility·release](docs/15-platform-accessibility-lifecycle-and-release.md) | — | [실습 08](exercises/08-release-readiness/README.md)과 platform·save·release gate | 실습 08 `submission/*`; `$CAP/submission/performance-and-release.md` | `make submission` (`EXERCISE=08`) | 실습 08 및 Capstone reference; 16 |
| 16 | [16 팀 경계·안전한 변경](docs/16-game-team-interfaces-and-change-management.md) | — | requirement→owner→implementation→test→release와 issue 순서 확정 | `$CAP/submission/traceability-matrix.csv`, `change-plan.md` | 필수 Profile A top-level 13개 사람 검토 | 자신의 초안 뒤 대응 Capstone references; 17 |
| 17 | [17 Vertical Slice Capstone](docs/17-capstone.md) | — | [Relay Arena](projects/relay-arena-vertical-slice/README.md)의 필수 Profile A 13개와 Profile B 구현·evidence bundle 완성 | `$CAP/submission/` top-level 13개; `$CAP/starter/relay_arena.py`; `$CAP/evidence/` | `python3 projects/relay-arena-vertical-slice/tests/check_contract.py --implementation "$CAP/starter/relay_arena.py"` 또는 동등 engine assertions | learner 결과 뒤 `reference/relay_arena.py`, `reference/artifacts/`; 실제 프로젝트 또는 선택 Profile C |
| 참고 | [90 엔진 교차표](docs/90-engine-and-source-map.md) | — | 선택 엔진의 symbol·callback·asset/tool entry에 개념 대응 | 실제 프로젝트 조사 기록 | engine version과 source revision을 사람이 확인 | 01~17에서 필요할 때 사용 |

Exercise `reference/`와 Capstone artifact reference는 자신의 첫 결과를 만든 뒤 비교합니다. Capstone black-box test와 `expected-contract.json`은 구현 전에 checker 방향을 확인하는 oracle로 실행할 수 있지만, `reference/relay_arena.py` source는 learner 구현을 시도한 뒤 읽습니다. root [`reference/`](reference/)는 glossary·checklist·crosswalk 같은 quick-reference 문서이며 exercise 답안이 아닙니다. `./verify.sh`는 repository 자체를 검증하며 외부 learner workspace의 완료를 대신하지 않습니다.

## 단계 실습

실습은 특정 엔진 프로젝트를 요구하지 않습니다. 제공된 system brief, trace, manifest와 profile을 분석해 **상태·수명·실패·검증 산출물**을 작성합니다.

| 실습 | 핵심 결과물 |
|---|---|
| [01 시간 단계 분석](exercises/01-time-step-analysis/README.md) | variable frame에서 fixed step, catch-up, pause와 overload 판정 |
| [02 입력과 명령](exercises/02-input-command-contract/README.md) | device event에서 action·command·UI focus로 이어지는 계약 |
| [03 월드와 객체 수명](exercises/03-world-lifecycle-review/README.md) | create·activate·stream·destroy와 cross-reference 위험 분석 |
| [04 자산과 loading](exercises/04-asset-loading-plan/README.md) | dependency·bundle·preload·unload·memory budget 계획 |
| [05 save와 replay](exercises/05-save-and-replay-migration/README.md) | schema migration, unknown field, replay divergence 조사 |
| [06 네트워크 권위](exercises/06-authority-and-latency/README.md) | client intent, server validation, prediction·correction 계약 |
| [07 성능 예산](exercises/07-performance-budget-review/README.md) | target device profile에서 CPU·GPU·memory·loading 병목 판정 |
| [08 릴리스 검토](exercises/08-release-readiness/README.md) | 입력·접근성·save·crash·telemetry·content validation release gate |

각 실습은 초기 자료, 의도적으로 미완성인 template, 완성 reference/expected evidence, 대표 오답과 사람 검토 질문을 제공합니다. 공통 제출 검사기는 문구나 내부 구현이 아니라 fixture가 결정하는 CSV/JSON 관측값과 공개 불변식을 판정하며, reference 통과·template와 알려진 오답 거부를 함께 확인합니다.

## 실행 예제

[`examples/fixed-step-replay`](examples/fixed-step-replay/README.md)는 Python 표준 라이브러리만으로 작은 결정적 simulation을 실행하고 같은 input trace에서 같은 state hash가 나오는지 확인합니다. 이 예제는 게임 엔진을 대신하지 않고 다음 계약만 관찰합니다.

```text
render frame duration
→ accumulator
→ bounded fixed step
→ command consumption
→ canonical state serialization
→ replay hash
```

## Capstone

[`projects/relay-arena-vertical-slice`](projects/relay-arena-vertical-slice/README.md)는 1~2명이 구현할 수 있는 작은 arena game을 가정합니다.

완료에는 두 묶음이 모두 필요합니다.

```text
13개 설계·검토 산출물
runtime·state ownership map
→ fixed-step·input command trace
→ scene/entity lifecycle
→ asset manifest와 loading plan
→ movement·presentation·save/replay
→ authority·latency model
→ test·telemetry·performance budget
→ release decision

실행 가능한 구현 evidence
input command → bounded fixed-step → gameplay state
→ presentation event → save/replay
→ failure reproduction → profile 전후 → regression result
```

필수 Profile B의 기본 경로는 Python 3.10 표준 라이브러리 기반 headless starter입니다. `simulate`, `migrate-save`, `profile`과 같은 public contract로 정상·hitch·duplicate/non-owner·stale resource·corrupt save·replay divergence·수정 전후를 검사합니다. Python 경로 자체는 Unity, Unreal Engine, Godot 또는 자체 framework에서 같은 assertion과 identity/evidence를 제공하는 동등 경로로 대체할 수 있지만, 실행 가능한 구현 evidence는 생략할 수 없습니다. AI 전용 추가 산출물과 실제 network transport는 선택 심화입니다.

## 준비와 검증

```sh
./prepare.sh
make check
make fixtures
make example
make capstone
make meta
./verify.sh
```

`prepare.sh`는 Python 버전과 저장소 구조를 확인하고 일회성 준비 marker를 만듭니다. 시스템 패키지를 설치하거나 사용자 파일을 수정하지 않습니다.

`verify.sh`는 다음을 검사합니다.

- 필수 문서·실습·Capstone 구조
- README의 문서→예제→실습→수정 위치→검증→reference 학습 지도
- Markdown 상대 링크
- JSON fixture의 schema와 교차 참조
- 문서 공통 절과 ownership 경계
- example과 Capstone reference의 project-wide Implementation annotation scope·연속성·금지 위치
- fixed-step replay 예제의 deterministic state hash
- 8개 실습의 reference 통과, 미완성 template와 대표 오답 거부
- Capstone reference 통과, starter와 네 종류 behavioral mutant 거부
- learner workspace의 non-overwrite·symlink 거부와 필수 13개·선택 AI 분리
- 검증 전후 원본 source snapshot 불변성

학습자 파일은 저장소 밖 새 절대 경로에 만듭니다. 생성기는 기존 경로와 symlink를 덮어쓰지 않습니다.

```sh
WORK_PARENT="$(mktemp -d)"
make workspace DEST="$WORK_PARENT/game-development"
```

실습을 작성한 뒤 같은 공개 계약으로 기계 판정 부분을 확인합니다. 예를 들어 01 제출 경로는 다음과 같습니다.

```sh
make submission \
  EXERCISE=01 \
  SUBMISSION="$WORK_PARENT/game-development/exercises/01-time-step-analysis/submission"
```

성공 시 `AUTOMATED_OK`와 자동화하지 않은 판단의 `MANUAL_REVIEW_REQUIRED`가 따로 출력됩니다. 로컬 marker와 Python cache만 정리하려면 다음을 실행합니다. 학습자 workspace는 삭제하지 않습니다.

```sh
make clean
```

세부 계약 연결은 [완료 증거와 계약 추적표](reference/completion-evidence.md), 데이터·권한·cleanup·라이선스 경계는 [안전·환경·증거 계약](reference/safety-and-environment.md)에서 확인합니다.

## 학습 방식과 한계

- 문서와 공통 fixture는 엔진 독립적이며, 선택한 엔진·언어의 설치와 API는 해당 공식 자료에서 확인합니다.
- Capstone은 범용 게임 엔진이나 상용 수준 게임의 완성을 요구하지 않습니다.
- “60 FPS”, “deterministic”, “server authoritative” 같은 표현은 측정 환경·보장 범위·실패 조건과 함께만 근거로 사용합니다.
- 자동 검사는 구조와 공개 행동을 확인하지만 설명의 정확성이나 교육적 완성을 대신 판정하지 않습니다.
- headless path는 실제 engine callback, GPU, target hardware, platform lifecycle/storage 또는 실제 network transport를 증명하지 않습니다.

이 가이드의 종료점은 특정 엔진의 인증서가 아니라, 게임 프로젝트의 한 기능을 **시간·상태·자산·표현·저장·네트워크·성능·릴리스 계약**으로 분해하고 실제 코드베이스에서 작은 변경을 완성할 수 있는 상태입니다.
