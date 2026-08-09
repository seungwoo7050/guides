# 시간 단계 분석 제출

## 사용한 정책과 가정

- policy id:
- 확인 가능한 사실:
- 계산을 위해 추가한 가정:
- 미확인 항목:

## clock 표

| 상태/동작 | clock | pause reason별 동작 | 근거 |
|---|---|---|---|
| match timer |  |  |  |
| network deadline |  |  |  |
| movement |  |  |  |
| camera blend |  |  |  |

## 입력 보존과 소비

- continuous action sampling:
- edge queue:
- menu/focus context:
- catch-up 중 중복 방지:

## overload 판정

- 첫 overload frame:
- 실행한 step 수:
- 보존한 accumulator:
- 버리거나 느려진 시간:
- telemetry event:
- replay/player experience 영향:

## 실패 검증

| 실패 주입 | 보호할 invariant | 예상 evidence | recovery |
|---|---|---|---|
| 200ms hitch |  |  |  |
| pause 중 input |  |  |  |
| step 없는 frame |  |  |  |
