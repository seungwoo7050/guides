# cost quota and metering

## Scope

provider bill, workload unit cost와 SaaS entitlement를 분리한다. 가격표가 아니라 `cost per 1,000 successful documents`, active tenant, stored GB-month, processing duration, request·I/O·egress를 기준으로 비교한다. provider가 선택되지 않았으므로 실제 단가와 월 비용은 **unmeasured/unknown**으로 남기고 임의 가격을 만들지 않는다.

| workload input | 고정값/계산 |
|---|---|
| upload | 평상시 2/s, peak 50/s |
| object | 평균 8 MB, 최대 100 MB |
| processing | 평균 4초, p99 40초 |
| concurrency | 평균 8, 보수적 peak stress 2,000 |
| peak ingress | 평균 크기 400 MB/s, 최대 크기 stress 5 GB/s |

TODO: traffic 지속 시간과 월 document 수가 없으므로 월 비용을 확정할 수 없다는 가정을 적는다.

## Stage 1 — IaaS

| cost class | idle/variable/step | quantity evidence | guard |
|---|---|---|---|
| VM·load balancer·database | TODO | TODO: uptime/capacity | TODO |
| object·snapshot·backup | TODO | TODO: GB-month·retention | TODO |
| request·I/O·log | TODO | TODO: operation count/bytes | TODO |
| egress·orphan resource | TODO | TODO: inventory/destination | TODO |

TODO: owner·cost center·expiry 없는 resource를 거부하고 zone 장애 여유 용량을 idle waste와 구분한다.

## Stage 2 — Managed platform

minimum capacity, provisioned/request/throughput unit, storage·I/O, backup, private network premium, observability, support와 quota increase lead time을 비교표에 넣는다. 사용량이 0이어도 발생하는 minimum/step cost를 표시한다.

TODO: provider 단가·discount·commitment는 선택 뒤 측정하며 현재는 unknown으로 둔다. bill export의 resource tag와 application operation ID를 연결하는 reconciliation 절차를 작성한다.

## Stage 3 — FaaS

invocation, duration×memory, retry, DLQ, log, object I/O, egress와 warm/provisioned capacity를 계산식으로 쓴다. invalid 1%와 transient 2%가 invocation·duration을 얼마나 늘리는지 별도 계수로 둔다.

TODO: global maximum concurrency, tenant별 30% fairness cap, maximum attempts·age와 budget hard guard를 정한다. cold start 대응 비용과 p99 40초 처리의 timeout 여유는 측정 전 unknown으로 표시한다.

## Stage 4 — SaaS

Starter 100건/월, Pro 10,000건/월의 entitlement를 versioned plan으로 정의한다. `AVAILABLE → RESERVED → COMMITTED|RELEASED` quota 상태와 `(tenant_id, operation_id, meter_name)` usage identity를 사용한다.

| 사례 | 기대 결과 | evidence |
|---|---|---|
| quota 마지막 1건 동시 요청 | 정확히 한 reservation만 성공 | TODO |
| duplicate completion | usage 1회 | TODO |
| invalid input | TODO: quota/usage 정책 | TODO |
| tenant deletion·export | charge와 보존 usage 처리 | TODO |

TODO: raw metering, entitlement, invoice pricing을 섞지 않고 tenant별 storage·processing·egress와 shared cost 배분 규칙을 작성한다.

## Evidence와 한계

provider bill/export, resource inventory, request outcome, duration·bytes, quota reservation과 usage event를 operation ID로 대조한다. 다음 식과 오차를 제출한다.

`unit cost = attributable provider cost / successful documents × 1,000`

TODO: shared/idle cost 배분, retry amplification, 누락·중복 meter 허용 오차와 reconcile 주기를 정한다. 추정치는 실제 공급자 가격·할인·traffic 지속 시간이 없으면 budget 승인 증거가 아님을 밝힌다.

## Open risks와 owner

| risk/condition | owner | due date | verification | rollback |
|---|---|---|---|---|
| TODO: 실제 provider 단가·limit 미측정 | TODO | TODO: YYYY-MM-DD | TODO | TODO |
| TODO: shared database/support 배분 왜곡 | TODO | TODO: YYYY-MM-DD | TODO | TODO |
| TODO: retry·log 비용 폭주 | TODO | TODO: YYYY-MM-DD | TODO | TODO |
