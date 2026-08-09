# Authority and latency — reference exemplar

## authority table

| state/result | client proposal | server validation | authoritative writer | prediction | correction | replication |
|---|---|---|---|---|---|---|
| player movement | owner submits Move intent | ownership, sequence, tick window, axis/rule | server in network profile | owning client may predict | snapshot + ack, rewind/resim | relevant clients |
| dash cooldown | owner submits Dash intent | owner, phase, cooldown, movement | server | owner may predict | authoritative cooldown/tick | owner and observers as needed |
| core activation | owner submits target intent | phase, range, inactive target | server | no rule prediction; pending UI only | rejected pending clears; accepted event projects | all match clients |
| match result | no direct client result claim | three-core invariant + idempotency | server/profile commit owner | none | authoritative result replaces pending view | all clients/result service |

## command/snapshot identity

- session/content/protocol: `relay-match-500`, `arena-rules@17`, protocol `4`.
- ownership: `client-a→p1`, `client-b→p2`.
- command identity: `(session, source client, sequence)` plus player/tick/payload consistency.
- trace findings: client-b command for p1 is `non_owner`; repeated p1 sequence 11 is `duplicate`.
- snapshot: accept sequence 52/tick101; discard sequence 51/tick99 as `stale_snapshot`.
- client result claim: reject; only server rules write result.
- reconnect generation: establish new connection epoch, snapshot and ack before applying new commands; old-epoch history cannot mutate the new session.

## fault matrix summary

| fault | expected authoritative behavior | player/presentation behavior | evidence/limit |
|---|---|---|---|
| latency 100ms, jitter 40ms | bounded command window and ordered simulation | prediction or explicit delay; no result prediction | values declared in fixture, transport not simulated |
| loss 5% | retry/idempotency without duplicate side effect | temporary interpolation/pending | headless checks duplicate semantics only |
| reorder 3% | monotonic snapshot sequence | never regress to snapshot 51 | authority report contains `stale_snapshot` |
| duplicate 1% | one identity processed once | no duplicate core/result cue | report contains `duplicate`; local duplicate scenario hash unchanged |
| non-owner | reject and preserve state | actionable denial, no cue | report/local scenario contain `non_owner` |
| incompatible content/protocol | reject before player state | update/compatibility message | join handshake not implemented by headless CLI |

## Evidence and limits

The headless authority report accepts two unique command identities and reports exactly `client_result_claim`, `duplicate`, `non_owner`, and `stale_snapshot`. The local `non-owner` scenario rejects p2 sequence 99 without changing canonical state. It does not transmit packets, implement server/client processes, prediction history, encryption, reconnect or bandwidth; those require multi-instance tests using the declared fault profile and human UX review.
