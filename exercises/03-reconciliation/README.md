# Reconciliation 상태 기계

## 목표

Desired/observed state, generation, condition, idempotent step와 finalizer를 가진 controller 설계를 만듭니다.

## 먼저 읽을 문서

- [`03-control-planes-and-reconciliation.md`](../../docs/03-control-planes-and-reconciliation.md)

## 시작 상태

`skeleton/submission.json`은 의도적으로 미완성입니다. 원본을 직접 수정하지 말고 `.workspace/`에 복사합니다.

```sh
mkdir -p .workspace/03-reconciliation
cp exercises/03-reconciliation/skeleton/submission.json \
  .workspace/03-reconciliation/submission.json
```

## 수행할 작업

1. Resource spec, observed state와 current generation을 분리합니다.
2. Reconcile 단계마다 idempotency key와 evidence를 정합니다.
3. Retryable, terminal, blocked와 degraded failure를 구분합니다.
4. 여러 controller의 field ownership을 지정합니다.
5. 삭제 시 finalizer와 orphan 검사를 설계합니다.

필드 이름과 최소 구조는 `contract.json`이 정의합니다. `reference/submission.json`은 Northstar 시나리오의 한 가지 답이며, 자신의 설계가 다른 경우 결과·소유권·실패·증거가 왜 다른지 설명합니다.

## 반드시 다룰 실패

- Controller가 성공했다고 기록하면 Ready입니다.
- Retry가 외부 resource를 중복 생성합니다.
- 하나의 poison resource가 전체 queue를 멈춥니다.
- Finalizer를 지우면 외부 resource도 사라진다고 가정합니다.

## 검증

```sh
python3 scripts/verify_submission.py \
  exercises/03-reconciliation/contract.json \
  .workspace/03-reconciliation/submission.json
```

검사기는 필수 field, 배열 항목, stable value와 placeholder 부재를 확인합니다. 실제 조직에서 설계가 옳거나 실제 cloud/Kubernetes 동작이 안전하다는 사실은 증명하지 않습니다.

## 완료 근거

- 검사 결과
- 선택한 상태와 책임 경계의 이유
- 자동 검증하지 못한 주장
- 실제 프로젝트에서 다음에 확인할 evidence
- reference와 다른 중요한 결정 및 trade-off
