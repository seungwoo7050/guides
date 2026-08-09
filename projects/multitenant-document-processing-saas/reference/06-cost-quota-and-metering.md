# cost quota and metering

## Scope

핵심 비교 단위는 `cost per 1,000 successful documents`, active tenant, stored GB-month와 tenant별 processing·egress다. provider bill의 resource consumption, product의 raw usage, Starter/Pro entitlement와 invoice pricing은 별도 ledger로 유지한다. 공급자와 월 budget 금액은 아직 선택되지 않았고 traffic의 월별 지속 시간도 주어지지 않았으므로 provider 단가, 실제 unit cost와 월 총액은 모두 `unmeasured/unknown`이다. 임의의 가격을 넣어 budget 승인을 가장하지 않는다.

평상시 2건/s와 평균 4초에서 평균 동시성은 8이다. 보수적 peak는 50건/s와 p99 40초를 곱한 2,000이며, peak에서 평균 8 MB object ingress는 400 MB/s, 최대 100 MB stress는 5 GB/s다. 이 수치는 request, duration, storage I/O와 network quantity의 capacity input이지만, peak 지속 시간이 없어 월 usage로 외삽하지 않는다.

## Stage 1 — IaaS

| cost class | 비용 형태 | quantity evidence | guard |
|---|---|---|---|
| VM pool·load balancer·database | idle/provisioned와 zone 여유 | instance-hours, capacity, zone | owner·cost center·expiry 필수 |
| object·volume·snapshot·backup | stored GB-month와 operation | bytes, retention, create/delete log | lifecycle과 final inventory |
| request·I/O·log | variable | request, read/write, ingested bytes | sampling·retention cap |
| egress | variable/step | source·destination·bytes | export estimate와 destination allowlist |
| address·image·orphan volume | idle waste | inventory age | expiry 후 alert·승인된 cleanup |

zone 하나의 compute 손실을 견디는 여유는 availability 요구 비용으로 따로 표시하고 orphan waste와 섞지 않는다. RPO 15분을 위한 backup frequency와 RTO 60분 restore capacity도 비용 항목이다. resource 삭제는 inventory·backup·key dependency를 확인한 명시적 cleanup run으로만 수행한다.

## Stage 2 — Managed platform

managed runtime·database·queue·object storage마다 minimum capacity, provisioned/request/throughput unit, storage·I/O, automated backup, restore environment, private network, observability, support와 quota increase lead time을 기록한다. 사용량이 없어도 청구되는 minimum/step cost와 처리량에 비례하는 variable cost를 분리한다.

bill line은 resource ID, environment, owner와 cost center tag로 inventory에 join하고, request·I/O는 application operation count와 일별 reconcile한다. provider price, discount, commitment term, backup/egress premium과 service limit은 공급자 선택 전 `unknown`이다. 공식 calculator 결과도 실제 bill이 아니므로 선택 뒤 representative traffic과 restore rehearsal에서 측정한다.

## Stage 3 — FaaS

FaaS quantity 식은 `invocations × billed duration × configured memory`에 object request·bytes, queue request, DLQ/redrive, logs, egress와 선택한 warm/provisioned capacity를 더한다. 정상 invocation 외에 invalid 1%는 첫 validation 후 terminal이며 재시도 비용을 만들지 않는다. transient 2%만 최대 3 attempts 내에서 비용을 늘린다. 실제 transient 분포와 recovery 비율은 `unmeasured`이므로 worst-case와 관측치를 함께 보존한다.

global maximum concurrency는 database·converter·object throughput의 last-known-safe 측정치로 제한하며 현재 정확한 값은 `unknown`이다. tenant별 dispatch target은 global active concurrency의 30%로 두어 한 enterprise tenant의 workload가 나머지를 고갈시키지 않게 한다. maximum attempts·event age, log byte cap, DLQ alert·redrive 승인과 월 budget hard guard가 무한 retry·logging 비용을 막는다. 월 budget 숫자가 정해지기 전에는 유료 provider experiment나 production enable을 허용하지 않는다.

## Stage 4 — SaaS

plan ID `starter`는 100건/월, `pro`는 10,000건/월의 versioned entitlement를 가진다. quota state는 `AVAILABLE → RESERVED → COMMITTED|RELEASED`이고, 마지막 한 건의 concurrent reservation은 compare-and-set으로 한 요청만 성공한다. 성공한 document의 usage identity는 `(tenant_id, operation_id, "document_processed")`이며 duplicate completion과 retry가 usage를 늘리지 않는다. invalid file과 최종 실패는 이 정책에서 reservation을 release하고 successful-document meter에는 포함하지 않는다.

tenant cost ledger는 document count, processing duration, source/result bytes, storage age, request/I/O, log와 egress를 operation ID로 연결한다. provider raw meter는 수정하지 않고 plan entitlement, overage 정책과 invoice price rule은 별도 version으로 적용한다. export는 요청 후 24시간 안에 usage·plan version·cost allocation을 manifest로 제공한다. deletion은 active data를 7일 안에 제거하되 tax/audit를 위해 보존할 aggregate usage의 목적·retention을 customer notice에 기록한다.

## Evidence와 한계

| reconcile | 비교 대상 | 합격 기준 | 한계 |
|---|---|---|---|
| document usage | successful operation ↔ unique usage event | 누락·중복 0 | 실제 invoice rule 미검증 |
| quota | reservation/commit/release ↔ plan limit | Starter 100, Pro 10,000 초과 없음 | distributed race는 integration 필요 |
| provider consumption | bill export ↔ tagged inventory·bytes·duration | owner 없는 line 0 | provider 내부 allocation 불명 |
| tenant allocation | shared+direct cost ↔ tenant meters | 총 allocation과 bill 차이 설명 | shared support 비율은 정책 판단 |
| cleanup | final inventory ↔ expected resources | orphan 0 또는 owner·expiry 존재 | provider delayed billing 가능 |

unit cost 식은 `attributable provider cost / successful documents × 1,000`이다. successful count가 0이면 나누지 않고 `undefined`로 보고한다. retry amplification, allocation rule version, bill 지연과 sampling 오차를 함께 남긴다. 현재는 provider price, 월 workload와 budget ceiling이 없으므로 숫자 unit cost·월 비용은 산출하지 않으며, local model은 quota·usage 불변식만 검증하고 청구 정확성은 검증하지 않는다.

## Open risks와 owner

| risk/condition | owner | due date | verification | rollback |
|---|---|---|---|---|
| provider 단가·limit·월 budget 미확정 | cost owner | 2026-09-29 | 선택 profile의 official price/limit snapshot과 representative estimate 승인 | 유료 experiment와 production enable 보류 |
| shared database·support 배분이 tenant unit cost를 왜곡 | cost owner | 2026-09-22 | direct/shared 합계가 provider bill과 reconcile되고 allocation version 표시 | direct cost만 공개하고 shared allocation을 `unknown` 처리 |
| retry·log가 비용을 폭주시킴 | runtime owner | 2026-09-15 | transient/poison load test에서 max attempts·log cap·budget alert 확인 | concurrency·redrive 중지, log level 축소 |
| deletion 뒤 usage retention이 customer 계약과 불일치 | product owner | 2026-09-22 | export/deletion notice와 retained fields·retention review | aggregate meter export 후 정책 확정까지 deletion release 보류 |
