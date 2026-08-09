# resource and state inventory

## Scope

이 inventory는 provider resource와 application/business state를 같은 이름으로 뭉개지 않고 `owner`, `region/zone`, `state class`, `dependency`, `expiry`, `cleanup evidence`로 연결한다. provider와 실제 region은 아직 미선정이므로 `region-primary`, `zone-a`, `zone-b`는 failure-domain을 나타내는 논리 이름이다. 실제 mapping·service quota·throughput·price는 `unmeasured/unknown`이다.

| State class | 판정 | 이 시스템의 예 |
| --- | --- | --- |
| authoritative | 잃으면 사용자나 업무 사실을 잃고 다른 정본에서 복원할 수 없음 | upload object, document metadata/status, tenant·membership, accepted usage event |
| derived | authoritative input과 versioned code로 재생성 가능 | extracted text, thumbnail, usage dashboard aggregate |
| ephemeral | lease·cache·runtime처럼 만료·재생성이 정상 | VM local temp, queue lease, function execution environment, cache entry |
| evidence | 운영·보안·복구·비용 주장을 재검토하는 기록 | audit/event trace, restore checksum, release manifest, final resource inventory |
| commercial | 고객 plan·권리·소비량·lifecycle 계약 | plan version, entitlement, quota reservation, usage, export/deletion job |

평균 동시 처리는 `2/s × 4초 = 8`이고 보수적 stress concurrency는 `50/s × 40초 = 2,000`이다. 평균 object의 peak ingress는 `50/s × 8 MB = 400 MB/s`, 모든 object가 최대 크기일 때 upper stress bound는 `50/s × 100 MB = 5,000 MB/s(약 5 GB/s)`다. 이는 capacity guarantee가 아니라 queue, object ingress, function, database와 egress limit을 검증하기 위한 bound다.

관계형 tenant schema·index·constraint의 내부 설계는 `database-systems`로 넘기고, 이 문서는 state ownership, failure domain, tenant key와 lifecycle만 고정한다. 여러 팀이 쓰는 cloud inventory platform은 후속 `platform-engineering` 범위다.

## Stage 1 — IaaS

| Resource ID / 종류 | Owner | Region / zone | Class·data | 주요 dependency | Backup·expiry | Cleanup evidence |
| --- | --- | --- | --- | --- | --- | --- |
| `edge-lb` / load balancer | runtime owner | region-primary / multi-zone | ephemeral config; public ingress | public subnet, TLS identity, `app-vm-*` | config version은 release와 동일; 고정 expiry 없음 | listener·address·target final inventory |
| `app-vm-a`,`app-vm-b` / VM pool | runtime owner | zone-a / zone-b | ephemeral runtime; authoritative file 금지 | private subnet, image, workload identity | image digest 고정; instance 교체 가능 | instance·volume·address가 desired set과 일치 |
| `app-image` / machine image | runtime owner | region-primary | release artifact/evidence | source revision, build provenance | 지원 종료일에 expire | digest와 사용 중 VM 대조, 구 image 삭제 기록 |
| `vnet` / public·private network | runtime/security owner | region-primary, zone-a/b subnet | control configuration | route, firewall, private endpoint | rule review 분기별 | route/firewall/endpoint inventory와 public scan |
| `db-primary`,`db-standby` | data owner | 서로 다른 zone | authoritative metadata·operation·tenant state | private network, DB identity, storage | point-in-time RPO ≤15분 목표 | isolated restore checksum, retired volume/snapshot inventory |
| `db-backup-*` / snapshot | data owner | primary와 격리된 failure scope | authoritative recovery copy·evidence | database engine/version, key | retention은 provider 선택 시 확정; 현재 unknown | expiry·restore result·잔존 snapshot 목록 |
| `obj-documents` / object storage | data owner | region-primary; 내부 zone scope unknown | authoritative upload, derived result | object policy, key, database operation ID | active/deleted tenant lifecycle 적용 | tenant별 object inventory와 metadata checksum |
| `api-role`,`worker-role`,`admin-role` | security/runtime owner | account/control plane; scope unknown | identity configuration | policy, workload, rotation mechanism | workload credential 단기; 실제 TTL unknown | unused binding·key 0, policy revision·audit |
| `obs-sink` / logs·metrics·audit | runtime/security owner | region-primary; failure scope unknown | evidence, 일부 derived aggregate | every service, clock, retention policy | retention은 계약 전 확정 | expected source coverage, expired data deletion report |

VM local disk와 process memory에는 upload 정본을 두지 않는다. zone 하나가 사라지면 다른 zone의 VM, private route, database failover target과 object access가 남아야 한다. 단일 zone에 남은 실제 capacity가 2,000 concurrent와 400 MB/s 일반 peak를 처리하는지는 아직 측정하지 않았고, 5 GB/s max-object bound는 admission·backpressure를 포함한 별도 stress scenario다.

