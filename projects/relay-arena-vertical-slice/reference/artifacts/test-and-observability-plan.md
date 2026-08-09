# Test and observability plan — reference exemplar

## test layers

| layer | state/contract | normal | boundary | failure | deterministic fixture |
|---|---|---|---|---|---|
| pure rules | command acceptance and core/result invariants | six fixture commands commit match once | repeated/unknown target and phase edge | non-owner; duplicate/stale; invalid axis/precondition | `gameplay-rules.json` + CLI `apply_command` |
| fixed simulation | frame schedule independent canonical state | smooth tick 90 hash | jittered max two steps | hitch max four and drops backlog | `replay-trace.json`; smooth/jittered/hitch |
| world/lifecycle | generation and resource owner | control closure attaches and exits | missing cosmetic degrades | stale generation completion discarded | `runtime-events.json`; scenarios `missing-cosmetic`, `stale-load` |
| save/replay | versioned migration and first divergence | v1→v2 yields 51720ms | known-bad sequence 5 differs at checkpoint 60 | corrupt JSON and unknown id do not publish | save fixtures + replay mutant |
| network | intent/authority/ordering | two unique owner identities accepted | latency/loss/reorder profile | non-owner; duplicate; stale snapshot; result claim | `network-session.json`; authority report |
| platform/release | target evidence and durable lifecycle | exact rc3 evidence only | remap/suspend/storage/device matrix | profile and suspend failures; unknown accessibility | `target-profile.json`, `release-evidence.json`; target/manual rerun |

## trace identity

- build/content: client `relay-client@1.0.0-rc3`, server `relay-server@1.0.0-rc3`, content/rules `arena-rules@17`.
- session/match: `relay-match-500`, canonical local match `match-1`.
- world/match generation: runtime generation 20 then 21.
- simulation: fixed step `16667us`, tick, player and command sequence.
- save/replay/protocol: save v1→v2, replay format from fixture, protocol `4`.
- source caveat: release fixture has no source commit/artifact hash; final evidence must add it rather than infer one.

## structured events

| event | required fields | privacy/volume | retention | investigation question |
|---|---|---|---|---|
| simulation_frame | build; session; frame delta; steps; first/last tick; dropped us | sampled; no raw user data | bounded profile/repro bundle | did overload change command order or only wall-time UX? |
| command_decision | match; player pseudonymous id; tick; sequence; kind; decision reason | avoid device text/account id; bounded per debug session | short diagnostic/replay window | what is the first rejected or wrongly accepted command? |
| runtime_transition | generation; from/to; request; result; duration | low cardinality state names | release diagnostic window | did generation 20 callback mutate generation 21? |
| asset_completion | manifest; asset stable id; request/owner generation; bytes; result | asset ids bounded by manifest | profile/repro bundle | was optional content on the critical gate or stale? |
| presentation_event | match; event id; kind; target; dedupe decision | no raw content/user text | bounded around correction/replay | did rollback replay a one-shot? |
| save_migration | format; from/to version; profile pseudonym; stage; result | never log payload/binding text beyond category | security-approved diagnostic | which atomic stage failed and was old data preserved? |
| authority_rejection | session; source role; player; sequence/snapshot; reason | pseudonymize player/client; rate limit | bounded anti-abuse/repro window | non-owner; duplicate; stale or invalid result? |

## known-bad/meta-test

- incomplete starter: run public contract with `--expect incomplete`; it must be rejected, not reported as completion.
- duplicate mutant: append sequence 3; expected `duplicate_or_stale` and unchanged canonical hash.
- authority mutants: p2 command, duplicate network identity, snapshot 51 after 52 and client result claim all appear in rejection set.
- resource mutants: stale request generation produces exactly one rejection and missing cosmetic remains control-ready/degraded.
- replay mutant: sequence 5 changed to `core-missing`; first divergent checkpoint must be 60.
- save mutant: corrupt input must fail and leave a pre-existing sentinel output unchanged.
- profile evidence: modeled dependency visits must decrease `49→23` while `invariants_preserved=true`.

## Evidence and manual-review limits

The black-box contract checks the reference CLI and rejects the starter. It does not certify engine callbacks, collision, actual GPU allocation, network transport, platform storage, accessibility or target timings. Those require packaged-build tests, fault injection and human review. Retry must not turn unavailable target checks into pass.
