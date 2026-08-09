# State, deduplication과 delivery

## 학습 목표

- stateless transform과 keyed/operator state를 구분한다.
- source replay, state checkpoint와 sink commit이 함께 만드는 처리 보장을 설명한다.
- at-most-once, at-least-once와 exactly-once 표현을 end-to-end outcome 기준으로 검토한다.
- dedup state의 key, TTL, false positive와 replay 범위를 설계한다.

## 핵심 모델

stateful stream processor는 다음 상태 기계다.

```text
(source position, operator state, pending timers, sink effects)
  --record / timer / checkpoint / failure-->
(next state)
```

worker process memory만 보면 안 된다. failure 뒤 어떤 checkpoint로 되돌아가고 어떤 output이 이미 보였는지 함께 본다.

## stateless와 stateful

### stateless

각 record를 독립적으로 map/filter한다. retry가 쉬워 보이지만 외부 side effect가 있으면 여전히 idempotency가 필요하다.

### keyed state

key별 count, latest version, session, dedup set를 유지한다. key partitioning이 state ownership과 scale-out을 결정한다.

### operator/global state

source split, broadcast rule, reference snapshot처럼 operator 전체가 공유하는 상태다. update order와 checkpoint semantics를 명확히 한다.

### timers

event-time 또는 processing-time 조건에서 state를 emit/cleanup한다. timer도 checkpoint와 restore 대상인지 확인한다.

## processing guarantee 용어

### at-most-once

record가 유실될 수 있지만 한 번보다 많이 반영되지 않도록 한다. source position을 처리 전에 commit하면 crash 시 유실될 수 있다.

### at-least-once

유실을 피하기 위해 실패 시 record를 replay한다. duplicate effect가 가능하므로 sink dedup/idempotency가 필요하다.

### exactly-once processing

engine 내부 state update가 checkpoint 기준으로 한 번 반영되는 것처럼 보일 수 있다. 그러나 외부 sink, API, email, file publish까지 자동 포함하지 않는다.

### exactly-once outcome

업무 결과가 한 번만 반영된 것과 동등한 상태가 된다.

가능한 조합:

- transactional source+state+sink commit
- deterministic record key와 idempotent upsert
- append 후 downstream dedup
- versioned output replace
- effect ledger와 reconciliation

“exactly-once 지원”은 어느 boundary와 failure model에서 성립하는지 적어야 한다.

## checkpoint

checkpoint가 capture해야 하는 항목:

- partition별 source position
- keyed/operator state
- event-time timers와 watermark 관련 state
- in-flight transaction 또는 sink commit token
- transform/schema version

### consistent cut

여러 operator의 state와 source position이 같은 논리 시점의 cut이어야 한다. 일부 state는 새 record를 포함하고 source offset은 이전 위치라면 restore 후 duplicate 또는 loss가 생긴다.

### checkpoint interval

짧으면 recovery loss/replay 범위가 줄지만 overhead가 커진다. 길면 checkpoint cost는 낮지만 restore와 replay가 커진다. state size, sink transaction, latency와 failure rate로 측정한다.

## sink 패턴

### idempotent upsert

stable key와 monotonic version을 사용한다.

```text
if incoming.version > stored.version:
    replace
else:
    ignore stale/duplicate
```

version ordering이 source contract와 일치해야 한다.

### transactional sink

checkpoint와 sink transaction을 연동한다. transaction timeout, coordinator failure, orphan transaction과 recovery를 검토한다.

### append with deterministic ID

append record에 event/window/result ID를 넣고 unique constraint 또는 downstream dedup을 사용한다.

### file sink

temporary file을 쓰고 checkpoint/manifest commit 뒤 final snapshot에 포함한다. task마다 바로 final path에 append하면 duplicate file이 생길 수 있다.

### external API

idempotency key를 지원하는지 확인한다. 지원하지 않으면 effect ledger와 reconciliation 또는 별도 delivery service를 둔다.

