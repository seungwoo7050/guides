# 완료 증거와 계약 추적표

이 문서는 `main`의 여섯 `owns`를 개념 설명, 단계 실습의 정상·경계·실패, Relay Arena 누적 과제와 세 `exit_capabilities`에 연결한다. 자동 검사는 공개 행동과 기계 판정 가능한 불변식을 확인하지만, 이 표만으로 학습자의 설명·설계 판단이나 실제 엔진 경험까지 자동으로 완료 처리하지 않는다.

## `owns`에서 종료 증거까지

| `owns` 계약 | 개념 설명 | 단계 실습과 대표 실패 | Capstone 누적 증거 | 연결되는 종료 능력 |
|---|---|---|---|---|
| 고정·가변 시간 단계와 game loop | [02 게임 루프, 시간과 프레임](../docs/02-game-loop-time-and-frames.md) | [01 시간 단계 분석](../exercises/01-time-step-analysis/README.md)의 long frame, pause, bounded catch-up 계산과 [`frame-analysis.csv`](../exercises/01-time-step-analysis/reference/frame-analysis.csv) | [`time-and-input-contract.md`](../projects/relay-arena-vertical-slice/reference/artifacts/time-and-input-contract.md), smooth/jittered/hitch `simulate`, 최대 네 step과 canonical state hash 검사 | 경계 복원, 작은 기능 구현, 실패 재현·수정 |
| 입력·카메라·장면·엔티티·컴포넌트의 상태 경계 | [03 입력·명령·카메라·UI](../docs/03-input-command-camera-and-ui.md), [04 월드·장면·엔티티 수명](../docs/04-world-scene-entity-component-lifecycles.md) | [02 입력과 명령](../exercises/02-input-command-contract/README.md)의 focus loss·context 우선순위, [03 월드 수명](../exercises/03-world-lifecycle-review/README.md)의 cancel·stale completion·cleanup 누락 | [`runtime-state-map.md`](../projects/relay-arena-vertical-slice/reference/artifacts/runtime-state-map.md), [`state-ownership.csv`](../projects/relay-arena-vertical-slice/reference/artifacts/state-ownership.csv), stale-load와 generation rejection trace | 경계 복원, 작은 기능 구현 |
| 자산 로딩·직렬화·resource lifetime과 editor workflow | [06 자산·loading·memory](../docs/06-assets-import-cooking-loading-and-memory.md), [09 save·replay](../docs/09-save-migration-replay-and-determinism.md), [12 도구·빌드·콘텐츠 검증](../docs/12-tools-editor-builds-and-content-validation.md) | [04 자산 loading](../exercises/04-asset-loading-plan/README.md)의 dependency·budget·fallback, [05 save/replay](../exercises/05-save-and-replay-migration/README.md)의 v1→v2·corrupt input·first divergence | [`world-and-asset-plan.md`](../projects/relay-arena-vertical-slice/reference/artifacts/world-and-asset-plan.md), [`save-and-replay.md`](../projects/relay-arena-vertical-slice/reference/artifacts/save-and-replay.md), stale/optional asset 처리와 원자적 save publish 검사 | 경계 복원, 작은 기능 구현, 실패 재현·수정 |
| 물리·애니메이션·오디오·렌더링 하위 시스템의 게임 계층 통합 | [07 충돌·물리·이동](../docs/07-collision-physics-movement-and-space.md), [08 animation·audio·VFX·표현](../docs/08-animation-audio-vfx-and-presentation.md) | [02 입력과 명령](../exercises/02-input-command-contract/README.md)의 command 경계와 [03 월드 수명](../exercises/03-world-lifecycle-review/README.md)의 presentation subscription cleanup; presentation이 gameplay state를 쓰는 mutant | [`movement-and-space.md`](../projects/relay-arena-vertical-slice/reference/artifacts/movement-and-space.md), [`presentation-contract.md`](../projects/relay-arena-vertical-slice/reference/artifacts/presentation-contract.md), one-shot event dedupe와 [`boundary-recovery.md`](../projects/relay-arena-vertical-slice/reference/boundary-recovery.md) | 경계 복원, 작은 기능 구현, 실패 재현·수정 |
| 게임플레이 기능의 상태 전이·저장·재현·테스트 | [05 게임 규칙과 진행 상태](../docs/05-gameplay-rules-progression-and-data.md), [09 save·replay](../docs/09-save-migration-replay-and-determinism.md), [13 테스트·재현](../docs/13-testing-debugging-telemetry-and-reproduction.md) | [05 save/replay](../exercises/05-save-and-replay-migration/README.md)의 migration과 first wrong checkpoint; 잘못된 divergence mutant 거부 | [`gameplay-rules.md`](../projects/relay-arena-vertical-slice/reference/artifacts/gameplay-rules.md), [`test-and-observability-plan.md`](../projects/relay-arena-vertical-slice/reference/artifacts/test-and-observability-plan.md), command→state→presentation→save/replay public contract | 작은 기능 구현, 실패 재현·수정 |
| frame budget·profiling·client/server authoritative 경계의 게임 맥락 | [11 authority·replication·latency](../docs/11-network-authority-replication-and-latency.md), [14 성능 예산·profiling](../docs/14-performance-budgets-profiling-and-scalability.md) | [06 authority](../exercises/06-authority-and-latency/README.md)의 duplicate·stale·non-owner, [07 성능](../exercises/07-performance-budget-review/README.md)의 percentile·resource·loading, [08 release](../exercises/08-release-readiness/README.md)의 stale/failed gate | [`authority-and-latency.md`](../projects/relay-arena-vertical-slice/reference/artifacts/authority-and-latency.md), [`performance-and-release.md`](../projects/relay-arena-vertical-slice/reference/artifacts/performance-and-release.md), authority mutants와 같은 workload의 modeled counter 전후 비교 | 작은 기능 구현, 실패 재현·수정 |

