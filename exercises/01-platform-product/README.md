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

검사기는 필수 field, 배열 항목, stable value와 placeholder 부재를 확인합니다. 실제 조직에서 설계가 옳거나 실제 cloud/Kubernetes 동작이 안전하다는 사실은 증명하지 않습니다.

## 완료 근거

- 검사 결과
- 선택한 상태와 책임 경계의 이유
- 자동 검증하지 못한 주장
- 실제 프로젝트에서 다음에 확인할 evidence
- reference와 다른 중요한 결정 및 trade-off
