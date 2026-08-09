# Upgrade·migration·deprecation

플랫폼은 서비스를 생성한 날의 도구와 계약을 영원히 유지할 수 없습니다. Cluster, runtime, add-on, base image, reusable workflow, policy와 platform API는 계속 변합니다. 문제는 변경 자체가 아니라 **누가 언제 어떤 상태를 어떤 근거로 다음 version으로 옮기는가**입니다.

이 장은 플랫폼 변경을 호환성, migration wave, rollback과 폐기 계약으로 관리합니다.

## 1. 무엇이 version을 갖는가

플랫폼에는 여러 독립 version이 있습니다.

- platform API
- runtime/profile
- repository template
- reusable CI workflow
- base image와 language runtime
- cluster/Kubernetes version
- network·storage·ingress add-on
- GitOps/IaC controller
- policy bundle
- observability schema와 collector
- catalog metadata schema

`platform version 3` 하나로 묶으면 일부 component만 rollback하거나 compatibility를 판단하기 어렵습니다. 대신 검증된 조합을 release manifest로 제공할 수 있습니다.

```yaml
platformRelease: 2026.08
components:
  api: 2.4.0
  statelessHttpProfile: 3.2.0
  kubernetes: 1.xx
  networkProfile: 5.1.0
  policyBundle: 7.3.2
compatibility:
  serviceProfile: ">=2.8 <4.0"
```

## 2. 변경 종류

### 내부 구현 변경

외부 contract와 실행 결과가 유지됩니다. 내부 refactoring이라도 latency, ordering 또는 failure mode가 바뀌면 관찰이 필요합니다.

### 호환 추가

Optional field, 새 profile 또는 새로운 status reason을 추가합니다. 오래된 client가 unknown field/status를 어떻게 처리하는지 확인합니다.

### Default 변경

새 resource에만 적용할지 기존 resource도 reconcile할지 명확히 합니다. 기존 resource를 바꾸면 migration입니다.

### 의미 변경

같은 입력이 다른 권한·network·storage·availability 결과를 만듭니다. Schema compatibility와 별개로 breaking change입니다.

### 제거

Field, API version, runtime, policy exception 또는 component를 폐기합니다. 대체 경로와 data 처리, deadline이 필요합니다.

## 3. Inventory와 dependency

변경 전에 영향을 받는 대상을 찾습니다.

- profile/version별 service 수
- cluster·region·tenant
- deprecated API/object
- custom override와 escape hatch
- policy exception
- external dependency
- data/storage format
- client와 automation version
- owner와 support tier

Catalog가 정확하지 않으면 migration plan도 정확하지 않습니다. Runtime discovery와 catalog metadata를 비교해 stale owner와 unknown workload를 찾습니다.

## 4. Compatibility contract

검사해야 할 축:

- API request/response
- desired/status conversion
- stored state와 serialization
- resource naming/identity
- network endpoint
- credential audience/format
- artifact/runtime compatibility
- telemetry field·metric name
- policy decision
- data/storage format
- rollback target

### N-1 호환 예

```text
새 control plane이 old client 요청을 받음
새 controller가 old resource version을 읽음
old workload가 새 platform service와 통신
new workload가 migration 중 old dependency와 공존
```

무조건 N-1을 지원할 필요는 없지만 어떤 조합을 얼마 동안 지원하는지 선언합니다.

## 5. Migration 상태 기계

```text
Discovered
→ Eligible
→ Scheduled
→ Prechecked
→ Migrating
→ Observing
→ Completed
```

예외 상태:

```text
Blocked
Failed
RolledBack
ManualReview
WaivedUntil
```

각 resource에 migration ID, source/target version, owner, deadline와 evidence를 연결합니다. Spreadsheet만으로 관리하면 actual state와 쉽게 어긋납니다.

## 6. Wave와 canary

한 번에 전체 fleet을 바꾸지 않습니다.

Wave 선택 기준:

- platform team 소유 test workload
- low-risk development tenant
- 대표적인 standard workload
- stateful 또는 특수 profile
- production canary
- remaining fleet

각 wave에서 다음을 확인합니다.

- API/controller health
- workload availability와 latency
- policy/authorization 변화
- resource usage
- telemetry schema
- rollback 가능성
- 새 support ticket와 unexpected exception

Canary가 실제 fleet 다양성을 대표하지 않으면 false confidence가 생깁니다.

## 7. Preflight

Migration 전에 차단 조건을 빠르게 찾습니다.