AI/navigation, 접근성·release와 팀 workflow는 새 소유 범위가 아니다. [10](../docs/10-game-ai-navigation-and-behavior.md), [15](../docs/15-platform-accessibility-lifecycle-and-release.md), [16](../docs/16-game-team-interfaces-and-change-management.md)은 위 상태·수명·도구·검증 계약을 agent, target platform과 협업 변경에 적용하는 보조 단원이다.

## `exit_capabilities`별 판정 근거

### 1. 기존 엔진 프로젝트의 update·render·asset·tool 경계를 복원한다

필수 증거는 [`boundary-recovery.md`](../projects/relay-arena-vertical-slice/reference/boundary-recovery.md)와 같은 경계 지도, runtime/state owner, 실제 symbol·callback·asset id·tool entry를 찾은 조사 기록이다. Headless reference는 조사 질문과 경계 모양을 보여 주지만 실제 엔진 callback, thread/job, GPU와 editor extension을 관찰하지 않는다. 실제 코드베이스 경로·revision과 근거 line/symbol은 사람이 확인한다.

### 2. 입력부터 상태·표현·저장까지 이어지는 작은 게임플레이 기능을 구현한다

기본 경로는 미완성 [`starter/relay_arena.py`](../projects/relay-arena-vertical-slice/starter/relay_arena.py)를 저장소 밖에서 완성하고 같은 [`check_contract.py`](../projects/relay-arena-vertical-slice/tests/check_contract.py)를 통과하는 것이다. `simulate`는 Move/Dash/Interact command, authoritative gameplay state, presentation event와 save/replay evidence를 연결한다. 실제 엔진 대체 경로는 동일 assertion을 engine test·trace에 mapping하고 build/content identity를 제출한다. 사람이 구현 소유권, 변경 범위와 유지보수 가능성을 검토한다.

### 3. frame·resource·simulation 실패를 재현하고 profiling 근거로 수정한다

필수 증거는 hitch와 bounded catch-up, stale/optional resource, replay first divergence, corrupt save 보존, duplicate/non-owner 거부, 동일 workload의 profile 전후와 회귀 결과다. [`check_mutants.py`](../projects/relay-arena-vertical-slice/tests/check_mutants.py)는 unbounded catch-up, non-owner 수락, presentation state write와 실패한 save overwrite가 거부되는지 확인한다. 실제 target의 CPU/GPU frame time, memory residence, load time과 network fault는 사람이 실제 장비·build에서 다시 측정한다.

## 판정 루브릭

다음 네 조건이 모두 있어야 완료 후보로 검토한다.

1. 각 `owns` 행에서 문서만이 아니라 실행·관찰·추론 증거를 가리킨다.
2. 8개 단계 실습의 기계 판정 결과와 `MANUAL_REVIEW_REQUIRED` 질문에 대한 근거가 있다.
3. Relay Arena의 13개 설계 산출물과 실행 evidence bundle이 서로 같은 state id, requirement id, build/content identity를 사용한다.
4. 세 종료 능력 각각에 source revision, 실행 명령, 결과와 알려진 한계가 있다.

자동 검사는 reference 통과, 미완성 template/starter와 알려진 오답 거부, 구조·schema·상대 링크·source 불변성을 확인한다. 설명의 타당성, fixture 밖 일반화, 실제 엔진/기기 결과, 교육적 이해와 팀 review 품질은 사람이 확인한다. 실행 환경과 증거 취급 규칙은 [안전·환경 계약](safety-and-environment.md)을 따른다.
