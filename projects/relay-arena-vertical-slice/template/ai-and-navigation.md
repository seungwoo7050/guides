# AI and navigation

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
