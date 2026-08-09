# responsibility matrix

## Scope

이 문서는 같은 문서 처리 workload를 IaaS, managed platform, FaaS, SaaS로 옮길 때 공급자·소비자·고객 admin 사이에서 **이동한 책임과 끝까지 남는 책임**을 task 단위로 기록한다. 서비스 이름만으로 분류하지 말고 누가 설정하고, 실패를 발견하고, 복구하며, 비용을 승인하는지 적는다.

고정 입력은 평상시 2 uploads/s, peak 50 uploads/s, 평균 8 MB·최대 100 MB object, 평균 처리 4초·p99 40초, invalid 1%, transient failure 2%다. 평균 concurrency `2 × 4 = TODO`, 보수적 peak concurrency `50 × 40 = TODO`, 평균 object 기준 peak ingress `50 × 8 MB = TODO`, 최대 object stress bound `50 × 100 MB = TODO`를 계산하고 어느 책임 판단에 쓰는지 설명한다.

| 책임 역할 | 이 설계의 담당자 | 승인하거나 보존할 증거 |
| --- | --- | --- |
| business owner | TODO | plan·quota·export·deletion 결정 |
| runtime owner | TODO | 배포·alarm·recovery 결과 |
| data owner | TODO | backup·restore·retention·deletion 결과 |
| cost owner | TODO | budget·unit cost·orphan inventory |

Linux host, 일반 retry/idempotency, 관계형 tenant schema, 공격 대응, 조직용 platform 구현은 이 문서에서 재교육하지 않는다. 각각의 소유 가이드로 넘기고 이 capstone에서는 cloud 책임 경계에 미치는 결과만 TODO로 연결한다.

## Stage 1 — IaaS

공급자가 제공하는 physical facility·host·hypervisor와 소비자가 소유하는 image·OS·network·runtime·database·backup·application·data의 경계를 채운다.

| Task 또는 상태 | Provider 책임 | Consumer 책임 | 실패 발견자 / 복구 owner | 필요한 evidence |
| --- | --- | --- | --- | --- |
| physical host와 hypervisor | TODO | TODO | TODO | TODO |
| VM image와 OS patch | TODO | TODO | TODO | TODO |
| public/private network와 egress | TODO | TODO | TODO | TODO |
| database와 backup restore | TODO | TODO | TODO | TODO |
| object upload와 derived output | TODO | TODO | TODO | TODO |
| zone 하나의 compute 손실 | TODO | TODO | TODO | TODO |
| capacity·budget·cleanup | TODO | TODO | TODO | TODO |

두 zone 중 하나를 잃어도 workload를 처리한다는 문장이 실제 capacity 책임인지, 공급자 SLA 의존인지 구분한다. RPO 15분·RTO 60분을 충족시키는 소비자 작업과 아직 측정하지 않은 항목을 `unmeasured/unknown`으로 표시한다.

## Stage 2 — Managed platform

VM, self-managed runtime/database/queue를 managed service로 바꾼다고 가정한다. 각 행에서 `이동한 task`와 `소비자에게 남은 판단`을 모두 적는다.

| Task | IaaS owner | Managed platform owner | 소비자에게 남는 책임 | 새 limit·failure | 확인 evidence |
| --- | --- | --- | --- | --- | --- |
| runtime host patch와 scaling | TODO | TODO | TODO | TODO | TODO |
| database engine patch와 failover | TODO | TODO | TODO | TODO | TODO |
| queue durability와 delivery | TODO | TODO | TODO | TODO | TODO |
| object durability와 restore | TODO | TODO | TODO | TODO | TODO |
| identity·private access·secret | TODO | TODO | TODO | TODO | TODO |
| backup retention·export·exit | TODO | TODO | TODO | TODO | TODO |

관리형이라는 이유만으로 schema, client timeout, restore 검증, quota, cost, portability를 공급자 책임으로 돌리지 않았는지 TODO로 검토한다. 공급자와 가격은 미선정이므로 service limit·SLA·price는 `unmeasured/unknown`으로 기록한다.

## Stage 3 — FaaS

async text extraction과 thumbnail worker만 FaaS로 이동한다. execution environment lifecycle과 invocation scaling이 이동해도 event 결과의 정확성은 소비자에게 남는다.

| Task | Provider 책임 | Consumer 책임 | 경계·대표 실패 | 필요한 evidence |
| --- | --- | --- | --- | --- |
| function environment와 instance lifecycle | TODO | TODO | TODO | TODO |
| event source delivery·ack·retry | TODO | TODO | TODO | TODO |
| handler·event identity·deterministic output | TODO | TODO | TODO | TODO |
| timeout 뒤 partial success | TODO | TODO | TODO | TODO |
| concurrency·downstream pressure·tenant fairness | TODO | TODO | TODO | TODO |
| DLQ replay·usage·quota·cost guard | TODO | TODO | TODO | TODO |

보수적 peak concurrency와 30%를 만들 수 있는 enterprise tenant가 어떤 concurrency·quota 책임을 만드는지 TODO로 설명한다. cold start, timeout, delivery guarantee, maximum concurrency와 실제 단가는 provider 선택 전 `unmeasured/unknown`이다.

## Stage 4 — SaaS

이제 소비자는 SaaS 공급자이고 고객 organization은 tenant다. 고객 admin에게 맡길 수 있는 설정과 SaaS 공급자가 위임할 수 없는 isolation·metering·lifecycle 책임을 분리한다.

| SaaS task | SaaS provider | Customer admin | Customer member | 내부 accountable owner | evidence |
| --- | --- | --- | --- | --- | --- |
| tenant create와 membership·role | TODO | TODO | TODO | TODO | TODO |
| request·DB·object·cache·queue isolation | TODO | TODO | TODO | TODO | TODO |
| starter 100 / pro 10,000 monthly quota | TODO | TODO | TODO | TODO | TODO |
| idempotent usage·cost attribution | TODO | TODO | TODO | TODO | TODO |
| export 24시간 | TODO | TODO | TODO | TODO | TODO |
| active data deletion 7일·backup notice | TODO | TODO | TODO | TODO | TODO |
| support access·audit·incident notice | TODO | TODO | TODO | TODO | TODO |

고객의 잘못된 sharing 설정과 공급자의 cross-tenant 결함을 같은 책임으로 처리하지 않는다. control plane과 data plane에서 공급자·고객 admin 책임이 달라지는 지점을 TODO로 명시한다.

## Evidence와 한계

| 주장 | 검증 방법 | 보존할 artifact | 통과 기준 | 증명하지 못하는 것 |
| --- | --- | --- | --- | --- |
| 책임 분류가 service label이 아닌 task 기반이다 | TODO | TODO | TODO | TODO |
| zone 손실 뒤 RTO/RPO를 만족한다 | TODO | TODO | TODO | TODO |
| duplicate가 output·usage를 한 번만 만든다 | TODO | TODO | TODO | TODO |
| cross-tenant access가 거부된다 | TODO | TODO | TODO | TODO |
| export와 deletion 목표를 지킨다 | TODO | TODO | TODO | TODO |
| budget·unit cost를 추적한다 | TODO | TODO | TODO | 실제 provider price는 unknown |

로컬 검사로 확인 가능한 계약과 실제 provider에서만 확인 가능한 SLA·IAM·network·billing·physical deletion을 나눈다. 자동 검사가 architecture 타당성이나 공급자 보장을 승인하지 않는 이유를 TODO로 적는다.

## Open risks와 owner

| Risk 또는 미결정 | Owner | Due / trigger | 닫는 evidence | 미해결 시 결정 |
| --- | --- | --- | --- | --- |
| provider·region·service limit 미선정 | TODO | TODO | TODO | TODO |
| 실제 failover·restore 시간 unmeasured | TODO | TODO | TODO | TODO |
| support access와 physical deletion unknown | TODO | TODO | TODO | TODO |
| unit price와 30% tenant의 cost 영향 unknown | TODO | TODO | TODO | TODO |
| 인접 소유 가이드 handoff 미확인 | TODO | TODO | TODO | TODO |