- owner 없음
- old API 또는 unsupported field
- capacity/headroom 부족
- PDB 또는 topology 때문에 drain 불가
- data backup/restore 미검증
- custom webhook/controller compatibility 미확인
- exception 만료
- rollback artifact 없음
- maintenance window와 communication 누락

Preflight 결과는 actionable해야 하며 자동 수정 가능한 항목과 사람 판단 항목을 분리합니다.

## 8. Cluster와 runtime upgrade

Kubernetes 또는 runtime substrate upgrade에는 여러 계층이 있습니다.

```text
control plane
→ node pool
→ system add-on
→ policy/admission
→ workload API/runtime compatibility
```

검토:

- supported version skew
- deprecated/removed API
- node drain와 disruption budget
- daemon/system workload
- storage/network plugin
- autoscaler와 scheduler behavior
- admission webhook availability
- image/runtime compatibility
- capacity surge

Upgrade 성공은 version이 바뀐 사실이 아니라 representative workload와 platform journey가 통과한 상태입니다.

## 9. API와 state migration

Stored resource를 새 schema로 옮길 때 다음을 정합니다.

- read old/write new 또는 dual read/write
- conversion webhook/controller
- backfill identity와 progress
- 재시도와 idempotency
- partial success
- data validation
- old field 보존 기간
- rollback 시 old reader가 읽을 수 있는지

모든 resource를 즉시 rewrite하지 않고 읽을 때 변환하거나 background migration할 수 있습니다. 어느 방식이든 완료 판정과 stale object 검사가 필요합니다.

## 10. Rollback boundary

변경 전에 reversible point를 찾습니다.

Rollback이 어려운 예:

- storage format 변환
- credential audience 변경과 old credential 폐기
- API field 제거 후 data 손실
- network address 변경
- provider resource replace
- old binary가 읽지 못하는 state write

Rollback이 불가능하면 forward repair와 restore 경로를 준비합니다. “이전 chart version 적용”만 rollback 계획으로 쓰지 않습니다.

## 11. Deprecation

Deprecation은 공지 한 번이 아니라 lifecycle입니다.

```text
대체 경로 제공
→ 신규 사용 중단
→ inventory와 owner 통지
→ warning/telemetry
→ migration tooling
→ support deadline
→ enforcement
→ old path 제거
→ 잔여 resource·credential·문서 정리
```

공지에는 다음이 필요합니다.

- 무엇이 왜 폐기되는가
- 영향을 받는 대상
- replacement와 차이
- 자동/수동 migration 절차
- deadline와 support
- 예외 조건
- 미이행 결과
- rollback 또는 data export

Team에 책임을 넘기기 전에 platform이 가능한 자동 migration과 evidence를 제공합니다.

## 12. Communication과 change window

변경 risk에 따라 다음을 조정합니다.

- notification audience
- freeze 또는 maintenance window
- canary/wave schedule
- on-call와 incident channel
- status update cadence
- application team action
- abort criteria
- post-change observation

모든 upgrade를 야간에 실행하는 것이 안전한 것은 아닙니다. 전문가가 관찰하고 dependency owner가 대응 가능한 시간대가 더 중요할 수 있습니다.

## 13. Migration metrics

- target version adoption
- blocked/failed/waived 수
- wave별 success/rollback
- preflight defect 종류
- migration duration
- application impact
- support ticket
- overdue owner
- old component/resource 잔여
- migration 뒤 cost/performance 변화

완료율만 보고 실패한 service를 제외하지 않습니다.

## 14. 실습

[`11-migration`](../exercises/11-migration/)에서 다음을 설계합니다.

- 변경 대상과 version 조합
- inventory와 owner
- compatibility matrix
- preflight
- canary와 wave
- abort/rollback/forward repair
- communication과 support
- deprecation deadline
- 완료·잔여 evidence

## 15. 검토 질문

- 독립 component의 version과 검증된 조합을 구분합니까?
- Schema가 같아도 의미가 바뀌는 변경을 찾습니까?
- Inventory가 실제 runtime과 비교됩니까?
- Migration이 resource별 상태와 owner를 가집니까?
- Canary가 fleet의 중요한 변형을 포함합니까?
- Rollback 불가능한 상태 전이를 미리 식별합니까?
- Deprecation에 replacement·tooling·deadline·support가 있습니까?
- 완료 뒤 old credential·resource·문서가 제거됐습니까?

다음 장에서는 source에서 runtime까지 artifact와 주체의 신뢰 근거, 플랫폼 control plane 자체의 공격면을 검토합니다.
