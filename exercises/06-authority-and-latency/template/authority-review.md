# authority와 latency 검토 제출

## authority table

| state/result | proposed by | validated by | authoritative writer | replicated to | local prediction | correction |
|---|---|---|---|---|---|---|
| player movement |  |  |  |  |  |  |
| core activation |  |  |  |  |  |  |
| match result |  |  |  |  |  |  |

## trace finding

| event index | finding | violated invariant | server decision | client UX | evidence |
|---:|---|---|---|---|---|
|  |  |  |  |  |  |

## sequence와 stale 정책

- session identity:
- command idempotency key:
- accepted tick window:
- snapshot monotonicity:
- reconnect generation:

## prediction/correction

- predicted state:
- non-predicted state:
- rollback/resimulation:
- presentation one-shot suppression:
- correction visibility policy:

## compatibility gate

- protocol:
- content:
- build/capability:
- actionable rejection:
