# IaC state·drift·migration 계약

## 목표

IaC configuration, state, external object와 plan/apply/destroy lifecycle의 소유권을 설계합니다.

## 먼저 읽을 문서

- [`04-infrastructure-as-code-state-and-drift.md`](../../docs/04-infrastructure-as-code-state-and-drift.md)

## 시작 상태

`skeleton/submission.json`은 의도적으로 미완성입니다. 원본을 직접 수정하지 말고 `.workspace/`에 복사합니다.

```sh
mkdir -p .workspace/04-iac-state
cp exercises/04-iac-state/skeleton/submission.json \
  .workspace/04-iac-state/submission.json
```

## 수행할 작업

1. State unit과 blast radius를 나눕니다.
2. 각 resource address와 external identity mapping을 정의합니다.
3. Locking, sensitive state와 backup/restore를 명시합니다.
4. Drift 종류별 자동·수동 행동과 owner를 정합니다.
5. Module/state migration과 destroy guardrail을 작성합니다.

필드 이름과 최소 구조는 `contract.json`이 정의합니다. `reference/submission.json`은 Northstar 시나리오의 한 가지 답이며, 자신의 설계가 다른 경우 결과·소유권·실패·증거가 왜 다른지 설명합니다.

## 반드시 다룰 실패

- 모든 환경과 tenant가 하나의 state를 공유합니다.
- Stale plan을 승인 뒤 언제든 적용할 수 있습니다.
- State remove가 실제 resource 삭제라고 가정합니다.
- Out-of-band 변경을 모두 자동 되돌립니다.

## 검증

```sh
python3 scripts/verify_submission.py \
  exercises/04-iac-state/contract.json \
  .workspace/04-iac-state/submission.json
```

검사기는 필수 field, 배열 항목, stable value와 placeholder 부재를 확인합니다. 실제 조직에서 설계가 옳거나 실제 cloud/Kubernetes 동작이 안전하다는 사실은 증명하지 않습니다.

## 완료 근거

- 검사 결과
- 선택한 상태와 책임 경계의 이유
- 자동 검증하지 못한 주장
- 실제 프로젝트에서 다음에 확인할 evidence
- reference와 다른 중요한 결정 및 trade-off
