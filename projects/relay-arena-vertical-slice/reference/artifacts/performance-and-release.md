# Performance and release — reference exemplar

## target and workload

- hardware/OS: `handheld-low`; exact model/OS version are absent and must be added to final capture.
- resolution/power/thermal: workload says warm and medium quality; resolution, refresh and power mode are not supplied in this Capstone profile.
- build/content: `relay-client@1.0.0-rc3`, `arena-rules@17`.
- scene/workload: 90 seconds, 12 agents, 24 hazards, medium quality.
- capture limitation: sample count, p95 method and raw trace are not included; observed summary cannot be independently recalculated.

## budgets and evidence

| metric | budget | observed | percentile/marker | pass | next action |
|---|---:|---:|---|---|---|
| frame p95 | 16.67ms | 18.4ms | warm representative arena | no | reproduce marker and rerun same target after fix |
| frame p99 | 25.0ms | 31.0ms | warm representative arena | no | separate checkpoint/streaming spikes |
| worst hitch | 50.0ms | 58.0ms | candidate cause checkpoint serialization | no | move/bound serialization work and capture first wrong frame |
| resident memory | 900MiB | 842MiB | total process scope | yes with 58MiB headroom | soak/restart and scope breakdown |
| peak memory | 1100MiB | 1088MiB | transition peak | yes with 12MiB headroom | transient breakdown and low-memory failure injection |
| control-ready p95 | 4000ms | 4320ms | candidate stale optional dependency | no | verify gate graph and target cold runs |

The headless `profile` command reports a proposed comparison: dependency visits `49→23`, frame p95 `18.4→16.2`, control-ready p95 `4320→3760`, with invariants preserved. Only the deterministic visit count is executable evidence; the improved timing values are modeled expectations and require target-device remeasurement.

## scalability

| tier | target | changes | preserved rule/accessibility | expected budget |
|---|---|---|---|---|
| low | handheld-low | critical control assets first; nav/agents late; optional music/cosmetic degraded; lower-cost presentation if validated | all three cores/hazard fairness; remap; subtitles/non-color cue | <=16.67ms p95; <=4000ms control-ready; <=900/1100MiB |
| medium | windows-mid/default handheld when measured | default agents and presentation; optional still outside control gate | identical command/rule/save/replay schema | target-specific capture required; no Windows observed value supplied |
| high | capable desktop | higher cosmetic/VFX/audio quality only | no extra gameplay information or authority difference | separate declared target and profile required |

## platform/accessibility gates

- remap/toggle/dead zone: REQ-001 has pass evidence for remap, but CLI begins after action mapping; device matrix remains manual.
- subtitles/non-color cues: REQ-011 evidence is `unknown`; block until review attached to rc3 or later exact candidate.
- focus/controller/suspend: REQ-003 needs target focus/device injection; REQ-012 suspend result commit is currently `fail`.
- localization/layout: no evidence supplied; add target locale/text scale/safe area capture.
- storage/quota/cloud: corrupt local migration is tested, but quota/cloud/suspend durability are not.

## release decision

- candidate identities: client rc3, server rc3, content `arena-rules@17`; save v2 and protocol 4 from contracts. Source commit/artifact hash is missing.
- pass evidence: rules, input remap, replay, network authority.
- stale/unknown/fail: load cancel unknown; save evidence stale on rc2; handheld profile fail; accessibility unknown; suspend result commit fail.
- decision: **block**. Unknown/stale are not pass, and REQ-009/010/011/012 are release-critical.
- rollback/feature disable: optional cosmetic/agent gate may be disabled without changing rules; save/protocol downgrade compatibility must be proven before executable rollback.
- post-release telemetry: exact build/content/session, frame/load percentiles, migration result, duplicate commit and authority rejection with bounded/privacy-reviewed fields.

## Manual approval conditions

Rerun on the exact candidate after fixes: target performance raw captures, 20-cycle load/cancel baseline, save v1 matrix, corrupt/quota/suspend commit tests, remap/focus/controller matrix, subtitle/non-color review, and rollback compatibility. A passing headless contract is necessary regression evidence but cannot change this block decision.
