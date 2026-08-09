# Platform journey SLO Template

## 1. Journey

- 이름:
- 사용자:
- 시작 사건:
- 완료 사건:
- 비범위:

## 2. SLI

```text
성공한 유효 요청 / 전체 유효 요청
```

- 분자:
- 분모:
- 측정 source:
- aggregation window:
- latency threshold:

## 3. 실패 분류

| 결과 | SLO 실패 | Owner | 사용자 행동 |
|---|---:|---|---|
| platform defect | 예 | platform | 없음/상태 확인 |
| dependency outage |  |  |  |
| invalid input | 아니요 | user/platform UX | 입력 수정 |
| policy deny | 아니요 | policy/user | remediation/승인 |
| application failure |  |  |  |
| cancellation | 아니요 | user | 없음 |

## 4. 목표

- 목표:
- Window:
- Error budget:
- 제외 조건:
- Support tier:

## 5. Alert

- Fast burn:
- Slow burn:
- Minimum traffic/sample:
- Runbook:
- Owner/on-call:

## 6. Error budget action

- 충분할 때:
- 빠르게 소진될 때:
- 소진됐을 때:
- 계속 허용할 변경:

## 7. Capacity와 dependency

- 처리 단위:
- 현재 capacity:
- Headroom:
- External quota/dependency:
- Admission/rate policy:

## 8. Review

- User outcome과 연결되는가?
- 분모에서 실패를 과도하게 제외하지 않는가?
- Application failure와 platform failure를 구분하는가?
- Alert가 사람이 수행할 행동을 가리키는가?
