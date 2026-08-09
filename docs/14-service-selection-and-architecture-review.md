# 서비스 선택과 architecture review

서비스 선택은 “어떤 제품이 더 최신인가”가 아니라 workload의 상태·실패·운영·비용과 team capability를 비교하는 일입니다.

같은 workload를 IaaS, managed platform, FaaS에 둘 수 있지만 책임과 failure surface가 달라집니다.

## 1. Workload brief

선택 전에 다음을 작성합니다.

```text
users and tenants
request/event pattern
state and data classification
latency and throughput
availability target
RTO/RPO
consistency and ordering
runtime and dependency
change frequency
security boundary
expected growth
budget and cost owner
team capability
exit requirement
```

제품을 먼저 정하고 요구를 끼워 맞추지 않습니다.

## 2. IaaS 적합성

IaaS가 유리할 수 있는 경우:

- OS·runtime·network에 높은 제어가 필요함
- custom binary·agent·driver
- predictable steady workload
- existing application lift-and-shift
- managed service limit가 맞지 않음
- specialized security·compliance control

비용:

- patch와 image lifecycle
- host capacity
- scaling과 failover
- monitoring과 backup
- configuration drift

## 3. Managed runtime/PaaS 적합성

유리할 수 있는 경우:

- standard web/API runtime
- 빠른 delivery
- host 운영을 줄이고 싶음
- autoscaling과 deployment 기능 활용
- standard managed data·queue integration

검토:

- runtime·version constraint
- extension와 network
- maintenance
- scale unit
- portability
- observability
- minimum cost

## 4. FaaS 적합성

유리할 수 있는 경우:

- event-driven
- bursty or intermittent
- short bounded work
- independent unit
- scale-to-zero 가치
- fine-grained cost attribution

검토:

- timeout
- duplicate·ordering
- downstream capacity
- cold start
- package size
- local state
- concurrency
- high steady-state cost

## 5. SaaS 구매 대 직접 구현

외부 SaaS를 구매할지 직접 만들지 결정할 때:

- capability가 differentiator인지
- data sensitivity
- integration
- customization
- identity·audit
- export·deletion
- vendor continuity
- total cost
- internal operation capability

직접 구현은 license fee를 피하는 대신 product lifecycle, support, tenant isolation와 incident responsibility를 만듭니다.

## 6. Managed database 선택

질문:

- relational, key-value, object, document 중 data invariant에 맞습니까?
- transaction과 consistency가 충분합니까?
- partition key와 access pattern이 정해졌습니까?
- backup·restore와 tenant unit을 지원합니까?
- connection·throughput·item limit가 맞습니까?
- migration과 export가 가능합니까?
- cost curve가 workload에 맞습니까?

기술 유행보다 data contract를 우선합니다.

## 7. 비교 matrix

| 기준 | IaaS | Managed platform | FaaS |
|---|---|---|---|
| OS 제어 | 높음 | 제한 | 없음 또는 매우 제한 |
| scale unit | instance | service instance/capacity | invocation/concurrency |
| idle cost | 보통 존재 | 서비스별 | scale-to-zero 가능 |
| startup | instance boot | platform deploy | cold start 가능 |
| local state | instance 수명 | 제한·ephemeral 가능 | ephemeral |
| event semantics | 직접 구현 | 서비스별 | trigger contract 중요 |
| patch 책임 | 소비자 큼 | 공급자 이동 | runtime 공급자, code 소비자 |
| portability | image·network dependency | platform API dependency | trigger·runtime semantics dependency |
| 관측 | 직접 구성 많음 | 제공 metric+application | invocation+end-to-end correlation |

표는 일반화일 뿐입니다. 실제 서비스 문서를 확인합니다.

## 8. Architecture review 순서

### Step 1. Scope

- workload와 tenant
- production/non-production
- region
- data class
- external dependency

### Step 2. State

- durable authoritative
- derived
- ephemeral
- evidence
- commercial state

### Step 3. Ownership

- business
- configuration
- runtime
- data
- cost

### Step 4. Control

- human·workload·automation identity
- network
- control/data plane
- approval

### Step 5. Failure

- instance·zone·region
- provider control plane
- dependency
- quota
- duplicate·timeout
- tenant isolation
- cost anomaly

### Step 6. Evidence

- test
- metric
- trace
- audit
- restore
- inventory
- cost

### Step 7. Exit

- export
- replacement
- cutover
- delete
- contract

## 9. “Best practice”를 계약으로 바꾼다

예:

### Best practice: least privilege

변환:

```text
function identity는 source object read와 result object create만 허용합니다.
다른 tenant prefix와 control plane action은 거부됩니다.
credential은 runtime이 발급하고 1시간 이내 만료됩니다.
allow·deny event를 audit에서 확인합니다.
```

### Best practice: multi-AZ

변환:

```text
application target은 zone A/B에 분산됩니다.
zone A 제거 뒤 5분 안에 error rate가 SLO 안으로 돌아옵니다.
B의 reserved capacity가 peak의 100%를 처리합니다.
database failover RTO와 client reconnect를 실험합니다.
```

### Best practice: backup

변환:

```text
매일 생성된 backup을 30일 보존합니다.
월 1회 empty environment에 restore합니다.
checksum과 5개 business invariant를 검사합니다.
RPO/RTO를 report에 기록합니다.
```

## 10. Decision record

서비스 선택마다 남깁니다.

```text
context
options
selected option
reason
assumptions
evidence
cost model
known limits
security and tenant impact
exit cost
review date
reversal trigger
```

decision은 영구 진리가 아닙니다. workload와 공급자 service가 바뀌면 재검토합니다.

## 11. Rejection 조건

다음 중 하나가 없으면 production 선택을 보류할 수 있습니다.

- data owner
- identity boundary
- backup restore evidence
- cost owner와 budget
- limit·quota 확인
- provider outage 대응
- tenant negative test
- resource cleanup
- version lifecycle
- exit plan

## 12. Review 결과

```text
APPROVE
근거가 충분하고 잔여 위험을 수용합니다.

APPROVE_WITH_CONDITIONS
제한된 traffic·tenant·기간 아래 허용합니다.

DEFER
필수 evidence가 없습니다.

REJECT
요구와 service contract가 맞지 않습니다.
```

결정에는 owner, due date와 재검토 trigger가 필요합니다.

## 연결 실습

01~06의 산출물을 사용해 Capstone의 네 architecture stage를 비교하고 release decision을 작성합니다.
