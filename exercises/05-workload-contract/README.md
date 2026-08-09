# Kubernetes workload 계약

## 목표

Application workload와 platform runtime 사이의 readiness, resource, network, storage, scheduling과 disruption 책임을 정의합니다.

## 먼저 읽을 문서

- [`05-kubernetes-api-workloads-and-controllers.md`](../../docs/05-kubernetes-api-workloads-and-controllers.md)
- [`06-kubernetes-network-storage-and-scheduling.md`](../../docs/06-kubernetes-network-storage-and-scheduling.md)

## 시작 상태

`skeleton/submission.json`은 의도적으로 미완성입니다. 원본을 직접 수정하지 말고 `.workspace/`에 복사합니다.

```sh
mkdir -p .workspace/05-workload-contract
cp exercises/05-workload-contract/skeleton/submission.json \
  .workspace/05-workload-contract/submission.json
```

## 수행할 작업

1. Workload 종류와 platform profile을 지정합니다.
2. Readiness/liveness/startup/termination의 의미를 구분합니다.
3. Resource request·limit와 scheduling 제약을 정합니다.
4. Ingress/egress, identity, storage lifecycle을 정의합니다.
5. Disruption과 rollout 중 허용할 unavailable을 명시합니다.

필드 이름과 최소 구조는 `contract.json`이 정의합니다. `reference/submission.json`은 Northstar 시나리오의 한 가지 답이며, 자신의 설계가 다른 경우 결과·소유권·실패·증거가 왜 다른지 설명합니다.

## 반드시 다룰 실패

- 프로세스가 실행 중이면 Ready입니다.
- Resource limit만 있고 request와 capacity 모델이 없습니다.
- Namespace가 모든 network와 data isolation을 자동 제공합니다.
- PDB가 replica와 capacity가 없어도 availability를 보장합니다.

## 검증

```sh
python3 scripts/verify_submission.py \
  exercises/05-workload-contract/contract.json \
  .workspace/05-workload-contract/submission.json
```

검사기는 필수 field, 배열 항목, stable value와 placeholder 부재를 확인합니다. 실제 조직에서 설계가 옳거나 실제 cloud/Kubernetes 동작이 안전하다는 사실은 증명하지 않습니다.

## 완료 근거

- 검사 결과
- 선택한 상태와 책임 경계의 이유
- 자동 검증하지 못한 주장
- 실제 프로젝트에서 다음에 확인할 evidence
- reference와 다른 중요한 결정 및 trade-off
