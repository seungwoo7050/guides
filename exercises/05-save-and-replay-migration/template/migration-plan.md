# save migration 계획 제출

## envelope validation

- format:
- checksum:
- supported version:
- newer version rejection:
- original generation retention:

## v1 → v2 field mapping

| v1 field | v2 field | conversion | default/fallback | invariant | failure action |
|---|---|---|---|---|---|
| bestTimeSeconds |  |  |  |  |  |
| unlockedSkins |  |  |  |  |  |
| input |  |  |  |  |  |
| audio |  |  |  |  |  |

## atomic commit

```text
read
→ validate
→ decode v1
→ migrate
→ validate v2 invariants
→ write temporary
→ verify
→ replace
→ retain/expire previous generation
```

## compatibility matrix

| input | expected | user-visible action | evidence |
|---|---|---|---|
| valid v1 |  |  |  |
| valid v2 |  |  |  |
| v3/newer |  |  |  |
| checksum mismatch |  |  |  |
| unknown cosmetic id |  |  |  |
| storage full during write |  |  |  |
