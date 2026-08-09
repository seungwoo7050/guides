# Relay Arena Vertical Slice

## 과제 목적

작은 top-down arena match를 대상으로 게임 runtime의 공통 계약을 하나의 trace로 연결한다. 완료하려면 **정확히 13개의 template 기반 설계·검토 산출물**과 **실행 가능한 구현 evidence bundle**이 모두 필요하다. 기본 구현은 offline Python 3.10+ headless path이며, 동등한 실제 엔진 구현으로 대체할 수 있다. AI 산출물과 실제 network transport는 선택 심화다.

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

## 구현·검증 자료

| 자료 | 역할 |
|---|---|
| [`starter/relay_arena.py`](starter/relay_arena.py) | import는 가능하지만 public contract가 의도적으로 미완성인 학습자 시작점 |
| [`reference/relay_arena.py`](reference/relay_arena.py) | 한 가지 허용 설계와 CLI 공개 행동을 보여 주는 headless reference |
| [`reference/expected-contract.json`](reference/expected-contract.json) | canonical state와 필수 authority rejection을 고정한 비교 oracle |
| [`tests/check_contract.py`](tests/check_contract.py) | 구현 내부 모양이 아니라 CLI 결과와 불변식을 검사하는 black-box test |
| [`reference/artifacts/`](reference/artifacts/) | 13개 필수 template 산출물의 reference 예시 |
| [`reference/boundary-recovery.md`](reference/boundary-recovery.md) | update/render·presentation·asset·tool 경계를 headless 증거와 실제 엔진 확인 항목에 mapping한 예시 |

## 필수 Profile A — 정확히 13개 제출 파일

`template/`을 개인 작업 디렉터리에 복사한 뒤 작성한다.

| 번호 | 제출 파일 | 확인할 계약 |
|---:|---|---|
| 1 | [`runtime-state-map.md`](template/runtime-state-map.md) | process→world→match→entity 상태와 전이 |
| 2 | [`time-and-input-contract.md`](template/time-and-input-contract.md) | clock, fixed step, action·command 소비 |
| 3 | [`state-ownership.csv`](template/state-ownership.csv) | authoritative owner·writer·reader·save·replay·replication·수명 |
| 4 | [`world-and-asset-plan.md`](template/world-and-asset-plan.md) | scene/entity lifecycle와 stable asset/load gate |
| 5 | [`gameplay-rules.md`](template/gameplay-rules.md) | command acceptance와 match invariant |
| 6 | [`movement-and-space.md`](template/movement-and-space.md) | 좌표·collision·movement·correction 적용 순서 |
| 7 | [`presentation-contract.md`](template/presentation-contract.md) | animation/audio/VFX/UI event 소비와 dedupe |
| 8 | [`save-and-replay.md`](template/save-and-replay.md) | migration과 replay divergence |
| 9 | [`authority-and-latency.md`](template/authority-and-latency.md) | intent·validation·prediction·correction |
| 10 | [`test-and-observability-plan.md`](template/test-and-observability-plan.md) | test pyramid, trace와 known-bad fixture |
| 11 | [`performance-and-release.md`](template/performance-and-release.md) | target budget·전후 profile·접근성·release gate |
| 12 | [`traceability-matrix.csv`](template/traceability-matrix.csv) | requirement→owner→implementation→test→evidence 연결 |
| 13 | [`change-plan.md`](template/change-plan.md) | 구현 issue 순서, compatibility, migration과 rollback |

`state-ownership.csv` header는 template과 같은 다음 10개 field를 사용한다.

```text
state_id,scope,authoritative_owner,writer,readers,serialized_in_save,recorded_in_replay,replicated,lifetime,invariant
```

[`ai-and-navigation.md`](template/ai-and-navigation.md)는 선택 산출물이다. 제출하더라도 필수 파일 수를 14개로 세지 않으며, 제출하지 않아도 위 13개 계약은 줄어들지 않는다.

Profile A만으로는 실제 작은 기능 구현이나 profiling 기반 수정 종료 능력을 충족하지 않는다. 아래 Profile B의 실행 증거도 필수다.

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

### 4. public CLI 구현

기본 headless 경로에서는 `simulate`, `migrate-save`, `profile`을 구현하고 reference와 같은 public contract test를 실행한다. 실제 엔진 대체 경로에서는 같은 assertion을 engine test·trace·adapter에 mapping한다. 구현 내부 구조를 reference와 같게 만들 필요는 없다.

### 5. 실패 주입 연결

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

### 6. release 근거까지 추적

기능 구현 완료를 release 완료로 보지 않는다. 정확한 candidate build/content/save/protocol identity와 target-device evidence를 `traceability-matrix.csv`에 연결한다.

## 필수 Profile B — 실행 가능한 구현 증거

### 기본 offline 실행 경로

저장소 root가 아니라 이 프로젝트 디렉터리에서 다음 명령을 실행한다. Python 3.10 이상과 표준 라이브러리만 사용하며 외부 서비스, 유료 자원과 엔진 설치가 필요하지 않다.

먼저 oracle과 검사기 방향을 확인한다.

```sh
python3 --version
python3 tests/check_contract.py --implementation reference/relay_arena.py
python3 tests/check_contract.py --implementation starter/relay_arena.py --expect incomplete
```

첫 명령은 `CAPSTONE_CONTRACT_OK`, 두 번째는 `EXPECTED_INCOMPLETE`여야 한다. reference는 허용된 한 설계일 뿐 복사 답안이 아니다. 저장소 root의 workspace 생성기로 starter와 입력을 저장소 밖 새 디렉터리에 원자적으로 복사하고 그 복사본만 수정한다. 대상은 존재하지 않는 절대 경로여야 하며 기존 경로와 symlink는 거부된다.

```sh
WORK_PARENT="$(mktemp -d)"
../../scripts/new-workspace.sh "$WORK_PARENT/game-development"
RELAY_WORK="$WORK_PARENT/game-development/relay-arena-vertical-slice"
RELAY_IMPL="$RELAY_WORK/starter/relay_arena.py"
mkdir -p "$RELAY_WORK/evidence/simulate" "$RELAY_WORK/evidence/save" "$RELAY_WORK/evidence/profile" "$RELAY_WORK/evidence/tests"
```

### 필수 CLI

#### `simulate`

```sh
python3 "$RELAY_IMPL" simulate \
  --inputs "$RELAY_WORK/inputs" \
  --schedule smooth \
  --scenario normal \
  --output "$RELAY_WORK/evidence/simulate/smooth-normal.json"
python3 "$RELAY_IMPL" simulate \
  --inputs "$RELAY_WORK/inputs" \
  --schedule hitch \
  --scenario normal \
  --output "$RELAY_WORK/evidence/simulate/hitch-normal.json"
```

최종 evidence에는 다음 조합을 모두 남긴다.

| schedule | scenario | 판단할 공개 행동 |
|---|---|---|
| `smooth`, `jittered`, `hitch` | `normal` | frame schedule이 달라도 canonical state hash가 같고 hitch catch-up이 상한 4에서 중단됨 |
| `smooth` | `duplicate` | 중복 command가 거부되고 canonical state가 변하지 않음 |
| `smooth` | `non-owner` | non-owner intent가 거부됨 |
| `smooth` | `stale-load` | owner가 사라진 completion을 버리고 resource baseline을 복원함 |
| `smooth` | `missing-cosmetic` | control-ready invariant를 보존한 채 cosmetic만 degrade함 |

입력 fixture의 duplicate, stale snapshot과 client result claim도 `authority_evidence`에서 거부돼야 하며 match result와 presentation one-shot은 한 번만 확정돼야 한다.

#### `migrate-save`

```sh
python3 "$RELAY_IMPL" migrate-save \
  --input "$RELAY_WORK/inputs/save-v1.json" \
  --contract "$RELAY_WORK/inputs/save-v2-contract.json" \
  --output "$RELAY_WORK/evidence/save/save-v2.json"
```

v1→v2에서 stable id, `best_time_ms`, input/accessibility setting을 보존한다. corrupt/unsupported 입력은 non-zero로 실패하고 이미 존재하는 output을 덮어쓰지 않아야 한다. public contract test가 sentinel을 사용해 이 atomic publish 불변식을 검사한다.

#### `profile`

```sh
python3 "$RELAY_IMPL" profile \
  --inputs "$RELAY_WORK/inputs" \
  --output "$RELAY_WORK/evidence/profile/before-after.json"
```

재현한 dependency/loading hotspot의 같은 workload 전후 결과, 적용한 수정과 `invariants_preserved`를 기록한다. deterministic counter 개선은 회귀 근거이지 target hardware timing으로 해석하지 않는다.

구현이 끝나면 black-box test를 실행한다.

```sh
python3 tests/check_contract.py --implementation "$RELAY_IMPL"
```

reference 통과, starter 거부, 학습자 구현 통과를 모두 기록해야 검사기가 한쪽으로만 성공하는 빈 검사가 아님을 보여 줄 수 있다.

### 필수 evidence bundle

13개 template 산출물과 별도로 다음 실행 근거 묶음을 제출한다. 이 bundle은 14번째 template 파일이라는 뜻이 아니라 구현 종료 능력을 판단하는 필수 증거다.

```text
evidence/
├── implementation-identity.md
├── commands.txt
├── simulate/
│   ├── smooth-normal.json
│   ├── jittered-normal.json
│   ├── hitch-normal.json
│   ├── smooth-duplicate.json
│   ├── smooth-non-owner.json
│   ├── smooth-stale-load.json
│   └── smooth-missing-cosmetic.json
├── save/
│   ├── save-v2.json
│   └── corrupt-rejection.txt
├── profile/
│   └── before-after.json
├── tests/
│   ├── reference-pass.txt
│   ├── starter-incomplete.txt
│   └── learner-pass.txt
└── limitations.md
```

`implementation-identity.md`에는 source revision, Python 또는 engine/build/content identity와 구현 파일 위치를 기록한다. `commands.txt`에는 실제 실행한 명령과 exit status를, `limitations.md`에는 생략한 환경과 그 때문에 보장하지 못하는 항목을 기록한다. reference의 작성 예시는 [`reference/artifacts/`](reference/artifacts/)와 [`reference/boundary-recovery.md`](reference/boundary-recovery.md)에서 비교한다.

### 실제 엔진의 동등 구현

Unity, Unreal Engine, Godot 또는 자체 framework 구현으로 Python headless path를 대체할 수 있다. 다음 조건은 그대로 필수다.

- Move/Dash/Interact가 gameplay command를 거쳐 authoritative state를 바꾸고 presentation과 save에 투영됨
- normal, frame variation, duplicate/non-owner, stale resource, missing cosmetic와 corrupt save를 실행해 같은 불변식을 검증함
- project/build/content revision, 준비·실행·cleanup 명령, automated test와 실패 로그를 보존함
- 수정 전후 같은 workload의 profile과 보존한 invariant를 제시함
- Python JSON contract를 내는 adapter 또는 public assertion→engine test·trace mapping을 제공함

### headless path의 한계

`CAPSTONE_CONTRACT_OK`는 다음을 증명하지 않는다.

- 실제 engine callback order, scene/object lifetime과 thread/job scheduling
- 실제 GPU rendering, shader, animation·audio·VFX 출력과 frame capture
- target hardware의 CPU/GPU frame time, memory residence와 loading time
- 플랫폼 input remap, focus, suspend/resume, storage durability와 접근성 동작
- 실제 network transport의 latency·loss·reordering, reconnect, bandwidth와 보안

이 항목을 완료 근거로 주장하려면 실제 engine/device/platform/network 환경에서 추가 evidence를 남긴다. [`reference/boundary-recovery.md`](reference/boundary-recovery.md)는 무엇을 headless에서 복원할 수 있고 무엇을 수동 확인으로 남겨야 하는지 보여 준다.

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
- reference 통과, starter 거부와 학습자 구현 통과 로그가 모두 있다.
- 같은 workload의 profile 수정 전후와 보존한 gameplay invariant가 evidence bundle에서 연결된다.

### 팀과 변경

- designer/art/QA/server/build/platform 담당자와 공유할 schema가 명확하다.
- 한 번에 전체 시스템을 재작성하지 않고 review 가능한 issue로 나눈다.
- migration, feature flag, compatibility와 rollback이 포함된다.

## 완료 후 실제 프로젝트 이동

1. 선택 엔진의 작은 sample에서 문서의 state를 실제 class/node/system에 매핑한다.
2. content validator, replay fixture, save migration test 또는 작은 gameplay bug를 첫 기여로 고른다.
3. 같은 subsystem에서 반복 기여하며 editor·content·target platform 제약을 배운다.
4. rendering, backend, data, platform, security는 해당 후속 브랜치로 깊이를 확장한다.
