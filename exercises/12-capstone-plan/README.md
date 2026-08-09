# Internal Developer Platform 통합 설계

## 목표

Product, API, control plane, delivery, runtime, security, tenancy와 운영을 service lifecycle 전체로 통합합니다.

## 먼저 읽을 문서

- [`17-capstone.md`](../../docs/17-capstone.md)

## 시작 상태

`skeleton/submission.json`은 의도적으로 미완성입니다. 원본을 직접 수정하지 말고 `.workspace/`에 복사합니다.

```sh
mkdir -p .workspace/12-capstone-plan
cp exercises/12-capstone-plan/skeleton/submission.json \
  .workspace/12-capstone-plan/submission.json
```

## 수행할 작업

1. 사용자 문제와 비범위를 가진 platform product brief를 작성합니다.
2. 필수 platform resource와 상태·소유권을 정의합니다.
3. 정상·중복·부분 실패·drift·quota·credential·migration·retirement 시나리오를 연결합니다.
4. Journey SLO, capacity, cost, support와 runbook을 포함합니다.
5. 구현하지 않았거나 검증하지 못한 주장을 명시하고 실제 프로젝트 전환 계획을 작성합니다.

필드 이름과 최소 구조는 `contract.json`이 정의합니다. `reference/submission.json`은 Northstar 시나리오의 한 가지 답이며, 자신의 설계가 다른 경우 결과·소유권·실패·증거가 왜 다른지 설명합니다.

## Starter와 회귀 fixture

- `skeleton/submission.json`은 reference와 같은 공개 key·배열·item shape을 보여 주되 모든 학습자 결정은 `TODO` 또는 미완성 값으로 남깁니다. 원본 대신 `.workspace/` 복사본을 수정합니다.
- `reference/submission.json`은 v2 계약을 통과하는 한 가지 완성 예시입니다. 문구를 복사하지 말고 상태·책임·실패·evidence의 차이를 설명합니다.
- `known_bad/submission.json`은 구조와 type은 완성됐지만 의도적으로 한 불변식을 위반합니다: 중복 요청·timeout 시나리오를 제거해 idempotency 증거를 잃습니다. 이 fixture가 통과하면 계약 또는 검증기의 회귀입니다.

## 반드시 다룰 실패

- 도구 아키텍처만 있고 사용자와 lifecycle이 없습니다.
- 모든 상태가 하나의 database 또는 Git에 있다고 표현됩니다.
- 정상 생성만 있고 실패·복구·폐기가 없습니다.
- Local simulation 결과를 production security/reliability 보장으로 표현합니다.

## 검증

```sh
python3 scripts/verify_submission.py \
  exercises/12-capstone-plan/contract.json \
  .workspace/12-capstone-plan/submission.json
```

검증기의 종료 코드는 통과 `0`, 학습자 제출 거부 `1`, 계약·검증 환경 오류 `2`입니다. 자동 검사는 strict JSON, 필수 경로, type, 배열 고유성, 핵심 category와 이 실습의 대표 불변식을 확인합니다.

자동 통과는 실제 조직에서의 타당성이나 cloud/Kubernetes 안전성을 증명하지 않습니다. 사람 검토에서는 선택한 경계의 이유, reference와의 trade-off, 자동화하지 못한 주장, 실제 환경에서 수집할 evidence를 확인합니다.

## 완료 근거

- 검사 결과
- 선택한 상태와 책임 경계의 이유
- 자동 검증하지 못한 주장
- 실제 프로젝트에서 다음에 확인할 evidence
- reference와 다른 중요한 결정 및 trade-off
