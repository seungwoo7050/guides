# Gameplay rules — reference exemplar

## match state machine

| phase | enter trigger | allowed commands | exit trigger | durable side effect | invariant |
|---|---|---|---|---|---|
| loading | arena generation and critical request created | none | critical rules/world/player ready | none | gameplay state is not writable before ready |
| countdown | control-ready and match created | Pause/system only | countdown completes | none | fixed gameplay clock policy is explicit |
| playing | countdown complete | Move, Dash, Interact | all three cores active or abandon | none yet | active count equals unique active ids |
| result_pending | third unique core activation | no gameplay mutation | idempotent profile commit succeeds/fails | commit intent only | one result id per match |
| result_committed | `match-1` stored | no gameplay command | frontend/restart | best time and result id | durable result changes at most once |
| abandoned | cancel/disconnect/shutdown policy | none | cleanup/frontend | no result grant | partial match never grants result |

The headless reference starts directly in `playing`; other phases remain lifecycle contracts to map in an engine integration.

## command decisions

| command | precondition | accepted transition/event | reject reason | idempotency |
|---|---|---|---|---|
| Move | p1 owner, playing, integer axes within ±1000 | replace move intent for fixed simulation | `non_owner`, `duplicate_or_stale`, `phase`, `invalid_axis` | `(player,sequence)` accepted once |
| Dash | Move preconditions + `pressed=true`, cooldown zero, nonzero move | add 3000 milli displacement; set cooldown 8 | `dash_precondition` plus common reasons | same sequence cannot move twice |
| Interact | p1 owner, playing, target in core a/b/c and not active | add core id; emit deduped core event | `interact_precondition` plus common reasons | unique command sequence and unique active core set |

Normal fixture accepts six commands: move tick 1, dash 4, core-a 12, move 30, core-b 45 and core-c 70. At tick 70 the third activation commits `match-1`; final tick-90 state has all cores, `best_time_ms=1166`, and canonical hash `08b46cfd…6d0e`.

## progression commit

- result identity: stable match id `match-1`; runtime generation remains separate.
- best-time compare: candidate is fixed simulation time; update only after durable result commit. Existing non-null best time should use the better value according to the product rule.
- durable owner: profile/save subsystem, not result UI or presentation event.
- duplicate/suspend retry: `result_commit_ids` is a set/idempotency ledger. Events 19 and 21 retry the same generation/result identity.
- UI notification: consume `match-1:result` only after authoritative commit and dedupe by event id.

## Evidence and limits

- Normal: accepted command count 6; core events at ticks 12, 45, 70; result event once.
- Boundary: smooth/jittered/hitch produce the same final canonical hash.
- Failure: duplicate sequence 3 is rejected without hash change; p2 sequence 99 is `non_owner`; network trace rejects duplicate/stale/result claim.
- Manual review: collision range, hazard checkpoint reset, countdown/pause and storage-backed best-time comparison are not modeled by the headless rule. Release evidence still reports suspend-result commit failure, so CLI idempotency alone cannot ship REQ-012.
