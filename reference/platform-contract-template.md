# Platform capability 계약 Template

## 1. Capability

- 이름:
- Version:
- Owner:
- 지원 수준:
- 대상 사용자:
- 해결하는 문제:
- 비범위:

## 2. 요청 계약

- Resource identity:
- 입력 spec:
- Default:
- Validation:
- Idempotency:
- Approval/policy:
- Quota/capacity:

## 3. 상태 계약

- Desired state 정본:
- Observed state source:
- Generation:
- Conditions:
- Progress evidence:
- Ready 판정:
- Terminal failure:

## 4. 외부 효과

| 효과 | Writer | External ID | Retry | Cleanup |
|---|---|---|---|---|
|  |  |  |  |  |

## 5. 실패와 복구

- Retryable failure:
- User action required:
- Platform defect:
- Cancellation:
- Partial success:
- Rollback/forward repair:
- Orphan detection:

## 6. 보안과 tenancy

- 사람/workload/automation identity:
- Secret reference:
- Policy:
- Exception:
- Tenant boundary:
- Audit/redaction:

## 7. 운영

- Journey SLI/SLO:
- Capacity unit/headroom:
- Cost owner:
- Alert/runbook:
- Support/escalation:
- Backup/restore:

## 8. Lifecycle

- Compatibility:
- Upgrade/migration:
- Deprecation:
- Delete/retention:
- Evidence retention:
