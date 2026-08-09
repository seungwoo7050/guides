# Credential 또는 policy failure

## 증상

- Workload/automation token 발급 또는 갱신이 실패합니다.
- 정상 deployment가 새 policy에 거부됩니다.
- Secret reference는 존재하지만 materialization이 실패합니다.
- Authorization deny가 급증합니다.

## 즉시 확인할 영향

- 기존 credential이 언제 만료되는가?
- 새 workload만 영향받는가, 실행 중 workload도 곧 실패하는가?
- 특정 identity issuer, policy version, tenant 또는 environment인가?
- 보안상 fail-closed가 필요한 경계인가?

## 검사 순서

1. Secret value가 아닌 identity, audience, expiry와 error code를 확인합니다.
2. Issuer/broker, network, clock와 trust root를 확인합니다.
3. 최근 policy/role/profile 변경과 rollout wave를 확인합니다.
4. Deny decision의 policy ID, input context와 exception을 확인합니다.
5. Credential source·reference·materialized copy를 구분합니다.
6. Old/new credential dual-valid 또는 revocation 상태를 확인합니다.
7. Audit와 unauthorized access 시도를 확인합니다.

## 안전한 완화

- Bad policy rollout이면 다음 wave를 멈추고 previous policy version을 복원합니다.
- Issuer 일시 장애면 existing short-lived credential의 남은 수명을 보고 workload risk를 평가합니다.
- Emergency credential이 필요하면 좁은 scope·짧은 TTL·승인·audit로 발급합니다.
- Rotation 중 후보가 실패했다면 old credential을 즉시 폐기하지 않습니다.
- Compromise 의심이면 발급을 재개하기 전에 영향 identity와 artifact를 격리합니다.

장기 static key를 전체 workload에 배포하거나 policy를 cluster-wide disable하지 않습니다.

## 복구 판정

- 정상 identity가 새 credential을 발급·사용합니다.
- Unauthorized identity는 계속 거부됩니다.
- Policy fixture와 대표 workload가 통과합니다.
- Emergency/old credential이 폐기됩니다.
- Exception과 controller pause가 종료됩니다.
- Secret 값 없이 audit와 incident timeline이 완성됩니다.
