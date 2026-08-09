# Northstar Platform Scenario

## 조직과 사용자

Northstar에는 application team 4개, 서비스 18개, 중앙 platform team 1개가 있습니다. application developer는 staging 환경을 만들기 위해 IaC repository, CI workflow, cluster namespace와 DNS ticket을 각각 수정합니다. 실패했을 때 어느 팀이 다음 행동을 소유하는지 알기 어렵고 environment cleanup도 일관되지 않습니다.

Capstone의 첫 사용자는 `tenant-checkout`의 `svc-payments` service owner입니다. 요청 대상은 `env-payments-staging`, operation은 `op-payments-staging-v3`, 배포 artifact는 `sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa`, runtime profile은 `stateless-http/v3`입니다.

## 목표 Journey

유효 요청은 15분 안에 `Ready`가 되며 operation status에서 현재 단계, 첫 실패, owner와 다음 행동을 볼 수 있어야 합니다. `Ready`는 controller 내부 성공이 아니라 policy version, artifact digest, workload readiness와 외부 smoke evidence를 모두 관찰한 상태입니다.

## 제약

- staging tenant environment quota는 2개입니다.
- production reserve는 preview/staging burst와 분리합니다.
- 장기 static credential fallback은 허용하지 않습니다.
- GitOps live drift는 되돌리며 break-glass에는 approver·expiry·reason·evidence가 필요합니다.
- profile migration은 canary와 wave로 진행하고 failure threshold에서 중단합니다.
- retirement는 traffic·data·credential·runtime·catalog·cost state를 각각 닫습니다.
- 필수 자동 evidence는 실제 cloud·cluster·credential 없이 결정적 로컬 모델로 생성합니다.

## 완료 주장 한계

합성 model report는 API 상태 계약, idempotency, evidence gate, tenant isolation, drift, credential fallback, migration abort와 cleanup을 검증합니다. 실제 provider operation, Kubernetes/CNI/storage, concurrent reconciler, workload identity issuer, GitOps controller, billing과 physical deletion은 검증하지 않습니다.
