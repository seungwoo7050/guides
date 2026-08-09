# 플랫폼 upgrade·migration·deprecation

## 목표

Platform API/profile/runtime 변경을 inventory, compatibility, wave, abort와 폐기 계약으로 전달합니다.

## 먼저 읽을 문서

- [`15-upgrades-migrations-and-deprecation.md`](../../docs/15-upgrades-migrations-and-deprecation.md)

## 시작 상태

`skeleton/submission.json`은 의도적으로 미완성입니다. 원본을 직접 수정하지 말고 `.workspace/`에 복사합니다.

```sh
mkdir -p .workspace/11-migration
cp exercises/11-migration/skeleton/submission.json \
  .workspace/11-migration/submission.json
```

## 수행할 작업

1. 변경 component, source/target version과 의미 차이를 정의합니다.
2. 영향 inventory와 compatibility matrix를 작성합니다.
3. Preflight, canary와 migration wave를 정합니다.
4. Abort, rollback 불가능 지점과 forward repair를 구분합니다.
5. Deprecation communication, deadline와 old resource cleanup을 작성합니다.

필드 이름과 최소 구조는 `contract.json`이 정의합니다. `reference/submission.json`은 Northstar 시나리오의 한 가지 답이며, 자신의 설계가 다른 경우 결과·소유권·실패·증거가 왜 다른지 설명합니다.

## 반드시 다룰 실패

- Schema가 호환되므로 의미도 호환된다고 봅니다.
- 대표 workload 없는 빈 cluster만 canary입니다.
- 이전 binary가 새 state를 읽지 못하는데 rollback합니다.
- 공지 뒤 old version 제거를 완료로 봅니다.

## 검증

```sh
python3 scripts/verify_submission.py \
  exercises/11-migration/contract.json \
  .workspace/11-migration/submission.json
```

검사기는 필수 field, 배열 항목, stable value와 placeholder 부재를 확인합니다. 실제 조직에서 설계가 옳거나 실제 cloud/Kubernetes 동작이 안전하다는 사실은 증명하지 않습니다.

## 완료 근거

- 검사 결과
- 선택한 상태와 책임 경계의 이유
- 자동 검증하지 못한 주장
- 실제 프로젝트에서 다음에 확인할 evidence
- reference와 다른 중요한 결정 및 trade-off
