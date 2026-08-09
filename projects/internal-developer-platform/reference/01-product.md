# Product Contract

## 공통 식별자

| 종류 | 고정 ID |
|---|---|
| service | `svc-payments` |
| resource | `env-payments-staging` |
| operation | `op-payments-staging-v3` |
| tenant | `tenant-checkout` |
| artifact | `sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa` |
| profile | `stateless-http/v3` |

## 사용자와 문제

`tenant-checkout`의 `svc-payments` owner가 첫 사용자다. 지금은 staging 환경 하나를 얻으려면 IaC, namespace, DNS, CI 네 작업 큐를 직접 조정하고 실패 owner를 다시 찾아야 한다. 최근 20건을 표본 조사한 결과 중앙값 lead time은 46분이고 7건은 재시도 때 중복 자원을 만들었다. 따라서 첫 product slice는 portal이 아니라 versioned request/status 계약, 단일 operation identity, 실행 가능한 실패 feedback이다.

성공은 `env-payments-staging` 요청이 15분 안에 검증된 `Ready`가 되고, 사용자가 `op-payments-staging-v3`만으로 현재 단계·첫 실패·owner·다음 행동을 찾는 것이다. adoption 수치만으로 성공을 주장하지 않고, journey SLI와 support load를 함께 본다.

## Golden path

1. 사용자는 `profile_id=stateless-http/v3`, tenant와 service, idempotency key를 API에 제출한다.
2. admission은 schema, entitlement, tenant quota, policy를 effect 전에 원자적으로 평가한다.
3. controller는 resource와 operation을 만들고 `Accepted → Progressing`으로 전이한다.
4. build된 `sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa`를 다시 빌드하지 않고 staging에 승격한다.
5. IaC, runtime, policy, artifact, workload readiness, 외부 smoke 결과를 operation evidence에 붙인다.
6. 모든 필수 evidence가 같은 generation을 가리킬 때만 `Ready`가 된다. 실패나 partial effect는 숨기지 않고 owner·cleanup action과 함께 `Blocked` 또는 `Degraded`가 된다.

지원 경로는 같은 API/status와 catalog detail을 사용한다. 재시도는 같은 payload면 기존 operation을 돌려주고, 같은 key의 다른 payload면 side effect 없이 충돌한다.

## 비범위와 다음 경로

이 capstone은 cloud provider 사용법, Kubernetes 기초, Terraform 문법, CI 엔진 문법, IAM 또는 observability의 일반 이론을 다시 가르치지 않는다. 그것들은 선행 전문 브랜치의 책임이다. 여기서는 그 기능을 platform product의 resource/status/evidence/SLO 계약으로 결합하는 책임만 깊게 다룬다.

실제 production rollout, 유료 자원 생성, 실제 credential 발급은 범위 밖이다. 성공한 합성 모델은 설계 evidence일 뿐 production readiness 증명이 아니다. 다음 단계는 작은 사용자 cohort에서 shadow mode로 요청·status·support 측정을 수집하고, 별도 승인 뒤 canary migration을 수행하는 것이다.
