# SaaS tenancy와 isolation

SaaS는 완성된 software를 service로 제공하는 모델입니다. SaaS 제품을 만드는 개발자에게 가장 중요한 새 상태는 `tenant`입니다.

```text
user
개별 사람 또는 machine identity

tenant
데이터·설정·권한·사용량·계약을 공유하는 고객 경계
```

B2B 제품에서는 한 회사나 workspace가 tenant일 수 있고, B2C에서는 가정·팀·계정 묶음이 tenant일 수 있습니다. tenant를 database schema와 동일시하면 안 됩니다. business·identity·data·runtime·billing 경계를 함께 봅니다.

## 1. Tenant 정의

다음 질문에 답합니다.

- 누가 tenant를 생성합니까?
- 한 사용자가 여러 tenant에 속할 수 있습니까?
- tenant 간 data sharing이 있습니까?
- tenant administrator는 무엇을 할 수 있습니까?
- support operator는 tenant data에 접근할 수 있습니까?
- tenant는 plan·region·key·backup을 독립적으로 가집니까?
- tenant를 suspend·merge·split·delete할 수 있습니까?

정의가 불명확하면 authorization, metering와 deletion이 모두 흔들립니다.

## 2. Tenant lifecycle

```text
REQUESTED
→ PROVISIONING
→ ACTIVE
→ SUSPENDED
→ CLOSING
→ RETENTION
→ DELETED
```

추가 상태가 필요할 수 있습니다.

- trial
- payment delinquent
- migration
- legal hold
- export pending
- deletion failed

각 상태에서 허용되는 action과 background job을 정합니다. 예를 들어 `SUSPENDED` tenant의 read/export는 허용하고 write는 금지할 수 있습니다.

## 3. Isolation은 연속선이다

모든 resource를 공유하거나 모든 tenant를 완전히 분리하는 두 선택만 있는 것이 아닙니다.

### Shared everything

- 같은 application instance
- 같은 database table
- row에 tenant ID

장점: 비용과 운영 효율
위험: application bug의 blast radius, noisy neighbor

### Shared service, isolated data unit

- 같은 application
- tenant별 schema 또는 database

장점: data boundary 강화, restore 단위 분리
비용: connection·migration·fleet 운영

### Dedicated deployment

- tenant별 application·database·network 또는 account

장점: 강한 isolation과 custom requirement
비용: provisioning, upgrade, capacity와 cost 증가

component별로 다른 지점을 선택할 수 있습니다. 중요한 것은 요구 isolation과 evidence입니다.

## 4. Tenant context

모든 request와 background work는 tenant context를 가져야 합니다.

```text
authenticated_subject
tenant_id
membership_or_service_relationship
role_or_entitlement
request_id
reason
```

tenant ID를 client가 보낸 값 그대로 신뢰하지 않습니다. authenticated membership 또는 trusted routing context와 연결합니다.

## 5. Data access

### Row-level shared table

모든 primary·foreign key와 query가 tenant boundary를 보존해야 합니다.

```text
PRIMARY KEY (tenant_id, document_id)
FOREIGN KEY (tenant_id, project_id)
WHERE tenant_id = current_tenant
```

global ID가 unique해도 tenant filter는 필요합니다. ID 추측 가능성과 무관하게 authorization boundary입니다.

### Schema 또는 database per tenant

connection 선택이 tenant context에 따라 안전하게 이루어져야 합니다.

- connection pool contamination
- migration version drift
- backup·restore mapping
- credential scope
- tenant deletion

### Object storage

object key, bucket/container policy와 pre-signed URL에 tenant를 포함합니다. path prefix만으로 authorization이 자동 완성되는 것은 아닙니다.

## 6. Cache

cache key에 tenant가 빠지면 database query가 안전해도 data leak이 발생합니다.

```text
bad: document:{document_id}
good: tenant:{tenant_id}:document:{document_id}:v{version}
```

공유 cache의 eviction과 memory quota도 noisy neighbor를 만들 수 있습니다.

## 7. Queue와 background job

job payload에는 tenant ID뿐 아니라 처리에 필요한 stable authorization context가 필요합니다.

문제:

- 사용자가 membership을 잃은 뒤 delayed job 실행
- tenant 삭제 뒤 event 재시도
- generic worker가 broad cloud role 사용
- batch가 여러 tenant record를 섞음
- dead-letter replay가 현재 tenant 상태를 무시

worker는 현재 tenant 상태와 operation entitlement를 다시 확인하고, workload identity는 필요한 resource scope만 가져야 합니다.

## 8. Search, analytics와 model

검색 index, data warehouse, log와 ML feature도 tenant boundary를 가집니다.

- index document에 tenant field
- query filter 강제
- export partition
- training dataset consent
- aggregate에서 small cohort leak
- deletion propagation
- retention 차이

운영 DB에서 row를 지웠다고 derived system에서 자동 삭제됐다고 가정하지 않습니다.

## 9. Support와 operator access

지원 기능은 강력한 cross-tenant 경로입니다.

필요한 통제:

- case 또는 reason
- tenant approval 또는 policy
- least privilege
- time-bound session
- read/write 분리
- sensitive field redaction
- immutable audit
- customer-visible access history가 필요한지 검토

“internal user”라는 이유로 tenant authorization을 우회하지 않습니다.

## 10. Export

tenant export는 portability와 권리 행사에 필요합니다.

- data scope
- snapshot consistency
- format과 schema version
- attachments와 object
- audit·usage 포함 여부
- encryption
- delivery identity
- expiration
- cross-tenant negative test

대용량 export는 async job이므로 중복, partial output와 retry를 설계합니다.

## 11. Deletion

삭제는 row 한 번 지우는 작업이 아닙니다.

```text
new writes 차단
→ final export 또는 legal hold 판정
→ active session·token revoke
→ primary data delete
→ object·cache·index·queue 정리
→ backup retention 정책 적용
→ billing·audit의 법적 보존 구분
→ completion evidence
```

삭제 실패는 재시도 가능해야 하며, 각 subsystem의 완료 상태를 기록합니다.

## 12. Noisy neighbor

공유 resource에서 한 tenant가 다른 tenant에 영향을 줄 수 있습니다.

- CPU·memory
- database connection
- query
- queue backlog
- storage I/O
- cache
- external API quota
- log volume

대응:

- tenant quota
- rate limit
- workload classification
- fair queue
- dedicated tier
- resource isolation
- per-tenant metric

## 13. Isolation evidence

- cross-tenant request test
- background job tenant mismatch test
- cache key test
- export content review
- support access audit
- backup restore to single tenant 또는 limitation 기록
- load test의 per-tenant fairness
- deletion inventory

## 14. 위협과 오류를 구분한다

cross-tenant leak은 공격자가 ID를 추측해서만 발생하지 않습니다.

- missing filter
- stale context
- reused connection
- misconfigured policy
- support tool bug
- batch join 오류
- analytics export
- cache collision
- restore mapping mistake

따라서 isolation은 secure coding 한 장이 아니라 architecture 전체의 불변식입니다.

## 연결 실습

[05 SaaS tenant isolation](../exercises/05-saas-tenant-isolation/README.md)에서 request, cache, queue, export와 deletion path를 검토합니다. [07 local cloud model](../exercises/07-local-cloud-model/README.md)에서 cross-tenant read와 cleanup 실패를 실제 테스트로 거부합니다.
