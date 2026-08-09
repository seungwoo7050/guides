# Platform runbook 색인

Runbook은 원인을 미리 단정하는 문서가 아닙니다. 불확실한 상황에서 사용자 영향과 최초 실패를 좁히고, 증거를 보존하며, 가역적인 완화와 복구를 수행하기 위한 순서를 제공합니다.

## 공통 사용 순서

1. 영향받는 사용자 journey, tenant와 environment를 확인합니다.
2. 현재 change, release, policy와 migration을 확인합니다.
3. request·operation·resource·generation identity를 고정합니다.
4. 사실과 가설을 분리합니다.
5. 증거를 지우지 않는 검사부터 수행합니다.
6. 자동 retry와 수동 행동이 충돌하지 않는지 확인합니다.
7. 가장 좁고 가역적인 완화를 선택합니다.
8. 사용자 결과와 backlog drain까지 복구를 검증합니다.
9. 임시 권한·pause·exception을 종료합니다.
10. 재발 방지 action에 owner와 기한을 둡니다.

## 목록

| 증상 | Runbook |
|---|---|
| Provisioning operation이 진행되지 않음 | [01 Provisioning stuck](01-provisioning-stuck.md) |
| Desired state와 live state가 반복해서 다름 | [02 Reconciliation drift](02-reconciliation-drift.md) |
| Workload가 schedule되지 않음 | [03 Workload unschedulable](03-workload-unschedulable.md) |
| 한 tenant가 quota/capacity를 소진함 | [04 Tenant resource exhaustion](04-tenant-resource-exhaustion.md) |
| Platform API 요청이 지연·실패함 | [05 Platform API degraded](05-platform-api-degraded.md) |
| Credential 발급 또는 policy 판단 실패 | [06 Credential or policy failure](06-credential-or-policy-failure.md) |
| Platform upgrade 뒤 오류 증가 | [07 Upgrade rollback](07-upgrade-rollback.md) |

## Runbook이 증명하지 않는 것

- 특정 원인이 항상 맞다는 사실
- 실제 조직의 승인·규제 절차
- provider 또는 제품별 정확한 명령
- application 업무 상태의 복구

운영 환경에 적용하기 전에 실제 system name, dashboard, query, 권한, communication channel과 안전한 명령으로 보완합니다.
