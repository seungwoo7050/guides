# SLO and Capacity Contract

## 공통 식별자

journey event는 `svc-payments`, `env-payments-staging`, `op-payments-staging-v3`, `tenant-checkout`, `sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa`, `stateless-http/v3`를 사용해 request와 최종 outcome을 결합한다.

## Journey SLO

SLI 분모는 schema와 entitlement를 통과해 `Accepted`가 기록된 고유 operation이다. 성공은 15분 안에 같은 generation의 `Ready` evidence가 생기는 것이며 사용자의 중복 retry는 새 분모가 아니다. user cancellation과 명시된 provider-wide disaster만 별도 분류하고 실패를 임의로 분모에서 제외하지 않는다.

목표는 rolling 28일 99.0%다. latency histogram, outcome code, first-failure owner와 evidence completeness를 함께 측정한다. 월간 0.5% fast-burn 또는 2시간 10배 burn이면 risky rollout을 멈추고 platform on-call에 page한다. 합성 모델 통과는 이 실제 SLO 달성을 증명하지 않는다.

## Capacity와 Fairness

API admission throughput, reconciliation workers/queue age, IaC/provider rate limits, cluster compute/storage/network, policy evaluation과 telemetry ingestion을 별도 capacity surface로 본다. 하나의 CPU 그래프로 전체 platform capacity를 표현하지 않는다. `tenant-checkout` quota는 최대 사용량을 제한할 뿐 부족한 cluster/provider capacity를 만들어 내지 않는다.

tenant queue는 weighted fair scheduling과 per-tenant concurrency를 쓰고 production reserve를 staging/preview burst와 분리한다. scale trigger는 p95 queue age와 saturation을 결합하며 provider limit에서는 worker만 늘리지 않는다. overload 때 새 preview를 명시적으로 거부하고 accepted operation과 retirement cleanup을 굶기지 않는다.

## Cost와 Support

resource에는 service, tenant, environment, profile, owner와 lifecycle tag를 요구하고 unallocated cost를 별도 지표로 둔다. 예상 월 비용과 plan delta를 admission feedback에 주되 가격 추정치를 보장으로 표현하지 않는다. idle staging에는 notification, grace period, owner-approved retirement를 적용하며 데이터는 자동 삭제하지 않는다.

support는 journey 실패율, time-to-owner, retry success, cleanup backlog와 toil을 측정한다. `op-payments-staging-v3` SLO 위반은 담당 writer와 runbook으로 route된다. capacity 변경은 가설, trigger, ceiling, 비용, rollback과 검증 window를 남기며 실제 비용·부하·provider quota는 인간 검토 대상이다.
