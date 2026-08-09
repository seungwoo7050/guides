# 게임 팀 경계와 안전한 변경

## 문제

게임 기능 하나는 여러 직군이 동시에 변경합니다.

```text
게임 디자인 규칙과 tuning
client/gameplay code
engine/runtime
level·art·animation·audio content
UI·localization·accessibility
server·database·live operations
QA·automation·build·release
```

이 경계가 암묵적이면 code review가 통과해도 asset, save, network와 player experience가 깨집니다. 반대로 모든 변경을 한 팀이 승인하면 전달 속도가 느려집니다. 필요한 것은 조직도 암기가 아니라 **각 산출물의 owner, public contract, compatibility와 검증 근거**입니다.

## 핵심 상태

### feature contract

한 기능의 최소 계약:

- player problem과 observable outcome
- authoritative rule와 state owner
- authored data/schema owner
- runtime lifecycle와 dependencies
- presentation consumers
- save/replay/network 영향
- telemetry와 privacy
- target performance/accessibility budget
- build/release requirement
- out-of-scope와 rollback

### 변경 종류

| 종류 | 예 | 추가 검토 |
|---|---|---|
| code-only internal | private algorithm | unit/profile |
| public gameplay rule | damage/cooldown | replay/network/save/tuning |
| content schema | item/level data | migration/validator/tool |
| asset dependency | texture/prefab reference | build/load/memory |
| protocol | command/snapshot | compatibility/fault/security |
| save schema | profile/world state | migration/corruption/rollback |
| platform behavior | input/suspend/storage | target-device checks |
| telemetry | event/field | schema/privacy/cardinality |

### ownership과 contribution

owner는 모든 코드를 직접 쓰는 사람이 아닙니다. 다음을 책임집니다.

- invariant와 public contract
- change review 기준
- compatibility와 deprecation
- failure/incident triage
- documentation과 examples
- 다른 팀이 self-service로 사용할 경로

## 설계 계약

### vertical slice를 작은 merge 단위로 나눕니다

예:

```text
1. data schema + validator
2. pure gameplay rule + tests
3. runtime integration behind flag
4. presentation consumer + fallback
5. save/network migration
6. telemetry + profile scene
7. content rollout
8. release flag enable
```

각 단계가 main branch에서 build/test 가능하고 필요하면 비활성 상태로 존재하게 합니다.

### public data 변경에 version과 migration을 둡니다

- field 추가/삭제/rename
- default semantics
- old content/runtime combination
- save/replay/network impact
- validator와 deprecation warning
- migration tool의 dry-run과 rollback

### binary asset collaboration을 계획합니다

- ownership/lock이 필요한 파일
- scene/prefab composition boundary
- one-file-per-entity/feature 가능성
- generated preview와 dependency report
- merge 전에 content validation
- large file storage와 fetch policy

### feature flag와 content gate를 구분합니다

code flag, server config, content availability와 platform entitlement는 서로 다른 gate입니다. enable 순서와 rollback을 작성합니다.

### review package를 만듭니다

PR description에 다음을 포함합니다.

```text
문제와 player-visible 결과
변경한 owner/contract
정상·경계·실패 사례
asset/schema/save/network 영향
target-device profile
접근성/localization 영향
migration/rollback
남은 위험
```

video는 유용하지만 state/test/profile 근거를 대신하지 않습니다.

### tuning과 code correctness를 분리합니다

designer가 data를 빠르게 바꿀 수 있어도 safe range, invariant와 automated scenario를 둡니다. code review 없이 바뀌는 값일수록 validator와 runtime guard가 중요합니다.

## 대표 실패

### giant feature branch에서 code와 content를 한 번에 통합합니다

오류의 원인과 rollback 단위를 찾기 어렵습니다. schema/rule/integration/content enable을 분리합니다.

### ownership 문서가 조직도만 나열합니다

실제 state, file, event와 release gate가 누구 책임인지 알 수 없습니다. artifact와 contract 기준으로 작성합니다.

### content 변경은 “코드가 아니므로 안전”하다고 봅니다

rule, memory, save와 network를 바꿀 수 있습니다. code와 동등한 validation과 rollout이 필요할 수 있습니다.

### gameplay programmer가 서버/DB에 결과를 직접 씁니다

match state와 durable state의 transaction 경계가 무너집니다. intent/result contract를 통해 backend owner와 연결합니다.

### engine upgrade와 feature change를 함께 합니다

regression 원인이 섞입니다. infrastructure migration, content resave와 gameplay change를 가능한 한 분리합니다.

### QA에 모호한 “확인 부탁”을 넘깁니다

expected state, build/content, test data와 observable failure가 없어 탐색 비용이 큽니다.

## 관찰과 검증

### dependency review

- 이 변경이 어느 owner의 state를 읽고 씁니까?
- 새로운 hard reference와 load group이 생겼습니까?
- save/replay/protocol/schema version이 바뀝니까?
- feature를 disabled/rollback했을 때 생성된 state가 남습니까?
- target device와 representative scene은 무엇입니까?
- automated test와 human playtest의 역할은 무엇입니까?

### integration order test

- old code + old content
- new code + old content
- new code + new content
- rollback code + state written by new version

허용되지 않는 조합은 build, join 또는 load 단계에서 actionable하게 거부합니다.

### 완료 정의

“코드 merged”가 아니라 다음이 연결됐을 때 feature complete로 봅니다.

```text
rule and content
+ runtime lifecycle
+ presentation and fallback
+ save/network compatibility
+ tests and telemetry
+ performance/accessibility
+ release and rollback
```

## 실습 연결

Capstone은 역할별 산출물을 하나의 traceability matrix로 연결합니다. `change-plan.md`에서 구현·content·test·release를 작은 통합 단위로 나눕니다.

## 기존 브랜치와 경계

- Git branch, commit, merge와 conflict 자체는 `git`이 소유합니다.
- CI/CD platform은 `web-infra`·`platform-engineering`이 소유합니다.
- 현재 문서는 game code, authored content, save/network, target-device와 여러 직군의 변경 계약을 소유합니다.

## 완료 기준

- feature의 state·data·runtime·presentation·save/network·release owner를 지정합니다.
- schema/rule/content 변경을 compatibility와 validator가 있는 작은 merge 단위로 나눕니다.
- binary asset, feature flag와 rollout/rollback의 협업 경계를 설계합니다.
- code merged를 넘어 target-device evidence까지 포함한 완료 정의를 작성합니다.
