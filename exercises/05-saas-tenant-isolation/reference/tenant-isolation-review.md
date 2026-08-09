# SaaS Tenant Isolation Review

## Tenant 정의와 lifecycle

workspace를 tenant로 정의하고 membership, role, plan, usage, data, export와 deletion을 같은 tenant ID에 연결한다. lifecycle은 PROVISIONING, ACTIVE, SUSPENDED, CLOSING, RETENTION, DELETED로 나누고 각 상태의 read·write·job·export를 정의한다.

## Authentication과 tenant context

request body의 workspace ID를 직접 신뢰하지 않는다. authenticated user의 active membership에서 tenant context를 만들고 role·entitlement를 별도 평가한다. service-to-service와 background job은 workload identity와 signed/stored tenant context를 사용한다. global support identity는 정상 request path를 우회하지 않는다.

## Database와 object boundary

ID가 globally unique해도 모든 query와 mutation에 tenant filter를 포함한다. composite key와 foreign key에 tenant ID를 넣어 cross-tenant 관계를 막는다. object key의 workspace ID는 authorization evidence가 아니므로 application 또는 object policy가 workload identity와 tenant prefix를 함께 검사한다. pre-signed URL은 tenant, object version, action과 짧은 expiry를 갖는다.

## Cache와 background job

cache key를 `tenant:{tenant_id}:document:{document_id}:v{version}`으로 바꾼다. job payload에는 tenant ID, document ID, operation ID, schema version을 포함하고 처리 시 tenant active와 document ownership을 다시 확인한다. broad worker role 대신 tenant-scoped object path와 필요한 database operation만 허용한다.

## Analytics와 derived data

warehouse·search·log에 tenant field를 강제하고 query layer에서 filter를 자동 적용한다. dashboard filter만으로 격리를 보장하지 않는다. shared export file 접근을 제한하고 tenant별 export artifact를 만든다. tenant deletion은 analytics, search, cache와 model feature의 deletion status를 추적한다.

## Support와 operator access

support access는 case ID, tenant, reason, read/write scope, approver, starts/expires, result와 audit를 가진 time-bound session으로 만든다. sensitive field redaction과 customer-visible access history 필요성을 검토한다. bulk search는 별도 privileged workflow로 제한한다.

## Entitlement와 quota

membership authorization과 plan entitlement를 분리한다. starter/pro limit는 versioned plan에서 평가한다. document 생성 전에 atomic quota reservation을 만들고 success에서 usage로 commit, terminal failure·expiry에서 release한다. UI hide만으로 feature를 막지 않는다.

## Export와 deletion

export는 consistent snapshot, database row, object version, membership·setting·usage 범위, encryption, delivery identity와 expiry를 가진다. cross-tenant canary data가 포함되지 않는 negative test를 수행한다. deletion은 new write 차단, session revoke, queue cancel, primary·object·cache·search·analytics cleanup, backup retention과 final evidence로 구성한다.

## Negative tests와 evidence

- tenant A token+tenant B workspace ID 거부
- tenant A가 B document ID를 요청해도 거부
- cache warm 뒤 다른 tenant request에 data leak 없음
- job tenant/document mismatch 거부
- export에 canary tenant row 없음
- support session expiry 뒤 접근 거부와 audit 존재
- quota 경쟁 request에서 limit 초과 없음
- deletion 뒤 active object·queue·index 없음

## Decision

현재 상태는 `REJECT`다. request body tenant 신뢰, missing DB filter, shared cache key, tenant 없는 job, unrestricted support, dashboard-only analytics isolation과 incomplete deletion이 중대한 leak path다. 위 invariant와 negative test가 구현된 뒤 제한된 tenant로 재검토한다.
