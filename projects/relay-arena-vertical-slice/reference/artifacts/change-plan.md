# Change plan — reference exemplar

## 목표와 비범위

- player problem: Relay Arena가 frame schedule, load failure, old save와 network fault에서도 같은 authoritative rules를 보존하고 조사 가능한 evidence를 남겨야 한다.
- target requirements: REQ-001 through REQ-012; current release blockers are REQ-004, 006, 009–012.
- in scope: headless public contract, runtime ownership, content gates, save/replay, authority, profile hypotheses and release evidence.
- out of scope: engine renderer/physics internals, real transport/backend, deployment, art quality and AI pathfinding implementation.
- constraints: no source commit/hardware details in release fixture; no timing or platform guarantee may be inferred from headless output.

## review 가능한 구현 순서

| order | issue/change | owner/files/subsystem | dependency | test/evidence | migration/compatibility | rollback |
|---:|---|---|---|---|---|---|
| 1 | freeze public CLI and fixture identities | QA/tools; simulate migrate-save profile | none | reference passes; incomplete starter rejected | schema_version and content/protocol recorded | revert harness/fixture change together |
| 2 | implement fixed simulation and gameplay invariants | gameplay/simulation | order 1 | smooth/jittered/hitch hashes; duplicate/non-owner | command schema and replay format stable | feature disable returns to prior rule version |
| 3 | implement generation-scoped world/assets and presentation events | runtime/content/presentation | order 2 state owners | stale-load; missing-cosmetic; event dedupe | manifest and stable id compatibility | disable optional groups; abandon load safely |
| 4 | implement v1→v2 migration and replay first-divergence | save/QA | order 2 canonical state | 51720ms aliases; corrupt sentinel; mutant tick60 | retain readable previous generation; no silent id loss | choose previous known-good save/build only if compatible |
| 5 | implement authority identities and correction contract | network/gameplay | order 2 command contract | duplicate non-owner stale snapshot result claim | protocol4 and content17 join gate | disable network profile; local offline remains playable |
| 6 | address dependency/profile hotspots without rule changes | performance/content | orders 2–3 | visits49→23; target before/after same workload | content gate change retains stable ids | revert optimization and optional gate config |
| 7 | close platform/accessibility/release blockers | platform/QA/release | all prior orders | rc3+ rerun load save performance cue suspend rollback matrices | exact build/content/save/protocol identity | block release or disable optional feature; no unsafe downgrade |

## cross-discipline handoff

| discipline | input contract | output contract | validation owner | integration risk |
|---|---|---|---|---|
| design | match phases; command preconditions; core/hazard invariant | versioned `arena-rules@17` data | gameplay + content QA | data change can alter replay/save/network semantics |
| art/animation/audio | semantic event ids and optional asset groups | presentation assets with fallback and accessible cue mapping | presentation/accessibility QA | hard reference may enter control gate or cue may duplicate |
| QA | build/content/session fixtures and expected failure | deterministic contract; target/manual evidence | QA automation + platform QA | passing headless result may hide platform failure |
| build/platform | manifest; save/protocol versions; target workload | exact candidate artifact; symbols; profile/storage reports | build/release owner | rollback may be incompatible with new save/content |
| server/data/security | intent/result and bounded event schema | authority decisions and privacy-reviewed telemetry | server/security/data owners | hidden state exposure; duplicate side effect; high cardinality |

## release and follow-up

- feature flag/config: optional cosmetic/agents may degrade; authoritative rules and accessible critical cues cannot be disabled.
- content/code ordering: join/load gates reject incompatible protocol/content before state creation.
- save/protocol impact: migration is forward; downgrade requires explicit compatibility proof.
- rollout: only plan internal/QA/beta after exact-candidate evidence; no external deployment is authorized by this guide.
- rollback trigger: save corruption, duplicate result, desync, target budget regression or inaccessible critical cue.
- post-release review: compare same build/content/workload metrics and investigate first wrong transition, not aggregate success alone.

## Manual review limit

This sequence is implementation-ready but organization owners, engine file paths, target devices, rollout infrastructure and approval authority must be resolved in the real repository. The exemplar does not authorize deployment or mark unknown evidence as pass.
