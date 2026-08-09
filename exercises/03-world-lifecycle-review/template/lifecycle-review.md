# 월드와 객체 수명 검토 제출

## lifetime scopes

```text
process
→ frontend/world session
→ match generation
→ entity/component
→ frame/event/callback
```

## 위험 edge

| event/edge | 현재 위험 | stale 여부 판정 | 보호할 invariant | 수정 계약 | evidence |
|---|---|---|---|---|---|
|  |  |  |  |  |  |

## unload/cancel 순서

1.
2.
3.

## generation과 handle 정책

- stable id:
- runtime handle:
- generation token:
- cancellation token:
- subscription cleanup:

## 반복 진입 검사

| 측정 | 기준선 | 1회 이탈 | 20회 뒤 | 합격 조건 |
|---|---:|---:|---:|---|
| live entities |  |  |  |  |
| subscriptions |  |  |  |  |
| resident bundles |  |  |  |  |
| async requests |  |  |  |  |
