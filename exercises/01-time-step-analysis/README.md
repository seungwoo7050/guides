# 01. 시간 단계 분석

## 목표

render frame trace와 time policy를 읽고, fixed simulation이 몇 번 실행되는지, 입력 edge가 어느 tick에서 소비되는지, pause와 overload가 어떤 상태를 남기는지 분석한다.

## 입력

- [`inputs/time-policy.json`](inputs/time-policy.json): clock, fixed step, clamp와 catch-up 정책
- [`inputs/frame-trace.json`](inputs/frame-trace.json): smooth·hitch·pause 구간의 render frame
- [`inputs/input-events.json`](inputs/input-events.json): frame 사이에 도착한 action edge

## 제출

템플릿을 별도 작업 디렉터리에 복사해 작성한다.

- [`template/analysis.md`](template/analysis.md)
- [`template/frame-analysis.csv`](template/frame-analysis.csv)

각 frame마다 최소한 다음을 계산한다.

```text
clamped delta
accumulator before/after
executed tick range
consumed input sequence
남은 accumulator
버린 simulation time 또는 overload state
```

## 대표 오답

- render frame마다 simulation을 정확히 한 번 실행한다.
- 200ms hitch 뒤 필요한 step을 상한 없이 모두 실행한다.
- pause 중 gameplay clock뿐 아니라 network deadline도 멈춘다.
- press edge를 catch-up step 모두에서 반복 소비한다.
- frame ID와 simulation tick을 같은 식별자로 사용한다.

## 사람 검토 질문

1. 모든 timer가 어떤 clock을 사용하는지 추적 가능한가?
2. step이 0개인 frame에서 press edge가 사라지지 않는가?
3. 여러 step이 실행돼도 같은 edge가 한 번만 적용되는가?
4. overload 때 정확도와 responsiveness 중 무엇을 포기했는가?
5. dropped time과 max catch-up 사건이 telemetry에 남는가?

## 완료 기준

- 세 trace 구간의 tick 전이를 계산한다.
- pause reason별 clock policy를 설명한다.
- 입력 edge의 보존·소비 규칙을 작성한다.
- overload 정책의 사용자 경험과 replay 영향을 기록한다.
