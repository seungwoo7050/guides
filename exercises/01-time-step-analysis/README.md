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

템플릿의 빈 셀과 `TODO` 성격의 항목은 의도적인 미완성 시작점이며 그대로는 완료 제출이 아니다. 계산을 마친 뒤에만 다음 기준 예시와 비교한다.

- [`reference/analysis.md`](reference/analysis.md): clock·입력·overload 판단의 완성 예시
- [`reference/frame-analysis.csv`](reference/frame-analysis.csv): fixture에서 계산한 frame별 정본 evidence

각 frame마다 최소한 다음을 계산한다.

```text
clamped delta
accumulator before/after
executed tick range
consumed input sequence
남은 accumulator
버린 simulation time 또는 overload state
```

## 기계 검증 가능한 evidence

검증기는 CSV를 파싱해 최소한 다음 fixture 결과를 확인할 수 있다.

- 실행 tick은 `120-129`이고 frame별 범위는 `none`, `120`, `121-123`, `124-127`, `none`, `none`, `none`, `128-129`다.
- frame 4는 raw `200000us`를 `100000us`로 clamp하고 step 4개 뒤 `33334us`를 버려 accumulator `3330us`를 남긴다.
- 마지막 accumulator는 `3996us`, 전체 dropped time은 `33334us`다.
- 입력 sequence 2, 3, 4는 각각 tick 120, 124, 128에서 한 번만 소비되고, Menu에서 차단된 sequence 5는 소비되지 않는다.
- step이 없는 frame 1과 7의 최신 Move sample은 각각 tick 120과 128까지 보존된다.

reference가 이 값을 만족한다는 사실은 계산 계약의 예시일 뿐, 학습자의 pause·replay trade-off 설명까지 자동 판정하지 않는다.

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

## 사람 검토 루브릭

| 항목 | 합격 evidence | 보완이 필요한 상태 |
|---|---|---|
| 계산 추적성 | 모든 frame의 accumulator 식과 tick 범위를 fixture 값으로 재계산할 수 있다. | 최종 숫자만 있고 중간 accumulator 또는 clamp 근거가 없다. |
| 입력 불변식 | 0-step·multi-step·pause에서 각 edge의 보존·단일 소비·차단 이유를 설명한다. | frame당 한 번 update 가정이나 edge 중복/유실이 남는다. |
| clock 경계 | 네 timer가 어떤 pause reason에 멈추는지 policy field로 근거를 댄다. | gameplay pause가 network deadline까지 멈춘다고 가정한다. |
| overload 판단 | responsiveness·replay 영향과 telemetry/recovery를 함께 기록한다. | max step 숫자만 쓰고 버린 시간과 사용자 영향이 없다. |

네 항목을 모두 만족해야 완료로 검토한다. 숫자 검사가 통과해도 추가 가정과 미확인 항목을 숨기면 완료로 보지 않는다.

## 완료 기준

- 세 trace 구간의 tick 전이를 계산한다.
- pause reason별 clock policy를 설명한다.
- 입력 edge의 보존·소비 규칙을 작성한다.
- overload 정책의 사용자 경험과 replay 영향을 기록한다.
