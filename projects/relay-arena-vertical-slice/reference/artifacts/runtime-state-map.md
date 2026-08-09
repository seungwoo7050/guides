# Runtime state map — reference exemplar

이 산출물은 fixture와 headless CLI가 증명하는 상태를 구분한다. 실제 엔진의 callback, thread, platform suspend deadline은 수동 조사 대상이다.

## 식별자

- process/build: release candidate `relay-client@1.0.0-rc3`; headless 구현은 executable build 대신 source와 input identity로 실행한다.
- frontend world: runtime trace의 generation `1`.
- arena session/world: 첫 요청 generation `20`, cancel 뒤 새 요청 generation `21`.
- match: headless canonical id `match-1`; runtime instance는 arena generation `20` 또는 `21`과 함께 식별한다.
- entity: player `p1`, relay core `core-a|core-b|core-c`; stable id와 runtime generation을 함께 사용한다.
- content/rules: `arena-rules@17`; network session `relay-match-500`, protocol `4`.

## 상태 기계

| from → to | trigger/guard | owner | durable or external side effect | failure state/evidence |
|---|---|---|---|---|
| boot → frontend | process start와 frontend critical services ready | runtime controller | 없음 | startup failure는 arena state를 만들지 않음 |
| frontend → arena loading | `arena_load_request`, 새 generation 발급 | arena session owner | content request 시작 | generation 20 cancel 가능 |
| arena loading → control-ready | critical scene/player/rules closure가 resident이고 generation 일치 | arena session + asset loader | world/entity 활성화 | missing critical이면 frontend로 복귀 |
| control-ready → playing | match rules와 input route 준비 | match owner | command consumption 시작 | optional cosmetic/nav는 gate를 막지 않음 |
| playing → result pending | 세 core가 active | rules subsystem | idempotent result intent | duplicate/retry는 같은 match id 사용 |
| result pending → result committed | profile save commit 성공 | profile/save owner | best time와 `result_commit_ids` 갱신 | storage/suspend 실패면 pending을 유지하고 재시도 |
| any arena state → abandoned/frontend | cancel, explicit abandonment 또는 shutdown | arena session owner | request 취소와 resource cleanup | late generation 20 completion을 폐기 |

Headless CLI는 `playing`에서 시작해 simulation contract를 작게 검증한다. boot, frontend, loading과 actual suspend callback은 구현했다고 주장하지 않는다.

## 취소·재시작·suspend

| event | current state | allowed next state | partial state | cleanup owner | evidence |
|---|---|---|---|---|---|
| arena load cancel, runtime event 10 | generation 20 loading/control-ready | abandoned → frontend | world/match/content request 일부 존재 가능 | arena generation 20 owner | events 11–13; `stale-load` scenario rejects one completion and restores baseline |
| match restart/new load, event 14 | previous generation cleaned or abandoning | generation 21 loading | generation 20 callbacks may still arrive | runtime controller issues 21; each old owner releases itself | event 16 navigation completion still carries generation 20 |
| OS suspend, event 18 | generation 21 match/result path | suspended or bounded result pending | result commit may be in flight | platform lifecycle + profile/save owner | events 19 and 21 show retry; release evidence marks this path `fail` |
| shutdown | any | shutdown | outstanding requests, presentation subscriptions, temporary save | process owner coordinates reverse cleanup | headless resource baseline only; target shutdown is manual evidence |

## stale completion

- generation check: `(arena_session_id, world_generation)` must equal the current owner before attach.
- cancellation: cancel marks generation 20 closed before destroying world/match and propagates to child requests.
- late callback decision: events 13 and 16 cannot mutate generation 21. Headless `stale-load` reports `stale_completions_rejected=1`.
- subscription cleanup: match/HUD/presentation subscriptions are removed before generation reuse; repeated entry must restore entity/subscription/resource counters.

## Evidence and limits

- Normal: smooth simulation reaches tick 90, `result_committed`, active cores a/b/c, one `match-1` commit.
- Boundary: jittered frame schedule reaches the same canonical hash with up to two steps per frame.
- Failure: hitch is bounded to four steps and drops `116669us`; stale load rejects one old completion; corrupt save test preserves the existing output.
- Manual review: map these states to actual engine classes/nodes, inspect asynchronous thread/fence behavior, repeat arena entry/exit on a packaged build, and reproduce suspend while durable storage is active. Headless success does not close release evidence `load-cancel=unknown` or `suspend-result-commit=fail`.
