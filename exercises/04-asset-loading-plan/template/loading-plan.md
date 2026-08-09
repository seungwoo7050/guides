# 자산 loading 계획 제출

## identity와 pipeline

```text
source file
→ imported artifact
→ stable logical asset id
→ cooked package/bundle
→ runtime handle
→ resident resource
```

## load graph와 gate

- control-ready:
- agent-ready:
- cosmetic-ready:
- background/preload:
- optional fallback:

## scenario별 계획

| scenario | critical path | defer/skip | peak transient | cancellation cleanup | player-visible result |
|---|---|---|---|---|---|
| cold-entry |  |  |  |  |  |
| cancel-at-40ms |  |  |  |  |  |
| low-memory-entry |  |  |  |  |  |
| missing-cosmetic |  |  |  |  |  |

## async completion 계약

- request identity:
- owner generation:
- cancel:
- stale completion:
- release fence/deferred destruction:

## content compatibility

- stable id rename/removal:
- save/replay content version:
- network join manifest:
