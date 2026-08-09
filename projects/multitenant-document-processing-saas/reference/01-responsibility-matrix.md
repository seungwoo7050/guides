# responsibility matrix

## Scope

대상은 B2B organization을 tenant로 삼아 PDF/image를 받고 metadata 저장, 비동기 text extraction·thumbnail, result download, quota·usage, export·deletion을 제공하는 작은 팀의 SaaS다. 동일 workload를 네 stage에 배치해 service marketing label이 아니라 **누가 설정하고, 실패를 발견하고, 복구하고, 비용과 고객 결과를 책임지는지**로 분류한다.

| Accountable role | 이 설계의 담당 | 위임할 수 없는 결정과 증거 |
| --- | --- | --- |
| business owner | product owner | starter 100건/월·pro 10,000건/월, export 24시간, active deletion 7일, 고객 공지 |
| runtime owner | cloud application lead | 배포, capacity, alarm, failover, cleanup, operation trace |
| data owner | data lead | authoritative state, RPO 15분, restore checksum, retention·deletion inventory |
| cost owner | engineering manager | 월 budget, tenant별 unit cost, quota와 orphan resource review |

평상시 concurrency는 `2 uploads/s × 평균 4초 = 8`, 보수적 peak concurrency는 `50 uploads/s × p99 40초 = 2,000`이다. 평균 object 기준 peak ingress는 `50 × 8 MB = 400 MB/s`, 최대 object만 연속 유입되는 stress bound는 `50 × 100 MB = 5,000 MB/s(약 5 GB/s)`다. 이 값은 보장된 용량이 아니라 capacity·quota·비용 검증의 입력이다. 공급자, 실제 limit, SLA와 가격은 아직 `unmeasured/unknown`이다.

단일 Linux/Docker/TLS 운영은 `web-infra`, 일반 retry·idempotency·DLQ는 `distributed-services`, tenant 관계 스키마는 `database-systems`, 위협 대응은 `cybersecurity`, 여러 팀용 golden path와 self-service 운영은 후속 `platform-engineering`으로 넘긴다. 여기서는 그 원리가 cloud 책임 이동과 tenant 계약에 주는 결과만 다룬다.

## Stage 1 — IaaS

공급자는 시설·전력·물리 host·hypervisor와 VM/network/storage API 가용성을 맡는다. 소비자인 cloud application team은 guest 위의 모든 것과 서비스 결과를 맡는다.

| Task / 상태 | Provider 책임 | Consumer 책임 | 실패 발견·복구 owner | 판단 evidence |
| --- | --- | --- | --- | --- |
| physical host·hypervisor | 물리 교체, 격리, virtual resource API | zone을 분리해 배치하고 host failure를 가정 | runtime owner가 instance health로 감지, 교체 VM 검증 | provider incident와 instance replacement trace |
| VM image·OS·runtime | VM 실행 기반 | image pinning, patch, hardening, process supervisor, rollback | runtime owner | image digest, patch report, release manifest |
| network·egress | virtual network primitive | public ingress 최소화, route/firewall, TLS endpoint, egress guard | runtime/security owner | flow·firewall inventory와 deny test |
| database·backup | block/storage primitive durability 범위 | engine patch, replication, transaction 결과, backup schedule와 restore | data owner | backup ID가 아닌 isolated restore checksum과 RPO/RTO report |
| upload/result object | storage API contract | tenant key, write completion, lifecycle, orphan reconciliation | data/application owner | object inventory, metadata reconciliation, checksum |
| zone compute loss | zone resource 실패 표면 제공 | 한 zone 제거 뒤 필요한 capacity와 routing 유지 | runtime owner | zone-loss drill, latency/error, final inventory |
| cost·cleanup | usage/billing record 제공 범위 | budget guard, owner·expiry, snapshot/address/log cleanup | cost owner | resource inventory와 billing export reconciliation |

IaaS를 선택해도 공급자가 RPO 15분·RTO 60분이나 zone-loss 후 application correctness를 보장하지 않는다. 보수적 2,000 concurrency와 400 MB/s 일반 peak, 5 GB/s max-object stress bound를 어느 수준까지 수용할지는 소비자 capacity decision이다. 실제 throughput과 단가는 미측정이다.

## Stage 2 — Managed platform

runtime host, database engine patch·replica orchestration, queue infrastructure와 object durability 일부가 공급자에게 이동한다. 이동한 운영 task와 application 결과 책임을 구분한다.

| Task | 공급자로 이동한 부분 | 소비자에게 남는 부분 | 새 failure/limit | Evidence owner |
| --- | --- | --- | --- | --- |
| managed runtime | host image, process restart, platform scaling primitive | artifact, configuration, health signal, scaling policy, rollback | deploy/control plane outage, instance·request quota | runtime owner |
| managed database | engine patch, replica/failover mechanism, automated backup primitive | schema, transaction ambiguity, connection retry, restore drill, export | connection cap, maintenance, replica lag, restore time | data owner |
| managed queue | broker patch, durable delivery primitive | message identity, ack timing, retry/DLQ policy, poison handling | retention, delivery delay, quota, duplicate | application owner |
| object storage | internal replication/durability contract | tenant authorization, checksum, lifecycle, inventory, deletion | request/throughput limit, regional dependency | data owner |
| identity/private access | IAM/network primitives | least-privilege roles, attachment, rotation, negative test | policy propagation, control-plane availability | security/runtime owner |
| backup·exit·cost | service export/billing mechanisms | RPO/RTO acceptance, restore validation, portability, budget | proprietary format, retention, egress and minimum capacity | data/cost owner |

"managed"는 schema, client timeout, entitlement, tenant isolation, restore acceptance와 exit를 공급자 책임으로 만들지 않는다. provider별 SLA·regional control plane·quota·price는 선택 뒤 검증할 `unmeasured/unknown` 항목이다.

## Stage 3 — FaaS

text extraction·thumbnail worker만 FaaS로 옮긴다. 공급자는 execution environment lifecycle, instance provisioning과 invocation scaling primitive를 운영하지만 event에서 business completion까지는 소비자 책임이다.

| Task | Provider 책임 | Consumer 책임 | 대표 failure와 경계 | Evidence |
| --- | --- | --- | --- | --- |
| environment lifecycle | 격리된 실행 환경 생성·폐기 | compatible artifact, configuration, cold-start tolerance | warm state 유실·cold start | version/config manifest, latency distribution |
| event delivery | trigger와 문서화된 delivery/ack 동작 | operation ID, duplicate-safe handler, maximum age·attempt | duplicate, delayed delivery, ack ambiguity | event/attempt trace와 DLQ inventory |
| handler result | invocation 실행과 timeout enforcement | deterministic output, status·usage 원자적 수렴 | result write 뒤 timeout | 한 operation ID당 output·usage 1개 검사 |
| concurrency | account/service scaling primitive | downstream limit, per-tenant fairness, admission·backpressure | 2,000 stress bound, 30% enterprise tenant 집중 | concurrency·throttle·tenant metric |
| invalid/transient | 없음 | invalid 1% terminal 분류, transient 2% bounded retry | poison retry 폭주와 cost amplification | terminal reason, retry count, replay audit |
| cost guard | usage meter 범위 | maximum concurrency·attempt, log/egress guard, budget alarm | retry storm·unbounded logs | cost estimate와 billing 대조; 실제 가격 unknown |

function return은 업무 완료가 아니다. output·document status·usage·quota가 같은 operation ID로 최종 상태에 수렴해야 한다. FaaS delivery guarantee, cold start, timeout, concurrency와 실제 단가는 provider 선택 전 미측정이다.

## Stage 4 — SaaS

이 stage에서 우리 팀은 고객 organization에 서비스를 제공하는 SaaS provider다. 고객 admin에게 위임한 구성과 공급자가 위임할 수 없는 tenant 안전·상업 상태 책임을 분리한다.

