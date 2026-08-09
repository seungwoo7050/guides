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

## Starter와 회귀 fixture

- `skeleton/submission.json`은 reference와 같은 공개 key·배열·item shape을 보여 주되 모든 학습자 결정은 `TODO` 또는 미완성 값으로 남깁니다. 원본 대신 `.workspace/` 복사본을 수정합니다.
- `reference/submission.json`은 v2 계약을 통과하는 한 가지 완성 예시입니다. 문구를 복사하지 말고 상태·책임·실패·evidence의 차이를 설명합니다.
- `known_bad/submission.json`은 구조와 type은 완성됐지만 의도적으로 한 불변식을 위반합니다: Ready 상태의 실패 owner까지 platform team으로 두어 책임 경계를 무너뜨립니다. 이 fixture가 통과하면 계약 또는 검증기의 회귀입니다.

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

검증기의 종료 코드는 통과 `0`, 학습자 제출 거부 `1`, 계약·검증 환경 오류 `2`입니다. 자동 검사는 strict JSON, 필수 경로, type, 배열 고유성, 핵심 category와 이 실습의 대표 불변식을 확인합니다.

자동 통과는 실제 조직에서의 타당성이나 cloud/Kubernetes 안전성을 증명하지 않습니다. 사람 검토에서는 선택한 경계의 이유, reference와의 trade-off, 자동화하지 못한 주장, 실제 환경에서 수집할 evidence를 확인합니다.

## 완료 근거

- 검사 결과
- 선택한 상태와 책임 경계의 이유
- 자동 검증하지 못한 주장
- 실제 프로젝트에서 다음에 확인할 evidence
- reference와 다른 중요한 결정 및 trade-off
