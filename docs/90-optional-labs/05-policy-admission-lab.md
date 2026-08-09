# Admission policy 실습

Local cluster에서 policy를 audit/warn/deny 단계로 적용하고, 정상 workload와 위반 workload의 결과를 비교합니다. Kubernetes CEL, Kyverno 또는 Gatekeeper 중 하나를 선택합니다.

## 목표

- policy를 source 검사와 runtime admission에서 각각 적용하는 이유를 봅니다.
- audit/warn/deny rollout의 차이를 확인합니다.
- error message와 remediation이 사용자에게 전달되는지 확인합니다.
- policy exception의 scope와 expiry를 설계합니다.
- policy 또는 webhook 장애 때 fail-open/fail-closed 결과를 검토합니다.

## 예시 정책

- privileged container 금지
- hostPath 또는 host namespace 제한
- image tag 대신 digest 요구
- resource request 필수
- owner/profile label 필수

모든 정책을 한 번에 강제하지 않습니다. 하나를 선택해 lifecycle을 완성합니다.

## 기본 흐름

1. 위반 workload와 정상 workload fixture를 작성합니다.
2. audit 또는 warn mode에서 inventory를 수집합니다.
3. policy ID, owner, message와 remediation을 보완합니다.
4. test namespace에서 deny mode를 적용합니다.
5. 정상 workload 통과와 위반 workload 거부를 확인합니다.
6. 좁은 scope와 expiry를 가진 exception을 설계하거나 적용합니다.
7. policy controller 장애 또는 timeout을 안전하게 모의해 failure policy를 확인합니다.
8. policy와 test resource를 cleanup합니다.

## 검토 질문

- 사용자가 배포 마지막 단계 전에 같은 오류를 확인할 수 있습니까?
- Deny message가 어떤 field를 어떻게 수정할지 알려 줍니까?
- Existing workload에는 어떤 migration과 deadline을 제공합니까?
- Exception이 전체 namespace 또는 cluster에 과도하게 적용되지 않습니까?
- Policy controller 장애가 모든 deployment를 막아야 합니까?
- Policy change 자체가 version·review·canary·rollback을 가집니까?