## dedup

### key 선택

- producer event ID
- source partition+offset
- transaction ID+row key+operation sequence
- deterministic business event key

payload hash는 안정성과 collision/semantic 문제를 검토한다.

### scope

- partition 내부
- entity key 내부
- window 내부
- 전체 retention 기간

scope를 문서화하지 않으면 replay 보장이 과장된다.

### TTL

state retention보다 늦게 duplicate가 오면 다시 반영될 수 있다. online dedup TTL과 historical backfill 경로를 분리한다.

### approximate dedup

Bloom filter 같은 구조는 false positive로 정상 record를 버릴 수 있다. loss 허용 여부와 secondary exact store를 검토한다.

## state schema evolution

job update 때 과거 checkpoint state를 새 code가 읽어야 한다.

- state key/namespace 변경
- serializer schema 변경
- timer format 변경
- operator topology 변경
- rescale/repartition

변경 전 savepoint/checkpoint compatibility, migration tool, rollback 가능성을 시험한다. input schema compatibility만 확인해서는 부족하다.

## backpressure

sink가 느리면 upstream state와 queue가 늘어난다.

관찰:

- records in/out rate
- busy/backpressured/idle time
- pending async requests
- checkpoint duration와 alignment
- state size
- sink commit latency

buffer를 크게 만드는 것은 지연을 숨기고 failure replay를 키울 수 있다.

## 실패 모드

### source offset committed too early

state/sink 반영 전에 offset을 commit해 crash 시 loss가 생긴다.

### sink effect before checkpoint

외부 API를 호출한 뒤 checkpoint 전에 crash해 replay가 같은 effect를 다시 만든다. idempotency key나 effect ledger가 필요하다.

### dedup TTL shorter than retry

장기 outage 뒤 replay가 TTL을 넘어 duplicate를 만든다. retention과 replay contract를 맞춘다.

### random output ID

retry마다 새 ID를 만들어 unique constraint가 dedup하지 못한다. source identity 기반 deterministic ID를 사용한다.

### incompatible state upgrade

새 job이 old checkpoint를 읽지 못해 state를 버리고 처음부터 실행한다. state migration과 rollback rehearsal가 필요하다.

### exactly-once label without consumer rule

engine 내부 state는 정확하지만 sink가 append하고 consumer가 duplicate를 합산한다. end-to-end outcome을 검사한다.

## 검증 전략

- 같은 event를 여러 번 입력해 결과가 한 번만 반영되는지 확인한다.
- sink 성공 뒤 checkpoint 전 crash를 주입한다.
- checkpoint 뒤 source position commit 전 crash를 주입한다.
- rescale 후 key별 state가 유지되는지 확인한다.
- TTL 경계 전후 duplicate를 입력한다.
- state schema upgrade와 rollback을 fixture로 실행한다.
- source count/sum과 sink result를 reconciliation한다.

## 검증 질문

1. state의 key와 lifetime은 무엇인가?
2. checkpoint가 source·state·timer·sink 중 어디까지 묶는가?
3. duplicate effect를 막는 최종 boundary는 어디인가?
4. dedup key와 TTL이 실제 retry/backfill 범위를 덮는가?
5. external side effect가 idempotency key를 지원하는가?
6. state schema와 topology upgrade를 restore해 봤는가?

## 연결 연습

- [`event-time windows`](../../exercises/03-stream-processing/01-event-time-windows/README.md)에 duplicate와 restart fixture를 추가한다.
- [`examples/windowing_model.py`](../../examples/windowing_model.py)의 pane ID와 correction version을 검토한다.

## 완료 기준

- processing guarantee를 end-to-end effect 범위로 제한해 설명한다.
- source position, operator state와 sink commit의 recovery 관계를 설계한다.
- dedup key·scope·TTL과 backfill 경로를 명시한다.
- checkpoint/state upgrade를 배포 계약에 포함한다.