| Operation | 시작·중간 상태 | 성공 상태 | 실패·timeout의 partial state | Reconciler와 orphan cleanup |
| --- | --- | --- | --- | --- |
| upload create | `RESERVED` operation과 tenant quota reservation → temporary object | checksum이 맞는 object + metadata `QUEUED`; 한 operation ID | object만 존재, metadata만 존재, client timeout 뒤 commit 결과 불명 | operation ID로 조회·재사용; 만료된 reservation과 unreferenced temp object를 inventory 후 삭제 |
| async process | durable event → `PROCESSING` lease·attempt | versioned text/thumbnail + status `SUCCEEDED` | lease 만료, result 일부, invalid/transient reason, worker loss | lease expiry 후 bounded retry; invalid는 terminal; result key와 attempt trace로 중복 억제 |
| result publish | temp result + checksum → deterministic final key | final object와 DB status가 같은 version/operation을 가리킴 | final object는 있으나 status는 processing, 또는 반대 | final-key 존재·checksum 확인 후 status 수렴; unreferenced temp result cleanup |
| document delete | tombstone → access deny → active metadata/object delete | active inventory 0, deletion evidence 보존 | subsystem 일부만 삭제, retry 중 | subsystem별 cursor와 idempotent delete; 7일 deadline alarm, backup retention 별도 고지 |

## Stage 2 — Managed platform

| 이동 전 resource | Managed resource / logical ID | 소비자가 계속 inventory할 state | 숨은 contract dependency·limit | Export·cleanup evidence |
| --- | --- | --- | --- | --- |
| `app-vm-*`,`app-image` | `managed-api-service`, release artifact/revision | code, config, workload identity, desired capacity, routing | platform instance·maintenance·request quota와 control plane scope unknown | revision list, route/identity detach, old release cleanup |
| `db-primary/standby` | `managed-db`, logical database/replica/backup | schema version, transaction outcome, connection policy, RPO/RTO | hidden replica, failover, connection cap, retention unknown | full export, restore checksum, snapshot/replica final inventory |
| self-managed worker queue | `managed-work-queue`, DLQ | operation/event ID, ack/retry/DLQ configuration | delivery·retention·throughput quota unknown | queue depth 0 or explained, DLQ export, trigger detach |
| backup scheduler | managed automated backup + explicit restore drill | retention acceptance, key, restore environment, report | "backup available" does not imply restorable; physical copy scope unknown | restore checksum, expired backup inventory where visible |
| direct service route/credential | private attachment + workload roles | least privilege policy, attachment owner, audit | policy propagation/private-path guarantee unknown | endpoint·binding·secret final inventory |

공급자 내부 host·replica는 직접 소유 resource row가 아니라 service contract dependency다. 반대로 version, configuration, service quota, identity binding, backup retention, export format은 관리형이어도 소비자 inventory에서 사라지지 않는다.

## Stage 3 — FaaS

| Resource / state | Owner | Class | Stable identity·tenant key | Limit / expiry | Cleanup·replay evidence |
| --- | --- | --- | --- | --- | --- |
| `processor-vN` / function version | runtime owner | release artifact/evidence | immutable version digest; tenant 없음 | support/rollback window; provider limit unknown | alias/trigger가 승인 version만 참조, old version inventory |
| `document-trigger` / event mapping | application owner | control configuration | operation ID를 전달, tenant는 operation record에서 재검증 | maximum age·attempt·batch/concurrency | config export, disabled stale trigger 0 |
| function execution environment | provider | ephemeral | 안정 identity로 사용 금지 | 언제든 폐기 가능; cold-start TTL unknown | inventory 대상이 아님; durable state 0임을 test |
| `operation` / idempotency record | application/data owner | authoritative coordination state | globally unique operation ID + tenant ID | output/usage retention보다 길게 유지 | unique outcome, duplicate-suppressed count, terminal reason |
| deterministic result object | data owner | derived | `tenant/operation/version` key | input 또는 retention과 함께 expire | checksum, source/version linkage, orphan inventory |
| queue lease / attempt | application owner | ephemeral + evidence trace | event/operation/tenant/attempt | bounded visibility·maximum age | expired lease 수렴, attempt trace |
| DLQ item / replay record | application owner | evidence + recoverable work | original operation·tenant, replay ID | reviewed expiry; unowned item 금지 | disposition, replay audit, remaining count |
| tenant concurrency counter | runtime/cost owner | ephemeral/derived guard | tenant ID + active reservation | global 2,000은 stress bound, tenant 30% 집중 고려 | observed concurrency·throttle·fairness report |

