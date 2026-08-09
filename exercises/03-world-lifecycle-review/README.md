# 03. 월드와 객체 수명 검토

## 목표

scene streaming과 match restart trace에서 world, entity, component, subsystem과 async request의 owner를 찾고 stale reference·double subscription·partial cleanup 위험을 분석한다.

## 입력

- [`inputs/system-brief.md`](inputs/system-brief.md)
- [`inputs/lifecycle-events.json`](inputs/lifecycle-events.json)
- [`inputs/references.json`](inputs/references.json)

## 제출

- [`template/lifecycle-review.md`](template/lifecycle-review.md)
- [`template/owner-map.csv`](template/owner-map.csv)

template의 빈 owner row·위험 edge·cleanup 순서·측정값은 의도적인 미완성 starter다. `GameProcess` 한 줄만 채우거나 `world_unloaded`를 cleanup 완료로 간주해서는 완료되지 않는다. 먼저 자신의 review를 작성한 뒤 다음 기준 예시와 비교한다.

- [`reference/lifecycle-review.md`](reference/lifecycle-review.md): trace 위험·teardown·generation 판정의 완성 예시
- [`reference/owner-map.csv`](reference/owner-map.csv): brief와 fixture runtime object의 owner/lifetime 정본 evidence

## 기계 검증 가능한 evidence

검증기는 reference에서 최소한 다음 fixture 사실을 확인할 수 있다.

- generation 7 cancel은 event 10, MatchState destroy는 event 12, ArenaWorld unload는 event 13이다.
- event 14의 Cosmetic completion, event 15의 HUD callback, event 18의 NavMesh completion은 각각 unloaded/destroyed/mismatched-generation target을 향하므로 stale로 거부한다.
- event 17에서 generation 8 ArenaWorld가 생성된 뒤에도 event 18의 generation 7 결과를 새 world에 적용하지 않는다.
- owner map은 process service, 두 world scope, session/match/entity/UI와 두 async request를 포함하고 persistent→match raw reference 위험을 generation-checked handle 또는 scoped token으로 바꾼다.
- trace에 없는 HUD unbind, Telemetry unsubscribe, Audio handle clear와 async cancel acknowledgement를 완료됐다고 가정하지 않는다.
- 반복 unload 뒤 arena/match-owned entity·subscription·resident bundle·async request 기준선은 모두 0이어야 한다.

이 검사는 문서에 필수 object/event가 있는지 판정할 수 있지만 실제 engine의 object reclamation, thread affinity나 GPU fence 완료를 증명하지 않는다.

## 대표 오답

- 화면에서 사라진 object는 즉시 파괴됐다고 가정한다.
- persistent manager가 scene object의 raw reference를 영구 보관한다.
- async callback이 owner generation을 확인하지 않는다.
- event unsubscribe를 destructor 한 곳에만 의존한다.
- restart가 새 match를 만들기 전에 이전 resource가 모두 정리됐는지 검사하지 않는다.

## 사람 검토 질문

1. logical identity와 runtime object identity를 구분했는가?
2. create, activate, disable, destroy, unload가 다른 사건인가?
3. cross-scene reference가 stable id/handle로 해석 가능한가?
4. stale async completion을 generation/cancellation으로 거부하는가?
5. 여러 번 진입·이탈했을 때 count가 기준선으로 돌아오는가?

## 사람 검토 루브릭

| 항목 | 합격 evidence | 보완이 필요한 상태 |
|---|---|---|
| owner/scope | fixture와 brief의 runtime object마다 owner·creator·destroyer·generation invariant가 있다. | 화면에서 사라짐을 destroy로 간주하거나 owner가 둘 이상이다. |
| stale 판정 | events 14·15·18과 process→match raw/subscription edge의 live 조건을 사건 순서로 증명한다. | object 이름만 비교하고 generation 7/8을 구분하지 않는다. |
| teardown/cancel | admission close→cancel→unsubscribe/handle clear→match destroy→world unload→baseline 순서와 idempotency를 설명한다. | destructor나 `world_unloaded` 한 사건에 모든 cleanup을 맡긴다. |
| 반복 evidence | active peak와 exit baseline을 구분하고 1회·20회 뒤 네 count의 합격 조건을 기록한다. | 한 번 성공한 screenshot만 있고 누적 count가 없다. |
| 한계와 복구 | fixture에 없는 acknowledgement를 누락 evidence로 표시하고 stale callback의 no-op/release telemetry를 정의한다. | 자동 검사가 실제 engine lifetime 전체를 증명한다고 주장한다. |

다섯 항목을 모두 만족해야 완료다. reference 문구를 복사한 것보다 선택한 engine의 handle·subscription·async cancellation API에 이 invariant를 어떻게 적용할지가 최종 사람 검토 대상이다.

## 완료 기준

- 모든 runtime object에 owner와 lifetime scope를 부여한다.
- trace에서 최소 네 개의 위험 edge를 찾는다.
- unload/restart/cancel의 cleanup 순서와 검사 근거를 작성한다.
