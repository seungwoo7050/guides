# 월드와 객체 수명 검토 기준 예시

## lifetime scopes

```text
process: GameProcess, AudioDirector, TelemetryClient
→ world session: FrontEndWorld, ArenaSession
→ arena/match generation: ArenaWorld, MatchState, async requests
→ entity/component: PlayerEntity, RelayCore[3], HazardSpawner
→ local projection: ArenaHud binding
→ event/callback: completion and subscription invocation
```

[`owner-map.csv`](owner-map.csv)는 brief와 두 fixture에 등장하는 runtime object·service·request의 owner, 파괴 주체와 generation invariant를 기록한다. logical identity(`match`, `player:p1`)와 runtime identity(`generation=7`의 실제 object)는 같지 않다.

## trace에서 확정되는 사건

- generation 7의 cancel은 event 10에서 시작되고 MatchState는 event 12, ArenaWorld는 event 13에서 더 이상 live하지 않다.
- generation 7의 `CosmeticBundleRequest`는 world unload 뒤 event 14에서 완료된다.
- generation 7 HUD callback은 MatchState destroy 뒤 event 15에서 도착한다.
- generation 8의 ArenaWorld는 event 17에서 만들어진다.
- generation 7의 `NavMeshRequest`는 generation 8 world가 존재한 뒤 event 18에서 완료된다.
- trace에는 `hud_unbound`, `telemetry_unsubscribed`, `audio_listener_cleared`, `async_cancel_acknowledged`가 없다. 보이지 않는 cleanup을 수행됐다고 가정하지 않고 누락 evidence로 취급한다.

## 위험 edge

| event/edge | 현재 위험 | stale 여부 판정 | 보호할 invariant | 수정 계약 | evidence |
|---|---|---|---|---|---|
| event 10 `arena_cancel_requested` | 두 async request와 새 callback admission을 닫았다는 사건이 없다. | cancel 자체는 stale이 아니지만 이후 generation-7 publish는 금지해야 한다. | cancel 뒤 generation 7은 어떤 load result도 commit하지 않는다. | session을 `cancelling/closed`로 원자 전이하고 request cancellation token을 발행한다. | events 10-13 사이 cancel acknowledgement가 없다. |
| `ArenaHud:local-1 → MatchState` raw reference | HUD binding을 끊기 전에 MatchState가 파괴될 수 있다. | event 12 이후 generation-7 reference는 stale이다. | callback 시작 시 binding token과 target generation이 모두 live다. | raw reference를 scoped subscription + checked handle로 바꾸고 match destroy 전에 revoke한다. | event 9 bind 뒤 unbind 없이 event 12 destroy와 event 15 callback이 나온다. |
| `TelemetryClient → MatchState` subscription | process service가 match-owned subscriber를 계속 호출할 수 있다. | event 12 이후 subscription target은 stale이다. | process service에는 destroyed match target을 향한 live token이 없다. | generation-scoped token을 ArenaSession이 소유하고 teardown barrier에서 revoke한다. | `references.json`에는 subscription이 있지만 trace에는 unsubscribe가 없다. |
| `AudioDirector → PlayerEntity:p1` raw reference | process service가 match teardown 뒤 entity memory를 관찰할 수 있다. | event 12의 match teardown 이후 stale로 판정한다. | process service는 stable id를 매 callback 때 live handle로 resolve한다. | `player:p1 + generation` handle로 교체하고 teardown 때 listener를 clear한다. | PlayerEntity는 match-owned이고 AudioDirector는 process-owned다. |
| event 14 cosmetic completion → ArenaWorld g7 | unloaded world에 cosmetic을 attach할 수 있다. | stale: event 13에서 generation-7 world가 이미 unloaded됐다. | callback generation과 current resident world generation이 일치할 때만 publish한다. | completion은 payload를 한 번 release하고 attach는 `current_generation == 7 && world_live`일 때만 한다. | event 13 precedes event 14; callback purpose는 `attach_cosmetic`이다. |
| event 15 HUD callback → MatchState g7 | destroyed MatchState를 projection하려 한다. | stale: event 12가 destroy이고 event 15가 callback이다. | revoked binding은 callback body에 들어가지 않으며 late invocation도 handle check로 no-op한다. | unsubscribe + generation check를 함께 사용한다. | event 12 precedes event 15; raw runtime reference edge가 있다. |
| event 18 navmesh completion g7 → MatchState | 같은 logical 이름의 새 generation에 이전 결과를 적용하는 ABA 위험이 있다. | stale: callback generation 7이고 현재 arena/match generation은 8이다. | async result는 captured generation과 live target generation이 같을 때만 commit한다. | generation mismatch를 `stale_completion`으로 기록하고 payload만 release한다. | event 17 creates ArenaWorld g8 before event 18 completes request g7. |

