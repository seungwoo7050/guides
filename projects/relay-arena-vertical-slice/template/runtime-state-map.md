# Runtime state map

## 식별자

- process/build id:
- frontend world generation:
- arena session generation:
- match id/generation:
- entity stable/runtime id:

## 상태 기계

```text
boot
→ frontend
→ arena loading
→ control-ready
→ playing
→ result pending
→ result committed / abandoned
→ frontend / shutdown
```

각 arrow의 trigger, guard, owner, side effect와 failure state를 작성한다.

## 취소·재시작·suspend

| event | current state | allowed next state | partial state | cleanup owner | evidence |
|---|---|---|---|---|---|
| arena load cancel |  |  |  |  |  |
| match restart |  |  |  |  |  |
| OS suspend |  |  |  |  |  |
| shutdown |  |  |  |  |  |

## stale completion

- generation check:
- cancellation:
- late callback decision:
- subscription cleanup:
