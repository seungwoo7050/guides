# Presentation contract — reference exemplar

## gameplay event → presentation

| authoritative event/state | animation | audio | VFX | UI/haptic | replay/correction policy |
|---|---|---|---|---|---|
| dash accepted | locomotion/dash state | dash cue | trail if available | optional haptic | event id/command result once; correction does not replay one-shot |
| core-a activated tick 12 | core active pose | activation cue | core effect | progress 1/3 + non-color label | `match-1:12:core:core-a` dedupe |
| core-b activated tick 45 | core active pose | activation cue | core effect | progress 2/3 + non-color label | `match-1:45:core:core-b` dedupe |
| core-c activated tick 70 | core active pose | activation cue | core effect | progress 3/3 + non-color label | `match-1:70:core:core-c` dedupe |
| match result committed | result state | result cue | optional celebration | best time/result panel | `match-1:result` only after authoritative commit |
| player reset by hazard | reset pose | warning/reset cue | checkpoint effect | non-color warning/haptic | authoritative reset id; prediction correction cannot duplicate |

## presentation ownership

- animation state that may influence rules: none directly. Animation/root motion must submit a bounded intent or be sampled by the simulation contract; animation callback cannot activate cores.
- cosmetic-only state: blend weights, particles, trail, music phase, camera shake and interpolation history.
- one-shot identity: authoritative `event_id`; headless normal emits exactly four events and stores a dedupe set.
- missing asset fallback: `missing-cosmetic` remains control-ready and gameplay hash-identical; use default material/no optional VFX while retaining core/result UI and accessible cue.
- accessibility alternatives: every core/result/hazard cue requires text/shape or haptic/audio alternative; subtitles are migrated but coverage is a manual release gate.

## stale callback/correction

- owner generation: presentation consumer is scoped to current arena/match generation; generation 20 callback cannot bind generation 21 UI/world.
- event sequence: accept a unique authoritative event id once and retain a bounded history for rollback/reconnect.
- rollback/replay: rebuild persistent views from authoritative state; replay one-shots only under an explicit replay mode, not ordinary correction.
- audio/VFX suppression: repeated command/result or snapshot does not enqueue another event with the same id.

## Evidence and limits

- Normal CLI output contains core events for a/b/c plus one result event.
- Duplicate and non-owner scenarios keep the same event list and canonical hash.
- Missing-cosmetic reports degraded operation without changing rule events.
- The headless CLI produces semantic presentation events but renders no animation, audio, VFX, UI, haptic, subtitle or camera. Target content fallback, event timing, accessibility coverage and visual correction artifacts require human playtest and platform capture; REQ-011 remains unresolved while release evidence is `unknown`.
