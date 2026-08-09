# release review

## Scope

초기 production 후보는 managed runtime·database·queue·object storage, FaaS document worker와 SaaS tenant layer의 조합이다. IaaS는 isolated recovery/portability 기준선으로 유지한다. 작은 팀이 host와 database patch를 직접 운영하지 않으면서도 application identity, tenant isolation, event effect, restore, cost와 exit 책임은 소비자가 보유하는 선택이다.

판정 input은 평상시 2건/s·peak 50건/s, 평균 8 MB·최대 100 MB, 평균 처리 4초·p99 40초, invalid 1%·transient 2%, 단일 enterprise tenant 최대 30%, RPO 15분·RTO 60분이다. Product 계약은 Starter 100건/월·Pro 10,000건/월, export 24시간, active deletion 7일이다. 실제 cloud provider, SLA, limit, price와 월 budget 숫자는 아직 선택·측정되지 않아 `unknown/unmeasured`이며 아래 조건을 닫기 전 production 승인은 아니다.

## Stage 1 — IaaS

IaaS는 image, network, VM scaling, OS patch, database, backup·restore와 zone capacity를 팀이 직접 소유해 제어와 portability가 높다. 그러나 작은 팀에 patch window, image drift, 24×7 database recovery와 peak capacity 책임을 집중시킨다. 따라서 primary runtime으로 선택하지 않고 reproducible artifact·configuration·backup을 이용한 isolated recovery와 exit rehearsal 대상으로 유지한다.

합격 evidence는 zone 하나의 compute를 제거한 뒤 workload가 계속되고, isolated restore가 checksum·business invariant를 만족하며 RPO 15분·RTO 60분 안에 끝나는 report다. 이 rehearsal은 아직 실제 provider에서 실행되지 않았으므로 release condition이다. 실패 시 primary endpoint를 건드리지 않고 isolated target을 폐기하며 managed 경로를 유지한다.

## Stage 2 — Managed platform

managed runtime·database·queue·object storage는 host, engine patch, replica orchestration과 invocation infrastructure 일부를 공급자로 이동한다. 소비자는 code·schema, human/workload identity, private ingress/egress, service limit, client timeout/retry, backup restore 검증, observability, cost attribution과 exit를 계속 소유한다. `managed` 명칭은 restore·tenant isolation 또는 control-plane availability를 자동 보장하지 않는다.

표준 API path에는 적합하나 private access와 distinct admin/runtime identity, version lifecycle, quota increase lead time, zone failure behavior, 실제 restore, export format과 backup retention 계약을 provider profile에서 확인해야 한다. provider 미선택으로 SLA·limit·price는 모두 `unknown/unmeasured`다. 조건 실패 시 production binding을 만들지 않고 IaaS/local evidence와 대체 provider 비교를 유지한다.

## Stage 3 — FaaS

평균 동시성은 `2/s × 4s = 8`, 보수적 peak stress는 `50/s × 40s = 2,000`이다. peak에서 평균 8 MB object ingress는 400 MB/s이고 최대 100 MB stress는 5 GB/s다. FaaS는 burst 처리에 맞지만 자동 scaling이 downstream database·converter·object limit, timeout·cold start와 비용을 해결하지 않는다. global concurrency는 측정한 safe limit로 제한하고 단일 tenant dispatch를 30% 목표로 제한한다.

tenant-scoped operation ID, deterministic output key, usage-once, timeout-after-write reconcile, invalid 1% terminal 처리, transient 2% bounded retry, maximum attempts·age, partial batch, DLQ와 deletion-safe redrive가 필수다. local model은 duplicate/conflict/retry/DLQ/usage 공개 행동을 검증하지만 실제 cold start, 400 MB/s·5 GB/s data path와 provider delivery는 미측정이다. load/failure test가 실패하면 concurrency를 last-known-safe 값으로 낮추고 FaaS trigger를 disable한 뒤 managed worker queue로 되돌린다.

## Stage 4 — SaaS

request tenant context는 authenticated membership에서 만들고 body의 tenant ID를 신뢰하지 않는다. database composite key, object prefix, cache, queue/function, analytics, support session, export와 deletion 모두 tenant context를 carry한다. control plane은 membership·role·plan·quota·deletion command를, data plane은 upload·processing·result read를 다루며 human admin, workload, automation과 support identity를 분리한다.

Starter 100건/월과 Pro 10,000건/월은 atomic reservation과 idempotent usage로 집행한다. export는 membership, metadata, original/derived object, plan·usage와 checksum manifest를 24시간 안에 제공한다. deletion은 새 write와 replay를 차단하고 active data를 7일 안에 제거하며 backup·aggregate usage retention을 고지한다. cross-tenant negative test, quota race, duplicate completion, export authorization과 subsystem별 deletion inventory가 없으면 production tenant onboarding을 허용하지 않는다.

## Evidence와 한계

| evidence | 현재 상태 | 입증하는 범위 | 입증하지 못하는 범위 |
|---|---|---|---|
| local cloud model reference report | 재현 가능한 로컬 경로, 09에 명령·inventory 기록 | state, tenant isolation, quota, duplicate/retry/DLQ, deletion 공개 행동 | 실제 IAM·network·concurrency·provider SLA |
| architecture dossier와 human rubric | 제출됨, 사람 판정 필요 | 책임·state·failure·cost·exit 추적성 | 구현 또는 provider 보장 |
| zone loss와 isolated restore | 실제 provider에서 미실행 | 실행 뒤 RPO 15분·RTO 60분 | region-wide failure와 support response |
| cross-tenant integration/load test | 실제 provider에서 미실행 | 실행한 request/data path와 30% fairness | 모든 query와 hidden provider path |
| cost/export migration sample | price·dataset 미선택으로 unmeasured | 실행 뒤 unit cost·throughput·checksum | 미래 가격·traffic·physical deletion |

필수 local experiment의 budget은 0이고 credential·network·cloud resource가 없다. 실제 provider experiment는 별도 budget·최소 권한·resource inventory·cleanup 승인이 있을 때만 선택적으로 수행한다. 자동 검사 통과는 architecture의 기술적 타당성, 실제 공급자 보장 또는 교육적 완료를 자동 승인하지 않는다.

## Open risks와 owner

| condition/risk | owner | due date | verification | rollback |
|---|---|---|---|---|
| provider SLA·limit·price·monthly budget 미확정 | runtime owner | 2026-09-29 | official contract snapshot, limit table, tagged cost estimate와 budget approval | provider binding·유료 resource 생성을 보류 |
| human/workload IAM과 private network 미검증 | security owner | 2026-09-22 | distinct identity로 allow test와 cross-tenant/public-access deny evidence | public endpoint·tenant onboarding disable |
| zone loss·database restore가 RPO 15분/RTO 60분을 충족하는지 미측정 | data owner | 2026-09-22 | isolated restore checksum과 elapsed/RPO report | last-known-good managed profile 유지, migration 중단 |
| FaaS 2,000 stress·400 MB/s·5 GB/s path와 tenant fairness 미측정 | runtime owner | 2026-09-15 | bounded load test에서 queue age, error, concurrency, tenant별 completion 기록 | trigger disable, managed worker와 safe concurrency로 복귀 |
| export 24시간·active deletion 7일·backup wording 미검증 | product owner | 2026-09-22 | representative export timestamps/hash와 deletion final inventory·customer notice review | 신규 tenant onboarding 보류, source access 유지 |

Decision: APPROVE_WITH_CONDITIONS
