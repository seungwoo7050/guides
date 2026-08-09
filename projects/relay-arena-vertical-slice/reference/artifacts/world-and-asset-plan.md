# World and asset plan — reference exemplar

## world/entity lifecycle

| object | stable id | runtime generation | owner | create/activate | disable/destroy | references |
|---|---|---|---|---|---|---|
| frontend world | frontend | 1 | runtime controller | process start → frontend ready | arena activation or shutdown | process services only; no raw match pointer |
| arena world | `scene.arena.01` | 20 then 21 | arena session | load request → critical closure → control-ready | cancel/abandon → detach → release fence | stable ids/handles tagged with arena generation |
| match | `match-1` | arena/match generation | rules subsystem | control-ready and rules ready | result/abandon/restart | owns player/core/hazard gameplay state |
| player | `p1` | match generation | match/simulation | spawn then command route active | match cleanup | presentation reads snapshots; input submits commands |
| relay core | `core-a|b|c` | match generation | rules subsystem | spawn inactive | match cleanup | interact uses stable target id, not object pointer |
| agent | `agent.chaser` | match generation | match/AI integration | agent/nav gate ready | cancel/world unload | path request carries world generation; idle before ready |

## loading gates

- control-ready: `scene.arena.01`, `player.base`, `rules.arena.default` and transitive dependencies; unique sum `48 CPU / 140 GPU MiB`.
- agent-ready: control union plus `nav.arena.01` and `agent.chaser`; unique sum `75/152 MiB`.
- cosmetic-ready: control union plus `cosmetic.player.gold` and `music.arena.01` closures; headless normal reports `118/202 MiB` because agent gate is separate.
- cancel: close owner generation before detaching world; completion from generation 20 after generation 21 begins is discarded.
- missing optional: control remains ready and presentation degrades. Current headless scenario reports missing `cosmetic.player.gold`, `degraded=true`, `114/164 MiB`; it is a contract fixture, not proof of real GPU allocation.

## memory/loading budget

| target | baseline/scope | critical added | optional/agent added | transient peak | load p95 | decision |
|---|---:|---:|---:|---:|---:|---|
| handheld-low content manifest | scope excludes process baseline | 48/140 MiB | all manifest union reaches 145/214 MiB | not supplied | budget control-ready 4000ms | declared asset set fits 800/400 but timing requires target capture |
| windows-mid content manifest | scope excludes process baseline | 48/140 MiB | all manifest union reaches 145/214 MiB | not supplied | budget control-ready 2200ms | resident declaration fits 1400/800; no measured Windows p95 supplied |
| handheld rc3 total process capture | observed total resident 842 MiB | scope not separable from fixture | peak 1088 MiB | included in peak only | observed 4320ms | total 900/1100 budgets pass memory but control-ready fails 4000ms |

Content-manifest MiB declarations and target-profile process measurements have different scopes; they must not be added or compared as if identical measurements.

## content compatibility

- stable id: manifest ids and `arena-rules@17` are persistent references; runtime handles include generation.
- save/replay/network: record content version with every stable id-bearing artifact.
- rename/remove: require alias/removal migration; unknown critical id blocks, unknown optional id degrades with explicit evidence.
- join: protocol `4` and gameplay-critical content `arena-rules@17` must be compatible before creating player state.

## Evidence and limits

- Normal headless asset evidence: control ready, declared `118/202 MiB`, dependency visits 15, baseline restored.
- Boundary: missing cosmetic stays control-ready and preserves canonical gameplay hash.
- Failure: stale-load rejects one completion, attaches only control closure `48/140 MiB`, and restores baseline.
- Profile proposal: memoization reduces modeled visits `49→23`; moving optional content out of control gate reports modeled `4320→3760ms`.
- Manual review: importer/cook output, actual resident/reference chain, transient peak, release fences, 20-cycle load/unload and target p95 must be captured. The modeled `3760ms` is not a target-device measurement.
