# Multi-tenancy·quota·isolation

Multi-tenancy는 여러 팀의 workload를 한 cluster에 넣는 것만을 뜻하지 않습니다. Identity, API, compute, network, storage, telemetry와 운영 책임에서 무엇을 공유하고 어디서 격리할지 결정하는 문제입니다.

완전한 격리와 완전한 공유 사이에서 workload의 신뢰 수준, 실패 비용, 규제·비용·운영 복잡성을 비교합니다.

Kubernetes quota·multi-tenancy·Pod security의 공식 구현 경계는 [source index의 Kubernetes runtime](../reference/source-index.md#kubernetes)을 확인합니다. Namespace 하나를 tenant isolation의 충분조건으로 간주하지 않습니다.

## 1. Tenant 정의

Tenant는 상황에 따라 다릅니다.

- 개발 팀
- 제품 또는 business unit
- 외부 고객
- environment
- 보안 trust zone
- 비용 center

같은 조직 팀이라도 production과 preview는 다른 isolation profile을 가질 수 있습니다. Tenant ID가 billing label인지 security boundary인지 구분합니다.

## 2. 격리 축

| 축 | 공유 가능 항목 | 격리 판단 |
|---|---|---|
| identity | identity provider | role, service account, credential audience |
| API | platform endpoint | authorization, rate limit, object visibility |
| control plane | cluster/API/controller | blast radius, noisy tenant, upgrade 영향 |
| compute | node/VM | kernel trust, resource contention, hardware 요구 |
| network | VPC/cluster network | east-west trust, egress, public exposure |
| storage | class/backend | encryption key, data residual, performance |
| telemetry | collector/backend | metadata privacy, query access, cardinality |
| delivery | runner/controller | credential, untrusted code, queue fairness |
| cost | shared capacity | attribution, budget, subsidy policy |

Namespace는 유용한 administrative boundary지만 모든 공격과 resource contention을 막는 보안 경계로 단정하지 않습니다.

## 3. Isolation profile

예시:

### Development shared

```text
shared cluster
namespace per team
default-deny network policy
resource quota
no sensitive production data
best-effort support
```

### Production standard

```text
shared production cluster pool
namespace per service or team
restricted admission policy
workload identity
quota and priority class
zonal disruption contract
platform SLO
```

### High isolation

```text
separate account/project
separate cluster or node pool
separate encryption key and telemetry access
narrow control-plane identity
stricter change approval
higher cost and slower provisioning
```

Profile 선택 조건과 비용·지원 수준을 platform API에 드러냅니다.

## 4. Namespace와 resource ownership

Namespace 생성만으로 multi-tenancy가 완성되지 않습니다.

필요한 기본:

- namespace owner metadata
- RBAC와 service account
- resource quota와 limit range
- network policy
- policy profile
- secret 접근
- storage class와 retention
- telemetry visibility
- lifecycle·deletion protection

Namespace-level resource를 application team이 바꿀 수 있는지, platform controller만 관리하는지 field ownership을 정합니다.

## 5. Quota와 limit

Quota는 cluster capacity를 만드는 기능이 아니라 tenant의 최대 사용량과 공정성을 제한하는 정책입니다.

구분:

- resource request/limit
- object count
- storage capacity
- external cloud service quota
- API rate limit
- CI runner concurrency
- environment count와 TTL
- log/trace ingestion
- cost budget

Quota가 너무 낮으면 self-service가 반복 ticket으로 돌아갑니다. 너무 높거나 없으면 한 tenant가 공유 capacity를 소진합니다.

### Quota 요청 경로

```text
현재 사용량과 trend
→ 요청한 추가 capacity
→ 기간과 workload 근거
→ 비용 owner
→ cluster/platform headroom
→ 승인 또는 자동 policy
→ expiry/review
```

임시 증가에는 자동 만료를 둡니다.

## 6. Scheduling과 noisy neighbor

Resource request가 없거나 부정확하면 scheduler와 capacity planning이 현실을 반영하지 못합니다.

검토:

- request와 실제 usage 차이
- CPU throttling과 memory OOM
- priority와 preemption
- topology spread
- dedicated node pool
- GPU/accelerator
- ephemeral storage
- daemon overhead
- system reserved capacity

Limit를 설정했다고 모든 성능 간섭이 사라지는 것은 아닙니다. Disk, network, cache와 shared dependency도 contention을 만듭니다.

## 7. Network isolation

Default-deny 정책에서 필요한 통신을 명시합니다.

- ingress source
- egress destination
- DNS
- platform control services
- telemetry collector
- dependency database/broker
- public internet allowlist 또는 proxy

정책이 존재하는지뿐 아니라 실제 network plugin과 경로에서 강제되는지 선택 실습 또는 운영 evidence로 확인합니다.

Tenant egress를 한 공용 proxy로 모으면 감사와 제어가 쉬워질 수 있지만 proxy 장애와 credential forwarding이 새로운 shared risk가 됩니다.

## 8. Storage와 data boundary

- volume reclaim policy
- snapshot과 backup owner
- encryption key
- tenant 간 volume attach 방지
- deleted volume의 data residual
- shared filesystem 권한
- stateful workload migration
- restore 권한

Namespace 삭제가 persistent data 삭제로 자동 이어지는지 명확히 합니다. Data retention이 필요한 경우 workload와 storage lifecycle을 분리합니다.

## 9. Control plane blast radius

여러 tenant가 같은 controller와 API를 사용하면 한 tenant의 invalid 또는 대량 요청이 control plane을 소진할 수 있습니다.

Guardrail:

- API rate limit
- work queue fairness
- per-tenant concurrency
- reconcile timeout
- object size와 count limit
- admission cost 제한
- controller circuit breaker
- tenant별 dead-letter 또는 blocked state
- system tenant reserved capacity

하나의 broken resource가 controller 전체 loop를 막지 않게 합니다.

## 10. Telemetry isolation

Shared telemetry에서는 tenant metadata와 application data가 섞입니다.

- team별 query authorization
- cross-tenant dashboard 제한
- log payload redaction
- trace baggage 제한
- metric cardinality budget
- audit 별도 retention
- tenant deletion과 data retention

Platform operator가 문제를 진단할 최소 접근과 application data privacy를 함께 설계합니다.

## 11. Cost attribution과 공정성

정확한 비용 배분이 불가능한 shared cost도 있습니다.

구분:

- 직접 비용: node, database, storage, egress
- shared platform overhead: control plane, observability, security service
- idle headroom: reliability를 위한 reserve
- engineering/support cost

Chargeback을 바로 도입하지 않아도 showback으로 usage와 선택의 trade-off를 보여 줄 수 있습니다. 비용 최적화가 reliability headroom을 없애지 않게 합니다.

## 12. Tenant lifecycle

```text
tenant 생성
→ owner와 trust profile
→ quota·policy·namespace/account 생성
→ workload onboarding
→ ownership 변경
→ suspension
→ data export/retention
→ credential·resource 폐기
→ audit 보존
```

Owner 없는 tenant, 만료된 preview environment와 빈 namespace를 자동 탐지합니다. 삭제는 data와 외부 dependency를 확인한 뒤 수행합니다.

## 13. 실습

[`09-multitenancy`](../exercises/09-multitenancy/)에서 다음을 작성합니다.

- tenant 정의와 trust profile
- account/cluster/namespace/node 경계
- RBAC·network·storage·telemetry isolation
- quota와 증가 경로
- noisy neighbor와 control-plane fairness
- cost attribution
- tenant 생성·변경·폐기

## 14. 검토 질문

- Tenant가 팀·고객·환경 중 무엇을 뜻하는지 명확합니까?
- Namespace를 완전한 보안 경계로 과신하지 않습니까?
- 신뢰 수준에 따라 isolation profile을 선택합니까?
- Quota와 실제 cluster capacity를 구분합니까?
- 한 tenant의 대량 요청이 control plane queue를 막지 않습니까?
- Network·storage·telemetry에서 cross-tenant 접근을 검사합니까?
- Temporary quota와 exception이 자동 만료됩니까?
- Tenant 폐기 뒤 data·credential·cost·audit가 처리됩니까?

다음 장에서는 공유 플랫폼을 사용자 여정의 SLO, capacity, cost와 support model로 운영합니다.