| SaaS task | SaaS provider 책임 | Customer admin 책임 | Customer member 책임 | Accountable 내부 owner |
| --- | --- | --- | --- | --- |
| tenant·membership·role | membership 경계와 authorization enforcement, audit | 자기 tenant의 초대·role·회수 | 허용된 tenant 선택과 기능 사용 | business/security owner |
| data isolation | request·DB·object·cache·queue·function·analytics 경계 | 자기 tenant 내 sharing policy | 허용 범위에서만 read/write | data/security owner |
| quota·usage | starter 100/pro 10,000 entitlement, atomic reservation, idempotent metering | plan 선택과 usage 확인 | 처리 요청 | business/application owner |
| availability·recovery | RPO 15분·RTO 60분 목표, incident/recovery evidence | 연락처와 integration 설정 유지 | 재시도 안내 준수 | runtime/data owner |
| export | 요청 authorization, 24시간 내 준비, checksum·delivery audit | export 요청·수신자 관리 | 권한 있을 때 download | data/product owner |
| deletion | 7일 내 active data 제거 workflow와 backup retention 고지 | 승인된 deletion 요청, 영향 확인 | 삭제된 tenant 접근 불가 | data/product owner |
| support access | 승인·시간 제한·최소 권한·audit·고객 공지 | support 승인과 연락 | 해당 없음 | security/support owner |

고객 admin이 잘못된 member에게 자기 tenant 문서를 공유한 사건과 SaaS provider가 tenant B 문서를 노출한 isolation 결함은 같은 책임이 아니다. 공급자는 control plane의 tenant lifecycle과 data plane의 모든 tenant context 전파를 함께 소유한다.

## Evidence와 한계

| 주장 | 검증과 artifact | 통과 기준 | 한계 |
| --- | --- | --- | --- |
| 책임은 task 단위로 분류된다 | stage별 matrix와 실제 service contract review | moved/retained task와 owner가 모두 있음 | provider marketing name의 적합성은 증명하지 않음 |
| zone loss 뒤 목표를 지킨다 | zone-loss drill, alarm·latency·error, restore/RPO/RTO report | RPO ≤15분, RTO ≤60분, final inventory 수렴 | local model은 실제 provider zone을 재현하지 않음 |
| duplicate effect가 하나다 | duplicate·timeout injection과 operation trace | output·status·usage가 logical operation당 1개 | 공급자 delivery SLA는 별도 확인 필요 |
| tenant 경계가 유지된다 | cross-tenant request/object/cache/queue negative test, audit log | 모든 경로 deny, tenant A 상태 변화 없음 | policy simulation만으로 application bug를 배제 못함 |
| export/deletion 계약을 지킨다 | timed export, subsystem deletion inventory, backup notice | export ≤24시간, active deletion ≤7일 | provider physical deletion은 contract evidence 의존 |
| 비용을 책임 있게 판단한다 | owner/expiry inventory, unit-cost estimate, billing reconciliation | 미귀속 resource 0, tenant usage와 cloud usage 차이 설명 | provider price와 실제 workload cost는 `unmeasured/unknown` |

자동 검사는 artifact의 형식과 공개 불변식을 확인할 뿐 architecture의 기술적 타당성, 실제 provider SLA·IAM·network·price·physical deletion을 승인하지 않는다.

## Open risks와 owner

| Risk / 미결정 | Owner | 닫는 시점 | 필요한 evidence | 미해결 시 처리 |
| --- | --- | --- | --- | --- |
| provider·region·service quota 미선정 | runtime owner | provider shortlist 승인 전 | limit/SLA/control-plane matrix와 sandbox test | release 조건부 유지 |
| 2,000 concurrency·400 MB/s·5 GB/s bound 미측정 | runtime/cost owner | capacity profile 확정 전 | load test, throttle·downstream·cost report | admission cap 축소 |
| 실제 failover·restore time 미측정 | data owner | production data 수용 전 | isolated restore와 managed failover report | RPO/RTO 승인 보류 |
| support access·physical deletion 범위 | security/data owner | customer contract 확정 전 | access audit와 provider retention terms | 기능 제한·고객 고지 |
| 실제 provider 가격 | cost owner | provider 선택·매월 review | versioned estimate와 billing export | budget/plan 재조정; 현재 unknown |
