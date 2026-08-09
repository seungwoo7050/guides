# 플랫폼 계약과 책임 경계

## 목표

Platform capability의 API·상태·외부 효과·지원·삭제 경계와 팀별 single writer를 고정합니다.

## 먼저 읽을 문서

- [`02-platform-contracts-and-ownership.md`](../../docs/02-platform-contracts-and-ownership.md)

## 시작 상태

`skeleton/submission.json`은 의도적으로 미완성입니다. 원본을 직접 수정하지 말고 `.workspace/`에 복사합니다.

```sh
mkdir -p .workspace/02-platform-contract
cp exercises/02-platform-contract/skeleton/submission.json \
  .workspace/02-platform-contract/submission.json
```

## 수행할 작업

1. Capability 이름, version, owner와 support tier를 정의합니다.
2. 요청 identity, validation, idempotency와 승인 조건을 작성합니다.
3. 조건별 의미, 사용자 행동과 failure owner를 구분합니다.
4. 외부 효과마다 writer, external identity, retry와 cleanup을 지정합니다.
5. Application/platform/security/runtime 팀의 책임과 escape hatch를 명시합니다.

필드 이름과 최소 구조는 `contract.json`이 정의합니다. `reference/submission.json`은 Northstar 시나리오의 한 가지 답이며, 자신의 설계가 다른 경우 결과·소유권·실패·증거가 왜 다른지 설명합니다.

## 반드시 다룰 실패

- 모든 실패 owner가 platform team입니다.
- 요청 수락과 실제 Ready가 같은 상태입니다.
- 외부 resource identity 없이 retry합니다.
- 삭제와 partial success 뒤 남는 상태가 없습니다.

## 검증

```sh
python3 scripts/verify_submission.py \
  exercises/02-platform-contract/contract.json \
  .workspace/02-platform-contract/submission.json
```

검사기는 필수 field, 배열 항목, stable value와 placeholder 부재를 확인합니다. 실제 조직에서 설계가 옳거나 실제 cloud/Kubernetes 동작이 안전하다는 사실은 증명하지 않습니다.

## 완료 근거

- 검사 결과
- 선택한 상태와 책임 경계의 이유
- 자동 검증하지 못한 주장
- 실제 프로젝트에서 다음에 확인할 evidence
- reference와 다른 중요한 결정 및 trade-off
