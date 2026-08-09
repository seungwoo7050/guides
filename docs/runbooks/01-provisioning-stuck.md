# Provisioning stuck

## 증상

- `Progressing` condition이 목표 시간보다 오래 유지됩니다.
- Operation queue age가 증가합니다.
- 일부 dependency는 생성됐지만 최종 `Ready`가 되지 않습니다.
- 사용자가 같은 요청을 반복 제출합니다.

## 먼저 확인할 영향

- 하나의 resource인가, tenant/region/profile 전체인가?
- 기존 workload에는 영향이 없고 새 생성만 막혔는가?
- production 변경도 막혔는가?
- 비용이 발생하는 부분 resource가 계속 생성되는가?

## 고정할 식별자

```text
request_id
operation_id
resource_id
generation
tenant/profile/region
controller version
```

## 검사 순서

1. Resource의 desired spec, observed generation과 condition history를 봅니다.
2. 마지막 성공 단계와 현재 blocked dependency를 찾습니다.
3. Controller queue, retry count와 next retry를 확인합니다.
4. 입력 오류·policy·quota·provider timeout·controller defect를 분류합니다.
5. 같은 idempotency key의 중복 operation이 있는지 확인합니다.
6. 외부 resource가 이미 생성됐지만 status write만 실패했는지 확인합니다.
7. 최근 platform release, policy와 provider incident를 비교합니다.

## 가설별 근거

| 가설 | 확인할 근거 |
|---|---|
| policy blocked | stable deny code, policy version, exception 상태 |
| quota/capacity | tenant usage, provider quota, queue admission |
| external timeout | provider operation ID, 실제 resource state |
| controller retry loop | 같은 error, retry budget, poison resource 여부 |
| status stale | external state와 observed generation 불일치 |
| dependency cycle | resource graph와 unmet condition |

## 안전한 완화

- Retry 가능한 dependency 오류면 backoff와 queue priority를 조정합니다.
- Poison resource가 전체 queue를 막으면 해당 resource를 `Blocked`로 격리합니다.
- Provider operation이 완료됐다면 새 resource를 만들지 말고 import/adopt 또는 status 복구를 검토합니다.
- 대량 요청이면 신규 low-priority admission을 제한합니다.
- Controller release 결함이면 canary 중단과 이전 version 복구를 검토합니다.

다음은 먼저 하지 않습니다.

- 상태를 확인하지 않고 같은 요청을 새 이름으로 반복합니다.
- IaC state 또는 finalizer를 바로 삭제합니다.
- 부분 resource를 무조건 수동 제거합니다.
- 전체 controller queue를 재시작해 증거를 잃습니다.

## 복구 판정

- Original resource의 같은 generation이 terminal condition에 도달합니다.
- 중복 resource와 orphan가 없습니다.
- External smoke 또는 capability별 완료 검사가 통과합니다.
- Queue age와 retry rate가 정상화됩니다.
- 사용자가 status와 결과를 조회할 수 있습니다.
- 임시 pause·priority·exception이 제거됩니다.

## 후속 action

- 실패 분류와 사용자 message 개선
- dependency timeout/budget 조정
- orphan detection
- idempotency fixture
- queue fairness
- 관련 SLO와 alert
