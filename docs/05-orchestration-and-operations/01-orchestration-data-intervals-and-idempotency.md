# Orchestration, data interval과 idempotency

## 학습 목표

- orchestrator의 DAG/task 상태와 data correctness를 구분한다.
- schedule time, logical data interval, run attempt와 publish identity를 분리한다.
- retry·catchup·manual run이 같은 pipeline contract를 사용하도록 설계한다.
- dependency를 task 완료가 아니라 data availability와 contract로 표현한다.

## 핵심 모델

orchestration은 transform 코드를 대신하지 않는다. **어떤 data interval을 어떤 parameter와 dependency로 언제 실행하고, 실패·재시도·취소를 어떤 상태로 기록할지** 관리한다.

```text
workflow definition
→ logical run for data interval
→ task instances와 attempts
→ artifacts/state changes
→ dataset publish
```

task instance가 `success`여도 output이 누락되거나 잘못될 수 있다. 반대로 task가 timeout됐어도 외부 write는 이미 성공했을 수 있다.

## 네 identity와 run ledger

재시도와 publish를 안전하게 판단하려면 네 identity를 분리한다.

| identity | 의미 | 예 |
|---|---|---|
| job | 반복 가능한 논리 작업 | `daily_sales` |
| run | 한 logical interval을 특정 input·version으로 처리하려는 의도 | `run=R42, interval=2026-08-09` |
| task attempt | run 내부 task의 실제 실행·재시도 | `aggregate/attempt=3` |
| output version | consumer가 읽는 immutable dataset commit | `sales_daily/snapshot=V7` |

Retry는 새 attempt일 수 있지만 같은 run/input을 유지한다. Failed run은 output이 없을 수 있고, 한 run이 validation에서 끝나 여러 output을 publish하지 않을 수 있으며, corrective rerun은 새 output version을 만들 수 있다. 이 관계를 1:1로 가정하지 않는다.

Run ledger는 최소한 다음 전이를 기록한다.

```text
PLANNED → RUNNING → VALIDATING → PUBLISHED
              └──→ FAILED
                         VALIDATING → QUARANTINED
                         PUBLISHED  → SUPERSEDED
```

각 transition에는 expected prior state, actor, time, input/output identity와 reason을 남긴다. 같은 interval의 active run 중복, `PUBLISHED → RUNNING` 같은 역전과 이미 superseded된 output의 재승인을 거부한다. Scheduler의 단일 `SUCCESS`로 validation과 consumer-visible publish를 합치지 않는다.

## logical date와 data interval

예를 들어 daily pipeline이 2026-08-10 01:00에 실행돼 2026-08-09의 데이터를 처리한다.

```text
schedule trigger: 2026-08-10T01:00Z
logical interval: [2026-08-09T00:00Z, 2026-08-10T00:00Z)
run attempt: 2
publish ID: sales_daily/2026-08-09/v4
```

코드는 orchestrator가 전달한 interval을 사용해야 한다. 현재 wall clock에서 하루를 빼면 manual run과 retry가 다른 데이터를 처리할 수 있다.

## DAG와 data dependency

`task_a >> task_b`는 실행 순서만 표현한다. `task_a`가 어떤 partition을 publish하고 `task_b`가 무엇을 읽는지는 별도 contract다.

더 강한 dependency:

- upstream dataset ID와 partition/interval
- required snapshot/version
- freshness와 quality state
- producer schema version
- completion marker/manifest

가능하면 downstream은 임의의 “latest”가 아니라 명시된 upstream snapshot을 읽는다.

## task 설계

좋은 task는 다음 경계가 명확하다.

- input contract
- output contract
- idempotency/retry identity
- timeout과 cancellation
- resource requirement
- emitted metrics와 lineage
- cleanup과 partial state

하나의 task가 너무 많은 외부 상태를 바꾸면 retry와 root cause가 복잡해진다. 반대로 file 하나마다 task를 만들면 scheduler overhead와 관리 복잡성이 커진다.

## 재현 가능한 version set

Run identity에는 Git SHA 하나보다 넓은 실행 판본을 고정한다.

```text
code/artifact revision
runtime와 dependency lock
config와 feature flags
input snapshot/source positions
schema와 semantic contract version
reference/dimension snapshot
state serializer/checkpoint version
output schema와 publish target
```

동일 artifact를 environment 사이에 promote하고 environment별로 다시 build하지 않는다. Secret과 environment endpoint는 artifact 밖의 runtime binding으로 주입하되 실제 사용한 config identity를 민감 값 없이 기록한다. 중단된 run을 “현재 최신 code”로 재개해 한 output에 서로 다른 transform version을 섞지 않는다.

## idempotent task

### parameterized by interval

```text
build_sales(date=2026-08-09, input_snapshot=X, code_version=Y)
```

### deterministic staging path

run/attempt별 staging을 분리하되 publish key는 logical interval과 version으로 결정한다.

### check-before-act의 한계

“file이 있으면 skip”은 partial/old output을 정상으로 오인할 수 있다. manifest status, checksum, schema와 validation을 확인한다.

### replace 또는 compare-and-swap

