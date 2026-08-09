# resource and state inventory

## Scope

이 문서는 cloud resource와 application state를 같은 목록에 섞지 않고, 각 항목의 owner·region/zone·data class·dependency·expiry·cleanup 증거를 추적한다. provider console 목록만으로는 tenant·quota·operation과 같은 논리 상태를 설명할 수 없으므로 둘을 연결한다.

고정 입력은 2 uploads/s, peak 50 uploads/s, 평균 8 MB·최대 100 MB, 평균 4초·p99 40초다. 평균 concurrency `TODO`, 보수적 peak concurrency `TODO`, 평균 object peak ingress `TODO`, 최대 object stress bound `TODO`를 계산하고 어떤 resource limit을 검증해야 하는지 적는다. provider, 실제 region/AZ, quota, 단가와 측정 throughput은 아직 `unmeasured/unknown`이다.

상태 분류를 다음처럼 사용한다.

| Class | 판정 질문 | 예시 또는 TODO |
| --- | --- | --- |
| authoritative | 잃으면 사용자·업무 사실을 잃는가? | TODO |
| derived | 정본에서 결정적으로 다시 만들 수 있는가? | TODO |
| ephemeral | lease·cache·runtime처럼 만료 가능한가? | TODO |
| evidence | audit·restore·cost 판단을 위해 보존하는가? | TODO |
| commercial | plan·entitlement·quota·usage처럼 고객 계약을 나타내는가? | TODO |

## Stage 1 — IaaS

| Resource ID / 종류 | Owner | Region / zone | State class | Data / dependency | Backup·expiry | Cleanup evidence |
| --- | --- | --- | --- | --- | --- | --- |
| load balancer | TODO | TODO | TODO | TODO | TODO | TODO |
| VM pool / image | TODO | TODO | TODO | TODO | TODO | TODO |
| public/private network | TODO | TODO | TODO | TODO | TODO | TODO |
| database / snapshot | TODO | TODO | TODO | TODO | TODO | TODO |
| upload/result object storage | TODO | TODO | TODO | TODO | TODO | TODO |
| workload identity / secret | TODO | TODO | TODO | TODO | TODO | TODO |
| log·metric·audit sink | TODO | TODO | TODO | TODO | TODO | TODO |

VM local file에 authoritative data를 두지 않는 이유와 zone 하나를 잃은 뒤 필요한 최소 resource를 TODO로 적는다. upload create 중단, metadata commit 실패, result write 성공 뒤 status 실패 때 남는 partial state와 orphan scan 조건도 정의한다.

| Operation | 시작 상태 | 중간 상태 / lease | 성공 상태 | 실패·timeout 상태 | Reconciler / cleanup |
| --- | --- | --- | --- | --- | --- |
| upload | TODO | TODO | TODO | TODO | TODO |
| process | TODO | TODO | TODO | TODO | TODO |
| result publish | TODO | TODO | TODO | TODO | TODO |

## Stage 2 — Managed platform

VM·self-managed database·queue를 managed runtime·database·queue로 바꿀 때 삭제되는 inventory 행과 새로 생기는 logical/provider resource를 명시한다.

| 이동 전 | 이동 후 managed resource | 여전히 추적할 consumer state | Hidden/contract dependency | Export·cleanup evidence |
| --- | --- | --- | --- | --- |
| VM runtime | TODO | TODO | TODO | TODO |
| self-managed database | TODO | TODO | TODO | TODO |
| worker queue | TODO | TODO | TODO | TODO |
| backup job | TODO | TODO | TODO | TODO |
| network·identity attachment | TODO | TODO | TODO | TODO |

replica, maintenance, failover, backup retention, connection·throughput quota처럼 console에서 완전히 보이지 않을 수 있는 항목을 TODO로 추가한다. provider 내부 node는 직접 소유 inventory가 아니라 contract dependency로 구분한다.

## Stage 3 — FaaS

| Resource / state | Owner | Class | Stable identity | Limit / expiry | Cleanup·replay evidence |
| --- | --- | --- | --- | --- | --- |
| function version·artifact | TODO | TODO | TODO | TODO | TODO |
| event source / trigger mapping | TODO | TODO | TODO | TODO | TODO |
| per-tenant concurrency state | TODO | TODO | TODO | TODO | TODO |
| operation / idempotency record | TODO | TODO | TODO | TODO | TODO |
| deterministic result object | TODO | TODO | TODO | TODO | TODO |
| DLQ / replay record | TODO | TODO | TODO | TODO | TODO |

execution environment나 warm instance를 authoritative resource로 오해하지 않는다. event delivery 뒤 timeout, result는 존재하지만 status가 processing인 상태, DLQ replay 중 duplicate가 생긴 상태를 어떻게 수렴시키는지 TODO로 기술한다. peak 50/s, p99 40초의 2,000 동시 실행 stress bound와 downstream/database limit의 차이를 기록한다.

## Stage 4 — SaaS

| Business / tenant state | Class | Authoritative owner | Tenant key가 존재하는 곳 | Lifecycle / terminal state | Reconciliation evidence |
| --- | --- | --- | --- | --- | --- |
| tenant·membership·role | TODO | TODO | TODO | TODO | TODO |
| plan version·entitlement | TODO | TODO | TODO | TODO | TODO |
| quota reservation·usage event | TODO | TODO | TODO | TODO | TODO |
| export job·delivery receipt | TODO | TODO | TODO | TODO | TODO |
| deletion workflow·tombstone | TODO | TODO | TODO | TODO | TODO |
| support session·audit event | TODO | TODO | TODO | TODO | TODO |

starter 100건/월, pro 10,000건/월을 plan label이 아닌 versioned entitlement로 표현한다. export는 24시간 안에 준비되고 active data는 deletion request 뒤 7일 안에 제거되도록 중간 상태와 subsystem별 completion을 TODO로 정의한다. 관계 스키마 자체는 database 소유 가이드로 넘기고 여기서는 tenant 경계와 lifecycle contract만 다룬다.

## Evidence와 한계

| Inventory 주장 | 비교할 두 source | Frequency / trigger | 불일치 처리 | 한계 |
| --- | --- | --- | --- | --- |
| 배포된 resource가 release manifest와 같다 | TODO | TODO | TODO | TODO |
| authoritative object와 metadata가 일치한다 | TODO | TODO | TODO | TODO |
| owner·expiry 없는 resource가 없다 | TODO | TODO | TODO | TODO |
| export/deletion 뒤 잔존 active data가 없다 | TODO | TODO | TODO | backup physical deletion은 unknown |
| orphan resource cost가 budget에 귀속된다 | TODO | TODO | TODO | provider unit price는 unknown |

provider inventory export, application state query, object inventory, restore checksum, final cleanup inventory를 증거 후보로 사용하되 각각이 보지 못하는 hidden replica·cache·backup을 TODO로 명시한다.

## Open risks와 owner

| Risk / unknown | Owner | Trigger / due | Required evidence | Fallback / handoff |
| --- | --- | --- | --- | --- |
| 실제 region/AZ와 provider quota 미선정 | TODO | TODO | TODO | TODO |
| max-object 5 GB/s stress bound 검증 전 | TODO | TODO | TODO | TODO |
| owner·expiry 없는 shared resource | TODO | TODO | TODO | TODO |
| provider backup·log retention 잔존 | TODO | TODO | TODO | TODO |
| commercial state와 billing export 불일치 | TODO | TODO | TODO | TODO |