warm environment나 function instance 수는 정본이 아니다. result write 뒤 timeout이면 deterministic key와 checksum을 확인하고 기존 effect를 재사용한다. DB status가 `PROCESSING`인 채 result가 존재하면 reconciler가 status를 수렴시키고 usage는 동일 operation ID로 한 번만 accept한다. provider의 실제 concurrency, cold start, request/streaming limit은 미측정이다.

## Stage 4 — SaaS

| Business / tenant state | Class | Authoritative owner | Tenant key가 필요한 경로 | Lifecycle / terminal state | Reconciliation evidence |
| --- | --- | --- | --- | --- | --- |
| tenant·membership·role | authoritative | business/security owner | request, DB, audit, support | `ACTIVE → SUSPENDED → DELETING → DELETED` | membership audit와 deleted-tenant deny test |
| plan version·entitlement | commercial authoritative | product owner | quota decision, UI, usage | versioned; starter 100/pro 10,000 monthly | accepted decision이 사용한 plan version |
| quota reservation | commercial coordination | application owner | tenant + billing period + operation | `RESERVED → COMMITTED` 또는 `RELEASED`; expiry 있음 | committed + released + active가 ledger와 일치 |
| usage event | commercial authoritative | product/cost owner | tenant + operation + unit | operation당 한 번 accepted; correction은 append-only | dedup result와 dashboard/billing reconciliation |
| export job·artifact | authoritative workflow + evidence | data owner | tenant, requester, delivery identity | `REQUESTED → SNAPSHOTTED → READY/FAILED/EXPIRED`; 24시간 | manifest·checksum·delivery audit·expiry cleanup |
| deletion workflow·tombstone | authoritative lifecycle/evidence | data owner | 모든 subsystem | active data는 request 후 7일 내 `DELETED`; backup은 고지 retention | subsystem cursor, final active inventory 0, retry trace |
| support session | evidence | security/support owner | tenant + ticket + operator | approved·time-bound → closed | approval, accessed objects/actions, revoke time |

plan 이름을 코드 상수 하나로 취급하지 않고 versioned entitlement와 decision evidence를 남긴다. export와 deletion은 boolean flag가 아니라 partial failure를 나타내는 durable workflow다. backup의 물리 삭제 시점은 provider retention 계약을 선택하기 전 unknown이며 고객에게 active deletion과 구분해 고지한다.

## Evidence와 한계

| 주장 | 대조 source | Trigger | 통과 기준 | 한계 |
| --- | --- | --- | --- | --- |
| 배포 resource가 승인 상태와 같다 | release manifest ↔ provider resource inventory | 매 배포·매일 | unexpected resource/binding 0; 차이는 owner·expiry 있음 | provider 내부 node는 보이지 않음 |
| authoritative object와 metadata가 일치한다 | DB operation/status ↔ object inventory/checksum | 매일·incident 후 | orphan/missing을 분류하고 deadline 안에 수렴 | scan 사이의 순간 상태는 snapshot 시각 영향 |
| backup이 실제 복구 가능하다 | backup inventory ↔ isolated restore dataset checksum | 분기·engine 변경 | RPO ≤15분 sample, restore 완료 ≤60분 목표 | 실제 대규모 data와 provider outage는 별도 test |
| tenant lifecycle가 모든 subsystem에 전파된다 | deletion/export workflow ↔ DB/object/cache/queue/analytics inventory | 요청마다 | export ≤24시간; active delete ≤7일; 실패 owner 존재 | physical backup deletion은 contract 의존 |
| 비용 resource가 귀속된다 | owner/expiry inventory ↔ billing export ↔ tenant usage | 매월 | 미귀속 line/resource 0 또는 문서화된 shared allocation | 실제 provider 가격은 `unmeasured/unknown` |

inventory는 존재와 참조 관계를 보여 주지만 isolation, restore 가능성, 기술적 설계 타당성을 단독으로 증명하지 않는다. negative test, restore drill, event trace와 사람 review가 별도로 필요하다.

## Open risks와 owner

| Risk / unknown | Owner | 닫는 trigger | Required evidence | Fallback / handoff |
| --- | --- | --- | --- | --- |
| 실제 region/AZ·failure domain mapping | runtime owner | provider 선택 전 | 공식 범위와 zone-loss sandbox 결과 | 단일 region 한계를 release risk로 유지 |
| 2,000 concurrency·400 MB/s·5 GB/s resource limit | runtime/cost owner | capacity profile 승인 전 | load/admission test와 cost estimate | max size/rate admission 제한 |
| owner·expiry 없는 shared resource | runtime owner | 매일 inventory check | owner/expiry 보완 또는 cleanup record | 신규 배포 차단 |
| provider backup·log·key 잔존 | data/security owner | retention contract 전 | visible inventory와 provider terms | retention 고지, 민감 data 최소화 |
| commercial ledger와 cloud billing 차이 | product/cost owner | 월말 | operation-level usage와 billing reconciliation | invoice 판단 보류; schema 설계는 database guide handoff |
