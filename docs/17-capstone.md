# Vertical Slice Capstone

## 목적

`Relay Arena`라는 작은 top-down arena game의 한 match를 설계하고 실행 가능한 작은 gameplay slice로 검증합니다. 이 Capstone은 완성 게임이나 범용 엔진을 만드는 과제가 아닙니다. 문서에서 배운 상태·수명·실패·검증을 한 feature 경로와 재현 가능한 증거 묶음으로 연결하는 과제입니다.

```text
boot/menu
→ arena content load
→ player input
→ fixed-step movement and interaction
→ match rule and result
→ presentation
→ save/replay
→ client/server authority boundary
→ profile and release decision
```

프로젝트 입력, 제출 템플릿과 fixture는 [`projects/relay-arena-vertical-slice`](../projects/relay-arena-vertical-slice/README.md)에 있습니다.

완료에는 두 묶음이 모두 필요합니다.

1. 정확히 13개의 필수 template 기반 설계·검토 산출물
2. 실행 가능한 구현과 public contract test, 정상·경계·실패·수정 전후 evidence bundle

네트워크 transport 구현과 `template/optional/ai-and-navigation.md`는 선택 심화입니다. 문서 산출물만 완성한 상태는 브랜치의 세 종료 능력을 모두 충족하지 않습니다.

## 제품 brief

- 1명의 player가 작은 arena에서 relay core 세 개를 활성화합니다.
- player는 이동, dash와 interact command를 가집니다.
- moving hazard와 간단한 agent가 방해합니다.
- 모든 core를 활성화하면 match result가 확정됩니다.
- local best time과 accessibility/input setting을 저장합니다.
- replay profile은 command trace에서 match result와 state hash를 재현합니다.
- network profile은 두 client가 server-authoritative match에 참여한다고 가정합니다.

아트 품질과 콘텐츠 양은 평가하지 않습니다. placeholder로 충분합니다.

## 필수 Profile A — 정확히 13개 설계·검토 산출물

`template/` top-level의 다음 13개는 모두 필수입니다. 선택 AI 산출물은 `template/optional/`에 분리돼 있습니다.

| 번호 | 필수 제출 파일 | 확인할 계약 |
|---:|---|---|
| 1 | `runtime-state-map.md` | process→frontend→world→match→entity 전이, owner, 취소와 cleanup |
| 2 | `time-and-input-contract.md` | real/game/fixed/render/server clock, bounded catch-up, action·command·focus |
| 3 | `state-ownership.csv` | authoritative owner·writer·reader·직렬화·복제·수명·불변식 |
| 4 | `world-and-asset-plan.md` | scene/entity lifecycle, stable asset id, dependency, load gate, fallback |
| 5 | `gameplay-rules.md` | match phase, command acceptance, core/result invariant, commit boundary |
| 6 | `movement-and-space.md` | 좌표·collision query·movement·correction의 적용 순서와 writer |
| 7 | `presentation-contract.md` | animation·audio·VFX·UI event와 acknowledgement/dedupe 경계 |
| 8 | `save-and-replay.md` | save v1→v2 migration, replay hash, determinism 범위와 divergence |
| 9 | `authority-and-latency.md` | client intent, server validation, duplicate/stale/non-owner 정책 |
| 10 | `test-and-observability-plan.md` | rule/simulation/system/platform test, trace, known-bad meta-test |
| 11 | `performance-and-release.md` | target budget, 전후 profile, 접근성·platform gate와 알려진 한계 |
| 12 | `traceability-matrix.csv` | requirement→owner→implementation→test→telemetry→release evidence |
| 13 | `change-plan.md` | review 가능한 구현 순서, compatibility, migration과 rollback |

`state-ownership.csv`의 header는 실제 template과 동일해야 합니다.

```text
state_id,scope,authoritative_owner,writer,readers,serialized_in_save,recorded_in_replay,replicated,lifetime,invariant
```

선택 산출물 [`optional/ai-and-navigation.md`](../projects/relay-arena-vertical-slice/template/optional/ai-and-navigation.md)는 agent의 sensing·decision·path lifetime을 게임 계층 통합 사례로 확장합니다. learner workspace에서는 `submission/optional/`에 놓이며, 제출하지 않아도 13개 필수 top-level 산출물 수는 변하지 않습니다.

Profile A는 구현 전에 상태·책임·실패·검증 판단을 고정합니다. 이것만으로 실제 update/render/asset/tool 경계 복원, 작은 기능 구현, profiling 기반 수정이 모두 입증되지는 않습니다.

## 필수 Profile B — 실행 가능한 구현과 evidence bundle

기본 경로는 외부 서비스·엔진 설치 없이 Python 3.10 이상에서 실행하는 headless 구현입니다.

- 의도적으로 미완성인 [`starter/relay_arena.py`](../projects/relay-arena-vertical-slice/starter/relay_arena.py)
- 공개 행동을 보여 주는 [`reference/relay_arena.py`](../projects/relay-arena-vertical-slice/reference/relay_arena.py)
- canonical state와 필수 authority rejection oracle인 [`reference/expected-contract.json`](../projects/relay-arena-vertical-slice/reference/expected-contract.json)
- black-box [`tests/check_contract.py`](../projects/relay-arena-vertical-slice/tests/check_contract.py)
- reference의 13개 산출물 예시 [`reference/artifacts/`](../projects/relay-arena-vertical-slice/reference/artifacts/)
- headless/실제 엔진 경계를 복원한 [`reference/boundary-recovery.md`](../projects/relay-arena-vertical-slice/reference/boundary-recovery.md)

reference가 통과하고 starter가 미완성으로 거부되는지 먼저 확인한 뒤, starter를 저장소 밖 학습자 작업 디렉터리에 복사해 구현합니다.

```sh
python3 projects/relay-arena-vertical-slice/tests/check_contract.py \
  --implementation projects/relay-arena-vertical-slice/reference/relay_arena.py
python3 projects/relay-arena-vertical-slice/tests/check_contract.py \
  --implementation projects/relay-arena-vertical-slice/starter/relay_arena.py \
  --expect incomplete
```

학습자 구현은 다음 세 CLI를 제공해야 합니다.

| CLI | 필수 공개 행동 |
|---|---|
| `simulate` | smooth/jittered/hitch schedule에서 같은 canonical gameplay state, bounded catch-up, command·presentation dedupe, stale resource와 optional cosmetic fallback, authority 거부 근거 |
| `migrate-save` | v1 save를 v2로 migration하고 corrupt 입력 실패 때 기존 출력을 덮어쓰지 않는 atomic publish |
| `profile` | 재현한 dependency/loading hotspot의 수정 전후 비교와 gameplay invariant 보존 |

구체적인 실행 명령과 evidence bundle layout은 [프로젝트 README](../projects/relay-arena-vertical-slice/README.md)의 “기본 offline 실행 경로”를 따릅니다. 최소 bundle에는 구현 identity, 실행 명령, 정상·hitch·duplicate·non-owner·stale-load·missing-cosmetic 결과, save migration과 corrupt rejection, profile 전후 결과, reference/starter/학습자 contract test 로그, 알려진 한계가 들어갑니다.

### 실제 엔진의 동등 구현

Unity, Unreal Engine, Godot 또는 자체 framework의 작은 구현으로 headless path를 대체할 수 있습니다. 이 경우에도 Move/Dash/Interact→authoritative state→presentation→save 경로와 같은 실패 불변식을 실행해 보여 주고, project/build/content revision, 재현 명령, test 결과, profile capture와 cleanup 절차를 evidence bundle에 남깁니다. Python contract와 같은 JSON을 내는 adapter를 제공하거나, 각 공개 assertion에 대응하는 엔진 test·trace를 mapping 문서로 제시합니다.

### headless 경로가 보장하지 않는 것

기본 reference/test 통과는 다음을 증명하지 않습니다.

- 실제 엔진 callback 순서, scene/object 수명과 thread/job scheduling
- GPU rendering, shader, animation·audio·VFX 출력과 frame capture
- target hardware의 CPU/GPU frame time, memory residence와 loading 시간
- 실제 플랫폼 input remap, focus, suspend/resume, storage durability와 접근성 동작
- 실제 network transport의 latency·loss·reordering, reconnect, bandwidth와 보안

이 항목을 종료 근거로 주장하려면 실제 엔진·기기·플랫폼·network 환경의 추가 수동/자동 증거가 필요합니다.

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
- reference 통과, starter 거부와 학습자 구현 통과를 함께 기록합니다.
- 같은 workload의 profile 수정 전후와 보존한 gameplay invariant를 evidence bundle에서 추적할 수 있습니다.

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
- reference와 동일한 내부 구현 구조

## 완료 뒤 확장

- gameplay/client: 실제 엔진 project에서 한 feature PR
- engine: custom subsystem, memory/streaming/tool 개선
- rendering: `computer-graphics`로 이동
- server: `distributed-services`, `web-infra`로 이동
- tools/build: `python`, `platform-engineering`으로 이동
- data/ML: `data-engineering`, `machine-learning`으로 이동
- security/anti-cheat: `cybersecurity`로 이동

Capstone의 목표는 모든 직무를 한 사람이 수행하는 것이 아니라, 각 직무가 같은 game state와 release를 어떻게 공유하는지 이해한 뒤 자신의 경로에서 깊이를 만드는 것입니다.
