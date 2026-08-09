# Artifact promotion과 GitOps

## 목표

Source에서 artifact, environment promotion, Git desired state와 live reconciliation을 추적 가능한 release로 연결합니다.

## 먼저 읽을 문서

- [`09-delivery-platform-and-artifact-promotion.md`](../../docs/09-delivery-platform-and-artifact-promotion.md)
- [`10-gitops-reconciliation-and-emergency-changes.md`](../../docs/10-gitops-reconciliation-and-emergency-changes.md)

## 시작 상태

`skeleton/submission.json`은 의도적으로 미완성입니다. 원본을 직접 수정하지 말고 `.workspace/`에 복사합니다.

```sh
mkdir -p .workspace/07-delivery-gitops
cp exercises/07-delivery-gitops/skeleton/submission.json \
  .workspace/07-delivery-gitops/submission.json
```

## 수행할 작업

1. Build input, artifact digest와 evidence bundle을 연결합니다.
2. Untrusted validation, trusted build와 deployment identity를 분리합니다.
3. 환경별 promotion gate와 rollback/roll-forward 조건을 정합니다.
4. Git desired state, controller observed revision과 drift 정책을 작성합니다.
5. Prune와 break-glass의 시작·종료를 설계합니다.

필드 이름과 최소 구조는 `contract.json`이 정의합니다. `reference/submission.json`은 Northstar 시나리오의 한 가지 답이며, 자신의 설계가 다른 경우 결과·소유권·실패·증거가 왜 다른지 설명합니다.

## 반드시 다룰 실패

- 환경마다 같은 source를 다시 build합니다.
- Build credential이 production 배포 admin입니다.
- Git commit이 있으면 deployment Ready라고 판단합니다.
- 긴급 live 변경이 Git에 반영되지 않거나 controller에 즉시 되돌아갑니다.

## 검증

```sh
python3 scripts/verify_submission.py \
  exercises/07-delivery-gitops/contract.json \
  .workspace/07-delivery-gitops/submission.json
```

검사기는 필수 field, 배열 항목, stable value와 placeholder 부재를 확인합니다. 실제 조직에서 설계가 옳거나 실제 cloud/Kubernetes 동작이 안전하다는 사실은 증명하지 않습니다.

## 완료 근거

- 검사 결과
- 선택한 상태와 책임 경계의 이유
- 자동 검증하지 못한 주장
- 실제 프로젝트에서 다음에 확인할 evidence
- reference와 다른 중요한 결정 및 trade-off
