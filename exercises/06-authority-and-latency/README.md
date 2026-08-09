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

`template/`은 의도적으로 비어 있는 starter다. 자신의 작업 디렉터리에 복사해 채우고 입력 trace나 template 원본을 수정해 문제를 없애지 않는다. 완료 뒤 다음 예시 해설과 비교한다.

- [`reference/authority-review.md`](reference/authority-review.md)
- [`reference/fault-matrix.csv`](reference/fault-matrix.csv)

정책 표현은 달라질 수 있지만 trace의 owner, duplicate/stale identity와 authoritative writer 판정은 fixture에서 결정되므로 일치해야 한다.

## 검증 근거

자동 검사 또는 trace에서 직접 판정 가능한 증거:

- session은 protocol `4`, content `arena-rules@17`이며 `p1`의 owner는 `client-a`다.
- index `2`는 protocol mismatch, `4`는 non-owner command, `6`은 sequence 11 duplicate다.
- snapshot `44/tick101` 뒤의 `43/tick99`는 stale이므로 index `8`을 적용하지 않는다.
- index `9`의 client result claim은 server-only `match_result` writer 계약을 위반한다.
- index `10`은 sequence 11의 canonical `out_of_range` rejection이며 duplicate side effect나 confirmed core cue가 없어야 한다.
- fault matrix는 `network-faults.json.required_cases`의 여섯 case를 모두 포함하고 protocol mismatch/result claim도 trace evidence로 다룬다.

사람이 검토할 rubric:

- state마다 authoritative writer가 하나이고 client intent와 result가 분리되는가?
- idempotency key, tick window, snapshot sequence와 reconnect generation의 역할이 다른가?
- movement/dash prediction과 core/result 대기를 구분하는가?
- rollback 뒤 simulation state와 presentation one-shot을 각각 수렴시키는가?
- fixture에 없는 numeric tick window, timeout과 transport 보장을 임의로 확정하지 않는가?

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
- 예시 해설의 event 판정과 비교하고 policy proposal과 fixture fact를 구분한다.