- same interval output을 atomic replace
- expected base snapshot을 확인해 commit
- 이미 같은 content/run이 publish됐다면 성공으로 종료

## retry

retry는 transient failure에 사용한다.

적합:

- 일시적 network failure
- rate limit과 backoff
- worker loss
- temporary catalog unavailability

부적합:

- schema incompatibility
- deterministic data validation failure
- permission/policy denial
- source interval missing
- code bug

모든 실패를 retry하면 incident detection을 늦추고 source/sink 부하를 키운다. error를 retryable/non-retryable/unknown으로 분류한다.

## timeout과 cancellation

orchestrator timeout은 외부 작업을 자동 취소하지 않을 수 있다.

확인:

- subprocess/job ID를 추적하는가?
- timeout 뒤 remote compute가 계속 write하는가?
- cancellation이 graceful checkpoint를 남기는가?
- retry가 이전 attempt와 충돌하는가?
- cleanup이 live attempt의 staging을 지우지 않는가?

kill signal과 consumer-visible publish를 분리한다.

## catchup과 backfill

orchestrator의 catchup은 과거 schedule instance를 생성하는 기능일 뿐 안전한 backfill을 자동 보장하지 않는다.

필요 조건:

- interval parameterization
- historical input availability
- dimension/reference version
- output overwrite/upsert policy
- rate limit와 priority
- downstream correction propagation
- reconciliation와 approval

큰 backfill을 live schedule과 같은 queue에 넣으면 SLA를 깨뜨릴 수 있다.

## dynamic workflow

source/table/tenant별 task를 동적으로 만들 때 topology가 지나치게 변하면 관측과 history가 어려워진다.

선택:

- stable task + partition parameter
- manifest-driven mapped tasks
- child workflow
- batch grouping

task ID가 매 run마다 무작위로 바뀌지 않게 한다. lineage와 failure comparison이 어려워진다.

## XCom/metadata store misuse

orchestrator metadata는 작은 control metadata에 사용한다.

- snapshot ID
- manifest URI
- count/quality summary
- job ID

대규모 dataset payload를 task metadata에 넣지 않는다. durable storage와 explicit artifact를 사용한다.

## scheduling과 concurrency

- same interval max active runs
- overlapping interval 허용 여부
- source rate limit
- sink writer concurrency
- partition conflict
- pool/priority
- backfill와 live 분리

mutex 하나로 모든 pipeline을 직렬화하기보다 실제 충돌 단위를 interval/table/partition으로 모델링한다.

## failure state

orchestrator 상태와 data 상태를 분리한다.

```text
task state: FAILED
external compute: UNKNOWN/RUNNING/SUCCEEDED
dataset state: NOT_PUBLISHED/STAGED/PUBLISHED/INVALID
quality state: UNKNOWN/PASSED/FAILED
```

incident 대응은 네 상태를 조사해야 한다.

## 실패 모드

### now-based interval

retry가 다른 날짜를 처리한다. explicit logical interval을 사용한다.

### file existence as success

빈/partial/old file을 정상으로 오인한다. manifest와 content validation이 필요하다.

### timeout starts duplicate job

원격 job이 계속 실행 중인데 retry가 새 job을 시작한다. external job ID와 idempotency token을 사용한다.

### upstream task success, data not ready

async publish나 quality check가 끝나기 전에 downstream이 시작한다. dataset availability marker와 snapshot dependency를 사용한다.

### catchup overload

수백 interval이 동시에 source와 warehouse를 압박한다. backfill plan, pool과 rate limit를 둔다.

### retry non-retryable error

schema mismatch를 계속 재시도해 alert가 늦어진다. error classification과 retry budget을 둔다.

## 검증 질문

1. schedule time과 logical data interval을 분리했는가?
2. task attempt와 logical output identity는 무엇인가?
3. task success가 아니라 어떤 manifest/quality state가 downstream을 열어 주는가?
4. timeout 뒤 외부 job 상태를 확인하고 이전 attempt를 정리하는가?
5. retryable과 deterministic failure를 구분하는가?
6. backfill이 live schedule의 capacity와 publish를 침범하지 않는가?

## 연결 연습

[`backfill plan`](../../exercises/05-orchestration-and-operations/01-backfill-plan/README.md)에서 interval, dependency, publish와 rollback 계획을 작성한다.

## 완료 기준

- orchestration state와 data product state를 구분한다.
- 모든 run을 explicit interval·input snapshot·publish identity로 표현한다.
- retry·timeout·catchup이 외부 effect를 중복시키지 않도록 설계한다.
- downstream dependency를 dataset snapshot과 quality contract로 고정한다.
- job·run·task attempt·output version과 run-state transition을 ledger로 분리한다.
- code·runtime·config·schema·input·reference·state 판본을 재현 가능한 실행 집합으로 기록한다.

## 공식 자료 연결

Apache Airflow의 DAG, task instance와 data interval 개념은 대표적 구현 예시다. 제품별 세부 API보다 위 계약을 우선하며 최신 링크는 [`reference/official-sources.md`](../../reference/official-sources.md)에 둔다.
