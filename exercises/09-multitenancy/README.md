# Multi-tenancy와 자원 공정성

## 목표

Tenant 정의, isolation profile, quota, noisy-neighbor 방어와 tenant lifecycle을 설계합니다.

## 먼저 읽을 문서

- [`13-multitenancy-quotas-and-isolation.md`](../../docs/13-multitenancy-quotas-and-isolation.md)

## 시작 상태

`skeleton/submission.json`은 의도적으로 미완성입니다. 원본을 직접 수정하지 말고 `.workspace/`에 복사합니다.

```sh
mkdir -p .workspace/09-multitenancy
cp exercises/09-multitenancy/skeleton/submission.json \
  .workspace/09-multitenancy/submission.json
```

## 수행할 작업

1. Tenant가 어떤 보안·비용·운영 단위인지 정합니다.
2. 서로 다른 trust 수준의 isolation profile을 두 개 이상 만듭니다.
3. Identity, compute, network, storage, telemetry 격리를 비교합니다.
4. Quota 증가, capacity reserve와 controller fairness를 설계합니다.
5. Tenant 생성·ownership 변경·폐기와 비용 처리를 작성합니다.

필드 이름과 최소 구조는 `contract.json`이 정의합니다. `reference/submission.json`은 Northstar 시나리오의 한 가지 답이며, 자신의 설계가 다른 경우 결과·소유권·실패·증거가 왜 다른지 설명합니다.

## 반드시 다룰 실패

- Namespace가 유일한 isolation 경계입니다.
- Quota를 설정하면 cluster capacity가 자동으로 생깁니다.
- 한 tenant의 reconcile storm이 전체 queue를 막습니다.
- Tenant 삭제 뒤 data와 telemetry retention이 없습니다.

## 검증

```sh
python3 scripts/verify_submission.py \
  exercises/09-multitenancy/contract.json \
  .workspace/09-multitenancy/submission.json
```

검사기는 필수 field, 배열 항목, stable value와 placeholder 부재를 확인합니다. 실제 조직에서 설계가 옳거나 실제 cloud/Kubernetes 동작이 안전하다는 사실은 증명하지 않습니다.

## 완료 근거

- 검사 결과
- 선택한 상태와 책임 경계의 이유
- 자동 검증하지 못한 주장
- 실제 프로젝트에서 다음에 확인할 evidence
- reference와 다른 중요한 결정 및 trade-off
