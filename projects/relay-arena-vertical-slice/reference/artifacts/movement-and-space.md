# Movement and space contract — reference exemplar

## coordinate spaces

| value | source space | destination space | conversion owner | validation |
|---|---|---|---|---|
| Move axis | device/action local 2D | gameplay world-planar intent in milli-units | input command router | each integer axis within `[-1000,1000]`; device identity removed |
| player transform | authoritative simulation milli-units | presentation world transform | simulation writes; presentation interpolates | one writer per tick; canonical x/y in replay hash |
| camera aim | local camera/view space | gameplay aim intent if a rule needs it | camera/input adapter | camera smoothing/offset never becomes authoritative position |
| navigation path | nav/world query space | movement intention command | AI/navigation adapter | world generation and target stable id checked before use |

## simulation order

```text
ordered command for fixed tick
→ validate owner/sequence/phase
→ update movement intent or apply dash
→ collision/world validation in an engine integration
→ authoritative transform and gameplay contact events
→ canonical state/replay checkpoint
→ presentation interpolation
```

- fixed/variable phase: rules and transform update only in `16667us` fixed steps; render schedule only controls how many steps run.
- teleport/checkpoint reset: hazard reset must be an authoritative transition that clears invalid contact/prediction history while preserving active cores per `gameplay-rules.json`.
- dash collision: the headless implementation applies 3000 milli-units directly. A playable engine must sweep/validate the displacement and define blocking/tunneling behavior before claiming collision correctness.
- hazard ordering: movement/collision produces a single reset event after authoritative transform evaluation; core progress remains unchanged.
- transform writer: local profile uses simulation; network profile uses server simulation with owning-client prediction as a temporary view.

## failure cases

| case | invariant | expected result | trace/profile |
|---|---|---|---|
| smooth/jittered/hitch render schedules | same ordered commands at 90 ticks give same gameplay state | x=32000, y=60000, same canonical hash | max steps 1/2/4; hitch drops 116669us |
| duplicate dash/interact command | a sequence mutates state once | duplicate sequence 3 rejected; canonical hash unchanged | `duplicate_or_stale` rejection |
| tunneling candidate during dash | transform cannot pass invalid blocker/contact | playable implementation sweeps or subdivides and records hit | not modeled by CLI; engine collision fixture required |
| scene origin/parent change | stable gameplay coordinates do not silently change | convert at one boundary or reject stale generation | runtime events generation 20→21 |
| network correction | authoritative transform wins without duplicate gameplay contact | rewind/resim bounded commands; presentation smooth/snap by policy | network fixture snapshot 52 then stale 51 |

## Headless calculation and manual limit

The fixture sets Move `[1000,0]` at tick 1. Fixed integration contributes 1000 milli-units per tick; dash at tick 4 adds 3000. Move changes to `[0,1000]` at tick 30, producing final x/y `32000/60000` at tick 90. This proves integer update ordering, not physics-engine contacts, root motion, coordinate-origin precision or target frame cost. Those require an actual engine scene, collision shapes and target capture.
