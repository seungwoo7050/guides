# Existing project boundary recovery — reference evidence

이 문서는 headless Relay Arena가 보여 주는 작은 공개 경계를 사용해 낯선 엔진 프로젝트의 update, render/presentation, asset과 tool 경계를 복원하는 방법을 설명한다. 특정 엔진 class 이름을 답으로 가정하지 않는다.

## Boundary map

| boundary | authoritative input/output | headless entry and evidence | representative failure | actual project에서 확인할 것 |
|---|---|---|---|---|
| update/simulation | ordered command + fixed tick → canonical gameplay state | `simulate`; `frame_schedule` → accumulator → `step` → `apply_command`; schedule-independent hash | hitch drop; duplicate/non-owner command | engine update/fixed callback order; pause; physics/contact; thread writers |
| render/presentation | authoritative event/state snapshot → local animation/audio/VFX/UI | `emit_presentation`; four deduped semantic events; presentation fields excluded from canonical state | rollback/duplicate one-shot; missing cosmetic | renderer/UI/audio consumers; interpolation; asset fallback; accessibility cues |
| asset/resource | manifest stable ids + owner generation → validated resident handles and cleanup evidence | `asset_report`; control/cosmetic closure; stale-load rejection; baseline restored | generation 20 completion after generation 21; missing optional | import/cook/package mapping; hard references; CPU/GPU/audio residence; release fences |
| tool/build/validation | versioned fixture/CLI input → reproducible artifact/report and actionable failure | `simulate`, `migrate-save`, `profile`; black-box contract rejects incomplete starter | corrupt save overwrite; checker false-success; modeled profile mistaken for target capture | editor/headless parity; content validator; build manifest/symbols; target automation |

## Recovery procedure

1. **Freeze identity.** Record exact build/source commit, content manifest, save/replay/protocol and target configuration. The Capstone fixture lacks a source commit, so that gap remains visible.
2. **Find the public path.** Start from an input command or load request and trace only public transitions to state, presentation and evidence. In the reference this is `simulate`; in an engine project locate wrappers/callback registration before subsystem internals.
3. **Assign writers and lifetimes.** Use [state ownership](artifacts/state-ownership.csv) and [runtime map](artifacts/runtime-state-map.md) as questions, then replace exemplar owners with real symbols and generations.
4. **Recover asset gates.** Resolve stable ids and transitive references from source/import/cook to runtime residence. Verify control-ready separately from optional presentation.
5. **Recover tool boundaries.** Identify editor import/save, headless validation, packaged build and target profile commands. Confirm they share schema and produce attributable artifacts.
6. **Inject one failure per boundary.** Hitch/duplicate for update; duplicate event/missing cue for presentation; stale completion/missing optional for asset; corrupt input/incomplete starter for tool.
7. **Compare evidence and repair.** Fix the first wrong transition, rerun the same fixture/workload and preserve rule/state invariants. Modeled counters never replace target captures.

## Evidence bundle

- update: smooth, jittered and hitch canonical hash `08b46cfd…6d0e`; hitch max four steps and `116669us` dropped.
- presentation: core events at ticks 12/45/70 and one `match-1:result`; duplicate/non-owner scenarios add no one-shot.
- asset: normal control-ready `118/202 MiB` declared closure; stale-load rejects one completion and restores baseline; missing cosmetic degrades safely.
- tool: reference CLI passes the black-box contract; incomplete starter is rejected; corrupt save preserves sentinel; replay mutant first diverges at checkpoint 60; dependency visits reduce `49→23`.

## What remains manual

- The headless CLI has no engine callback graph, renderer, physics, importer/cooker, GPU/audio allocator, network transport or platform storage.
- Declared MiB and modeled post-fix timings are not measurements of a packaged target build.
- A human must attach real symbol/file paths, capture target traces, inspect presentation/accessibility, validate cleanup fences and approve release evidence.
- Boundary recovery is complete only when another developer can follow input→state→presentation/save and reproduce a frame/resource/simulation failure in the actual project; passing this fixture alone is supporting evidence, not that final judgment.
