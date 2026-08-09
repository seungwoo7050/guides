# Self-service API와 golden path

## 목표

Portal 없이도 자동화 가능한 platform API, catalog와 생성부터 폐기까지의 golden path를 설계합니다.

## 먼저 읽을 문서

- [`07-self-service-platform-apis-and-catalogs.md`](../../docs/07-self-service-platform-apis-and-catalogs.md)
- [`08-golden-paths-and-service-lifecycle.md`](../../docs/08-golden-paths-and-service-lifecycle.md)

## 시작 상태

`skeleton/submission.json`은 의도적으로 미완성입니다. 원본을 직접 수정하지 말고 `.workspace/`에 복사합니다.

```sh
mkdir -p .workspace/06-self-service
cp exercises/06-self-service/skeleton/submission.json \
  .workspace/06-self-service/submission.json
```

## 수행할 작업

1. Versioned API request, 202 response와 status resource를 정의합니다.
2. Stable condition과 actionable error taxonomy를 작성합니다.
3. Catalog metadata의 정본과 runtime 상태 source를 분리합니다.
4. Profile version, template 이후 update와 escape hatch를 정합니다.
5. Service retirement와 orphan/credential/data 처리를 작성합니다.

필드 이름과 최소 구조는 `contract.json`이 정의합니다. `reference/submission.json`은 Northstar 시나리오의 한 가지 답이며, 자신의 설계가 다른 경우 결과·소유권·실패·증거가 왜 다른지 설명합니다.

## 반드시 다룰 실패

- Portal form이 ticket을 만들 뿐 API 상태가 없습니다.
- Template 생성 뒤 기존 서비스 update 경로가 없습니다.
- 오류가 internal error 하나로 표현됩니다.
- 생성만 자동이고 폐기는 수동입니다.

## 검증

```sh
python3 scripts/verify_submission.py \
  exercises/06-self-service/contract.json \
  .workspace/06-self-service/submission.json
```

검사기는 필수 field, 배열 항목, stable value와 placeholder 부재를 확인합니다. 실제 조직에서 설계가 옳거나 실제 cloud/Kubernetes 동작이 안전하다는 사실은 증명하지 않습니다.

## 완료 근거

- 검사 결과
- 선택한 상태와 책임 경계의 이유
- 자동 검증하지 못한 주장
- 실제 프로젝트에서 다음에 확인할 evidence
- reference와 다른 중요한 결정 및 trade-off
