# 선택 산출물: AI and navigation

이 파일은 Profile A의 필수 13개 제출 파일에 포함되지 않는 선택 심화입니다. 작성하지 않아도 필수 산출물 수와 Capstone 완료 계약은 바뀌지 않습니다.

## agent contract

```text
sense snapshot
→ decision/behavior state
→ path request
→ movement command/intention
→ world validation
→ presentation
```

## state and lifetime

| state/request | owner | clock/tick | generation | cancellation | fallback |
|---|---|---|---|---|---|
| perception snapshot |  |  |  |  |  |
| behavior state |  |  |  |  |  |
| path request |  |  |  |  |  |
| path result |  |  |  |  |  |

## failure policy

- navigation not ready:
- world/target unloaded:
- stale path result:
- CPU budget exceeded:
- deterministic replay scope:
