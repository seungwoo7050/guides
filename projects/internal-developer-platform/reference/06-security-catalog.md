# Security and Catalog Contract

## 공통 식별자

security decision과 catalog feedback은 `svc-payments`, `env-payments-staging`, `op-payments-staging-v3`, `tenant-checkout`, `sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa`, `stateless-http/v3`를 correlation field로 사용한다.

## Identity와 Secret

human identity는 service intent 승인, workload identity는 runtime dependency 접근, automation identity는 reconciliation에 사용한다. 각 identity는 issuer, subject, audience, TTL, allowed action과 revocation owner가 다르다. build/deploy/control-plane 권한은 분리하고 tenant scope를 넘지 않는다.

static access key나 shared token은 issuer 장애의 fallback이 아니다. workload identity를 발급할 수 없으면 operation을 `Blocked`로 두고 owner와 복구 절차를 공개한다. secret 값은 API/status/catalog/log/evidence에 쓰지 않으며 reference와 version만 기록한다. rotation은 old/new version overlap과 revoke 확인을 가진 operation이다.

## Policy와 Break-glass

admission은 profile entitlement, tenant quota, artifact provenance, runtime bounds와 forbidden static credential을 effect 전에 평가한다. decision에는 policy bundle version, rule ID, input hash, result와 remediation을 남긴다. unknown/error를 allow로 바꾸지 않는다.

break-glass에는 named approver, reason, expiry, affected ID, before/after evidence가 필요하다. expiry가 없거나 증거가 없는 exception은 거부한다. 허용된 live drift도 `Ready` 증거를 대체하지 않고 catalog에 위험과 종료 시각을 표시한다. 만료 후 reconciler가 desired state로 수렴했는지 별도 evidence를 남긴다.

## Catalog와 Developer Feedback

catalog는 owner, profile, current condition, SLO, active operation, artifact digest, dependencies, support/runbook과 retirement 상태를 보여 준다. source of truth를 복제해 사용자가 수정하는 곳이 아니라 platform API/status의 projection이다. stale projection에는 observed time과 source generation을 표시한다.

developer에게는 `POLICY_DENIED`, `QUOTA_EXCEEDED`, `IDENTITY_UNAVAILABLE`, `PARTIAL_EFFECT`, `MIGRATION_ABORTED`처럼 안정된 code, owner, retryability, 다음 행동, evidence ref를 준다. controller 내부 stack trace나 “contact platform”만 반환하지 않는다. 실제 IAM enforcement와 catalog freshness는 이 로컬 합성 evidence 밖이므로 사람이 별도 확인한다.
