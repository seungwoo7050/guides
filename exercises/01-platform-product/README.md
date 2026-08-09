# 플랫폼 제품 문제 정의

## 목표

도구 목록이 아니라 사용자·현재 여정·근거·outcome·guardrail을 가진 첫 platform capability를 정의합니다.

## 먼저 읽을 문서

- [`01-platform-as-product.md`](../../docs/01-platform-as-product.md)

## 시작 상태

`skeleton/submission.json`은 의도적으로 미완성입니다. 원본을 직접 수정하지 말고 `.workspace/`에 복사합니다.

```sh
mkdir -p .workspace/01-platform-product
cp exercises/01-platform-product/skeleton/submission.json \
  .workspace/01-platform-product/submission.json
```

## 수행할 작업

1. 서로 다른 두 명 이상의 platform 사용자를 식별합니다.
2. 현재 journey의 handoff, wait와 failure를 단계별로 기록합니다.
3. 관찰·인터뷰·incident·ticket 중 확인 가능한 evidence를 연결합니다.
4. outcome metric과 함께 품질·보안 guardrail을 둡니다.
5. 첫 capability와 의도적인 비범위를 정합니다.

필드 이름과 최소 구조는 `contract.json`이 정의합니다. `reference/submission.json`은 Northstar 시나리오의 한 가지 답이며, 자신의 설계가 다른 경우 결과·소유권·실패·증거가 왜 다른지 설명합니다.

## Starter와 회귀 fixture

- `skeleton/submission.json`은 reference와 같은 공개 key·배열·item shape을 보여 주되 모든 학습자 결정은 `TODO` 또는 미완성 값으로 남깁니다. 원본 대신 `.workspace/` 복사본을 수정합니다.
- `reference/submission.json`은 v2 계약을 통과하는 한 가지 완성 예시입니다. 문구를 복사하지 말고 상태·책임·실패·evidence의 차이를 설명합니다.
- `known_bad/submission.json`은 구조와 type은 완성됐지만 의도적으로 한 불변식을 위반합니다: platform operator 관점을 제거해 사용자·운영 책임의 구분을 잃습니다. 이 fixture가 통과하면 계약 또는 검증기의 회귀입니다.

## 반드시 다룰 실패

- Kubernetes 또는 portal 도입 자체가 목표입니다.
- 사용자와 증거 없이 platform team의 추측만 기록합니다.
- 채택률만 outcome으로 두고 전달 품질과 support cost를 무시합니다.
- 첫 capability가 전체 플랫폼 재구축처럼 너무 큽니다.

## 검증

```sh
python3 scripts/verify_submission.py \
  exercises/01-platform-product/contract.json \
  .workspace/01-platform-product/submission.json
```

검증기의 종료 코드는 통과 `0`, 학습자 제출 거부 `1`, 계약·검증 환경 오류 `2`입니다. 자동 검사는 strict JSON, 필수 경로, type, 배열 고유성, 핵심 category와 이 실습의 대표 불변식을 확인합니다.

자동 통과는 실제 조직에서의 타당성이나 cloud/Kubernetes 안전성을 증명하지 않습니다. 사람 검토에서는 선택한 경계의 이유, reference와의 trade-off, 자동화하지 못한 주장, 실제 환경에서 수집할 evidence를 확인합니다.

## 완료 근거

- 검사 결과
- 선택한 상태와 책임 경계의 이유
- 자동 검증하지 못한 주장
- 실제 프로젝트에서 다음에 확인할 evidence
- reference와 다른 중요한 결정 및 trade-off