events 14, 15, 18은 모두 정상적인 “늦게 도착할 수 있는 사건”이며 process crash로 숨길 오류가 아니다. 각각 `stale_completion` 또는 `stale_callback`으로 거부하고 cleanup은 정확히 한 번 수행해야 한다.

## unload/cancel 순서

1. event 10에서 ArenaSession generation 7의 admission을 닫고 cancel state와 generation token을 먼저 publish한다.
2. 새 gameplay/input commit을 중단하고 NavMesh·Cosmetic request에 cancellation을 요청한다. cancellation 요청과 완료 acknowledgement를 구분한다.
3. ArenaHud binding과 Telemetry subscription을 revoke하고 AudioDirector의 player runtime handle을 clear한다.
4. match-owned `PlayerEntity`, `RelayCore[3]`, `HazardSpawner`를 정리한 뒤 MatchState를 파괴한다.
5. ArenaWorld를 unload한다. 이후 도착한 generation-7 completion은 payload만 release하고 world/match에 publish하지 않는다.
6. live entity·subscription·resident bundle·async request count가 기준선으로 돌아왔음을 기록한다. generation 8은 generation 7의 admission이 닫힌 뒤 시작할 수 있지만, 늦은 transport completion을 기다릴 필요는 없으며 반드시 generation check로 격리한다.

현재 trace는 event 11-13의 파괴 순서는 보여 주지만 2·3·6의 완료 evidence가 없다. 따라서 “world_unloaded가 있으므로 cleanup 완료”라고 판정하면 안 된다.

## generation과 handle 정책

- stable id: save·progression·lookup에는 `world:arena`, `match`, `player:p1` 같은 logical id를 사용한다.
- runtime handle: `{stable_id, generation, weak_slot}`을 resolve해 대상이 live인지 검사하며 raw address를 process service에 보존하지 않는다.
- generation token: ArenaSession이 단조 증가하는 7, 8을 발급한다. async callback과 UI binding은 생성 시 generation을 capture하고 commit 직전 current generation과 다시 비교한다.
- cancellation token: request마다 cancel 요청·completion·payload release 상태를 닫힌 state machine으로 관리한다. cancel과 completion이 경쟁해도 release owner는 하나다.
- subscription cleanup: subscription token은 subscriber가 아니라 ArenaSession의 teardown bag에도 등록하고 명시적으로 revoke한다. destructor만을 유일한 cleanup 경로로 삼지 않는다.

generation mismatch는 target 이름이 같아도 허용하지 않는다. event 18의 `ArenaWorld`라는 logical 이름이 event 17의 새 object와 같다는 이유로 generation-7 navmesh를 generation 8에 붙일 수 없다.

## 반복 진입 검사

아래 count는 process·FrontEndWorld 같은 의도된 persistent object를 제외한 **arena/match-owned** resource 기준이다.

| 측정 | 기준선 | 1회 이탈 | 20회 뒤 | 합격 조건 |
|---|---:|---:|---:|---|
| live entities | 0 | 0 | 0 | 각 active match의 peak는 Player 1 + RelayCore 3 + HazardSpawner 1인 5이고 unload 뒤 항상 0이다. |
| subscriptions | 0 | 0 | 0 | HUD binding과 Telemetry token이 teardown 뒤 모두 revoke된다. |
| resident bundles | 0 | 0 | 0 | late Cosmetic completion도 attach하지 않고 payload를 release한다. |
| async requests | 0 | 0 | 0 | cancel·completion race 뒤 NavMesh와 Cosmetic request가 terminal/released 상태다. |

한 번의 exit 직후뿐 아니라 20번 반복 뒤에도 기준선과 같아야 한다. peak count가 매 진입마다 5 entities, 2 scoped binding/subscription, 2 async requests를 넘어서 누적되면 double subscription 또는 partial cleanup을 조사한다.

## machine-checkable 판정 요약

```text
generation-7 close begins: event 10
generation-7 MatchState dead: event 12
generation-7 ArenaWorld dead: event 13
must reject as stale: events 14, 15, 18
new generation observed: events 16, 17, 19
required missing cleanup evidence: HUD unbind, telemetry unsubscribe,
                                   audio handle clear, async cancel acknowledgement
post-exit arena/match baselines: entities=0, subscriptions=0,
                                 resident_bundles=0, async_requests=0
```

## 사람이 확인할 판단

- fixture는 actual allocator, engine weak handle API와 callback scheduler를 제공하지 않으므로 handle 표현과 teardown thread는 프로젝트에 맞게 결정해야 한다.
- event 12가 모든 match-owned entity teardown을 포함한다는 해석은 system brief에서 도출한 것이다. 실제 trace에는 entity별 destroy event가 없어 production telemetry 보강이 필요하다.
- zero baseline은 누수를 찾는 acceptance criterion이지 실제 memory reclamation이나 GPU fence 완료를 자동 증명하지 않는다.
