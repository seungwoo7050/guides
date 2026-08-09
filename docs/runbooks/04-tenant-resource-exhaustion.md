# Tenant resource exhaustion

## 증상

- 한 tenant의 environment·job·telemetry가 급증합니다.
- 공유 queue, cluster 또는 provider quota가 포화됩니다.
- 다른 tenant의 provisioning과 deployment latency가 증가합니다.
- Cost anomaly 또는 quota deny가 발생합니다.

## 영향 확인

- 어떤 shared resource가 포화됐는가?
- Production과 platform system capacity가 보호되는가?
- 악성/오류 automation인가, 정상 burst인가?
- 이미 실행 중인 workload를 중단해야 하는가, 새 요청만 제한하면 되는가?

## 검사 순서

1. Tenant ID, request source와 최근 변화량을 확인합니다.
2. API rate, queue, object count, compute, storage, network, telemetry와 cloud quota를 분리합니다.
3. Per-tenant quota와 global headroom을 비교합니다.
4. Preview TTL, orphan와 retry storm을 확인합니다.
5. Automation identity와 idempotency 오류를 확인합니다.
6. Cost와 사용자 impact를 추정합니다.

## 안전한 완화

- 새 low-priority 요청에 rate limit 또는 temporary deny를 적용합니다.
- Tenant별 controller concurrency를 줄입니다.
- Production/system reserved capacity를 보호합니다.
- 명확한 orphan와 만료 preview만 lifecycle policy에 따라 정리합니다.
- 정상 business burst면 비용 owner와 기간을 확인해 임시 quota를 승인할 수 있습니다.
- 오류 automation이면 credential 또는 workflow를 좁은 범위에서 중지합니다.

전체 tenant workload를 즉시 삭제하지 않습니다. Stateful data, external effect와 production impact를 먼저 확인합니다.

## 복구 판정

- Shared queue와 saturation이 SLO 범위로 돌아옵니다.
- 다른 tenant journey가 회복됩니다.
- Tenant owner가 원인과 제한 상태를 확인합니다.
- 임시 quota/rate/credential이 만료 또는 정상화됩니다.
- Orphan, cost와 external resource가 정리됩니다.

## 후속 action

- quota default와 increase workflow
- preview TTL와 cleanup
- idempotency/rate test
- per-tenant fairness
- cost anomaly alert
- capacity forecast
