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

## 완료 기준

- 모든 runtime object에 owner와 lifetime scope를 부여한다.
- trace에서 최소 네 개의 위험 edge를 찾는다.
- unload/restart/cancel의 cleanup 순서와 검사 근거를 작성한다.
