# Service scorecard Template

Scorecard는 팀을 벌점으로 순위 매기는 도구가 아닙니다. 지원되는 platform contract의 현재 상태, 개선 owner와 근거를 보여 줍니다.

## Metadata

- Service ID:
- Owner:
- Lifecycle:
- Runtime/profile version:
- Support tier:
- Repository:
- Environments:

## 계약 상태

| 항목 | 상태 | 근거 | Owner | 기한 |
|---|---|---|---|---|
| Owner 유효 | pass/warn/fail |  |  |  |
| Build workflow 지원 version |  |  |  |  |
| Immutable artifact와 provenance |  |  |  |  |
| Workload identity |  |  |  |  |
| Secret reference/rotation |  |  |  |  |
| Resource request와 quota |  |  |  |  |
| Network policy |  |  |  |  |
| Readiness와 smoke |  |  |  |  |
| SLO/dashboard/runbook |  |  |  |  |
| Backup/restore 요구 |  |  |  |  |
| Profile migration |  |  |  |  |
| Exception expiry |  |  |  |  |
| Retirement readiness |  |  |  |  |

## 해석 규칙

- `pass`는 자동 또는 반복 가능한 evidence가 있어야 합니다.
- `warn`은 위험과 기한, owner가 있어야 합니다.
- `fail`이 곧바로 deployment 차단을 뜻하지 않습니다. 차단 여부는 policy와 risk가 결정합니다.
- Score를 하나의 숫자로 합치지 않습니다. 서로 다른 risk를 평균내면 중요한 실패가 숨겨집니다.
