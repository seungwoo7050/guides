# Migration and Runbook Contract

## 공통 식별자

migration과 retirement record는 `svc-payments`, `env-payments-staging`, `op-payments-staging-v3`, `tenant-checkout`, `sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa`, `stateless-http/v3`를 유지한다.

## Migration Waves

목표는 기존 profile에서 `stateless-http/v3`로 이동하는 것이다. wave 0은 synthetic reference, wave 1은 opt-in staging 2개, wave 2는 10%, wave 3은 50%, wave 4는 나머지다. 각 wave entry에는 이전 wave evidence, owner acknowledgement, capacity headroom, rollback/roll-forward 가능 여부가 필요하다.

exit은 request success, Ready latency, error budget burn, workload health, policy deny와 support ticket이 threshold 안이고 observation window를 채운 상태다. failure threshold를 넘으면 현재 wave를 `Failed`, 이후 wave를 `Pending`으로 두고 자동 중단한다. 이미 적용된 artifact/config/data, traffic과 exception을 inventory한 뒤 reversible하면 rollback하고 그렇지 않으면 제한된 roll-forward plan을 승인받는다.

## Runbook

1. `op-payments-staging-v3`에서 first-failure owner, generation, partial effects와 evidence freshness를 확인한다.
2. API/control-plane이면 queue age, journal/replay point와 reconciler health를 확인한다.
3. IaC/provider이면 state lock/serial, provider IDs와 rate limit을 확인하고 import/converge 또는 cleanup을 선택한다.
4. runtime이면 scheduler, rollout, endpoint와 external smoke를 같은 generation으로 비교한다.
5. policy/identity이면 policy version, issuer/audience/TTL과 exception expiry를 확인한다. static credential을 발급하지 않는다.
6. recovery 뒤 동일 operation을 reconcile하고 status/evidence/catalog projection을 확인한다.

모든 수동 변경은 named owner, 이유, 시작/만료, before/after, 검증과 revert command/forward step을 incident에 남긴다. 실제 명령은 환경별 검토를 거치며 이 dossier가 production 명령 실행을 승인하지 않는다.

## Retirement

service owner 승인과 dependency/traffic 확인 뒤 새 request를 막고 traffic을 drain한다. data retention/export 결정을 먼저 기록하고 credential·policy exception을 revoke한다. IaC/provider resource, namespace/workload/storage, DNS, queue/quota reservation, catalog entry와 비용 inventory를 순서대로 닫는다.

삭제 증거가 없는 항목은 pending cleanup과 owner를 유지한다. 모든 active state가 닫힌 뒤에만 `Retired`를 발행하고 최소 audit tombstone에는 service/resource/tenant, 마지막 artifact/profile, operation outcome, retention class와 evidence hash를 남긴다. `svc-payments` 정리가 다른 service 환경이나 공유 control-plane을 삭제해서는 안 된다.
