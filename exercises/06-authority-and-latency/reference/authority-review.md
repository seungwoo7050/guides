# authority와 latency 검토 예시 해설

이 해설은 trace에 나타난 판정과 fixture가 요구하는 정책을 분리한다. accepted tick window의 숫자, reconnect timeout과 smoothing 값은 입력에 없으므로 프로젝트 설정으로 발명하지 않는다.

## authority table

| state/result | proposed by | validated by | authoritative writer | replicated to | local prediction | correction |
|---|---|---|---|---|---|---|
| player movement | owning client가 move intent 제출 | server가 owner, tick window와 movement rule 검사 | server | 모든 relevant client | owning client transform prediction 허용 | acknowledged command까지 rewind 후 unacked command resimulation |
| dash cooldown | owning client가 dash intent 제출 | server가 owner, cooldown과 movement precondition 검사 | server | owner 중심, 필요한 observer | owning client만 bounded prediction | server cooldown/tick으로 교정하고 duplicate one-shot 억제 |
| core activation | owning client가 target intent 제출 | server가 owner, phase, range와 inactive 상태 검사 | server | 모든 client | 하지 않음; pending UI만 가능 | reject면 pending 해제, accepted authoritative event만 presentation |
| match result | client가 직접 제안할 수 없음 | server rule simulation이 core invariant와 idempotency 검사 | server | 모든 client | 없음 | authoritative result id로 UI/audio/VFX를 한 번만 표시 |
| camera shake | local presentation event 소비 | local accessibility/presentation policy | local presentation | replication 없음 | 해당 없음 | correction/replay에서 event id로 dedupe 또는 suppress |

## trace finding

| event index | finding | violated invariant | server decision | client UX | evidence |
|---:|---|---|---|---|---|
| 2 | `client-b`가 protocol 3으로 join | session protocol은 4 | gameplay state를 만들기 전에 join 거부 | update/compatibility 이유 표시 | authority model protocol 4 vs event protocol 3 |
| 4 | `client-b`가 `p1` dash 제출 | command source는 player owner여야 함 | `non_owner` 거부, state 불변 | action denied; 다른 player motion 없음 | actor map에서 p1 owner는 client-a |
| 6 | sequence 11 command가 중복 도착 | `(session, source, sequence)` side effect는 at-most-once | 최초 command의 pending/결과를 재사용하고 두 번째 실행 금지 | 중복 core cue 없음 | index 5와 payload/identity 동일 |
| 8 | snapshot 43이 44 뒤 도착 | applied snapshot sequence/tick은 단조 증가 | server state 변화 없음; client가 43 폐기 | 위치가 과거 7.0으로 튀지 않음 | index 7 seq44/tick101 뒤 seq43/tick99 |
| 9 | client가 `match_won` result를 주장 | match result writer는 server | invalid message/result claim 거부 | 승리 UI를 표시하지 않음 | authority model `match_result.writer=server` |
| 10 | sequence 11이 `out_of_range`로 늦게 거부 | pending intent가 result 전에 authoritative state를 바꾸면 안 됨 | core state 불변, canonical rejection 한 번 기록 | pending 표시 해제; core/audio/VFX one-shot 없음 | command_result sequence 11 rejected |

## sequence와 stale 정책

- session identity: `match-204` + protocol `4` + content `arena-rules@17`.
- command idempotency key: `(session_id, source_client, command_sequence)`. player/tick/kind/value는 duplicate payload consistency를 확인하지만 key를 대신하지 않는다.
- accepted tick window: `server_tick - rollback_window <= command.tick <= server_tick + future_tolerance`인 bounded window를 사용한다. 두 bound의 숫자는 fixture에 없으며 target latency/profile로 정해야 한다.
- sequence policy: source client별 accepted/high-water와 bounded dedupe cache를 유지한다. 같은 key의 다른 payload는 protocol violation으로 거부한다.
- snapshot monotonicity: stream/entity별 `snapshot_sequence > last_applied_sequence`만 적용한다. index 43은 44 뒤이므로 폐기한다.
- reconnect generation: reconnect는 새 connection/session generation을 만들고 snapshot+ack에서 history를 다시 세운다. 이전 generation packet과 prediction history는 적용하지 않는다.

## prediction/correction

- predicted state: owning player transform과 dash cooldown처럼 즉시 feedback이 필요하고 rewind 가능한 state.
- non-predicted state: core activation, match result와 durable reward. pending presentation만 허용한다.
- rollback/resimulation: server snapshot과 `acked_command`까지 복원한 뒤 같은 ordered unacked command를 재적용한다.
- presentation one-shot suppression: authoritative event id 또는 `(match_id, event_sequence)`로 audio/VFX/UI를 dedupe한다. simulation rollback이 one-shot을 다시 만들지 않게 한다.
- correction visibility policy: 작은 transform error는 bounded smoothing, 큰/invalid state는 snap+명확한 feedback을 사용하되 threshold는 profile evidence로 정한다.

## compatibility gate

- protocol: join event의 version은 `4`여야 한다. index 2는 `3`이라 pre-session reject다.
- content: gameplay-critical content는 `arena-rules@17` 호환이어야 한다. mismatch는 command를 받기 전에 거부한다.
- build/capability: fixture에 build allow-list가 없으므로 protocol/content 외 조건을 통과했다고 가정하지 않는다.
- actionable rejection: expected/actual protocol·content와 update/retry 가능 여부를 제공하되 hidden server state는 노출하지 않는다.

## 사람 검토 rubric

- index 2, 4, 6, 8, 9와 late rejection 10을 구체적으로 판정했는가?
- command identity와 packet arrival order를 구분했는가?
- transform/dash prediction과 core/result 대기를 분리했는가?
- correction 뒤 authoritative event가 한 번만 표현되는가?
- fixture에 없는 tick window 숫자나 transport 보장을 사실처럼 쓰지 않았는가?
