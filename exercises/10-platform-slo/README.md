# Platform SLO·capacity·support

## 목표

Component health가 아니라 사용자 여정에 기반한 SLO, 관측 identity, capacity와 support 계약을 만듭니다.

## 먼저 읽을 문서

- [`12-observability-audit-and-developer-feedback.md`](../../docs/12-observability-audit-and-developer-feedback.md)
- [`14-platform-slo-capacity-cost-and-support.md`](../../docs/14-platform-slo-capacity-cost-and-support.md)

## 시작 상태

`skeleton/submission.json`은 의도적으로 미완성입니다. 원본을 직접 수정하지 말고 `.workspace/`에 복사합니다.

```sh
mkdir -p .workspace/10-platform-slo
cp exercises/10-platform-slo/skeleton/submission.json \
  .workspace/10-platform-slo/submission.json
```

## 수행할 작업

1. 두 개 이상의 platform journey와 시작·성공 사건을 정의합니다.
2. Platform/user/application/dependency failure를 분류합니다.
3. Trace·metric·log·audit identity를 연결합니다.
4. Fast/slow burn alert와 error-budget 행동을 작성합니다.
5. Capacity headroom, admission, support tier와 cost model을 정합니다.

필드 이름과 최소 구조는 `contract.json`이 정의합니다. `reference/submission.json`은 Northstar 시나리오의 한 가지 답이며, 자신의 설계가 다른 경우 결과·소유권·실패·증거가 왜 다른지 설명합니다.

## 반드시 다룰 실패

- API server uptime이 모든 platform SLO입니다.
- Invalid input을 제외하지만 반복 입력 오류를 개선하지 않습니다.
- 무한 queue로 capacity 부족을 숨깁니다.
- 모든 capability가 24시간 같은 지원 수준입니다.

## 검증

```sh
python3 scripts/verify_submission.py \
  exercises/10-platform-slo/contract.json \
  .workspace/10-platform-slo/submission.json
```

검사기는 필수 field, 배열 항목, stable value와 placeholder 부재를 확인합니다. 실제 조직에서 설계가 옳거나 실제 cloud/Kubernetes 동작이 안전하다는 사실은 증명하지 않습니다.

## 완료 근거

- 검사 결과
- 선택한 상태와 책임 경계의 이유
- 자동 검증하지 못한 주장
- 실제 프로젝트에서 다음에 확인할 evidence
- reference와 다른 중요한 결정 및 trade-off
