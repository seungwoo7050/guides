# 06. authority와 latency

## 목표

multiplayer command와 snapshot trace에서 client intent, server validation, authoritative result, local prediction과 presentation을 분리한다. latency·loss·duplicate·reordering에서 상태가 어떻게 수렴하거나 명시적으로 실패해야 하는지 설계한다.

## 입력

- [`inputs/authority-model.json`](inputs/authority-model.json)
- [`inputs/session-trace.json`](inputs/session-trace.json)
- [`inputs/network-faults.json`](inputs/network-faults.json)

## 제출

- [`template/authority-review.md`](template/authority-review.md)
- [`template/fault-matrix.csv`](template/fault-matrix.csv)

## 대표 오답

- client가 `award_score`, `hit_confirmed`, `match_won` 결과를 제출한다.
- packet arrival order를 simulation order로 사용한다.
- duplicate command가 side effect를 두 번 발생시킨다.
- old snapshot이 local latest state를 덮는다.
- correction 뒤 audio/VFX one-shot을 다시 재생한다.

## 사람 검토 질문

1. 각 state의 authoritative writer가 하나인가?
2. command sequence/tick/session identity가 중복·stale 판정에 충분한가?
3. prediction 가능한 상태와 기다려야 하는 상태를 구분했는가?
4. correction은 simulation과 presentation을 각각 어떻게 처리하는가?
5. incompatible protocol/content가 join 전에 거부되는가?

## 완료 기준

- authority table과 command validation을 작성한다.
- session trace에서 최소 세 개의 잘못된 전이를 찾는다.
- fault별 player-visible UX와 telemetry를 제출한다.
