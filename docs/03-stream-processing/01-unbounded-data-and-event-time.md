# Unbounded data와 event time

## 학습 목표

- bounded와 unbounded를 실행 방식이 아니라 입력의 완료 가능성으로 구분한다.
- source offset, event time, processing time과 pipeline progress를 분리한다.
- out-of-order와 late event가 예외가 아니라 기본 상태인 이유를 설명한다.
- 동일한 업무 계산을 batch와 stream에서 같은 논리 모델로 표현한다.

## 핵심 모델

unbounded source는 “끝까지 모두 읽었다”는 시점이 없다. 따라서 전체 집합에 대한 계산을 바로 완료할 수 없다.

```text
무한하거나 계속 증가하는 input
→ key 또는 time window로 유한한 상태를 정의
→ progress estimate와 trigger로 중간 결과 emit
→ late data에 대한 수정 정책 적용
→ state와 source position checkpoint
```

streaming은 단순히 작은 batch를 자주 실행하는 것과 같지 않다. event time, state lifetime과 결과 수정이 명시적으로 필요하다.

## bounded와 unbounded

### bounded

- input manifest 또는 snapshot이 유한하다.
- 모든 input을 읽은 뒤 global aggregation을 완료할 수 있다.
- 재실행 시 동일 snapshot을 다시 열 수 있다.

### unbounded

- 새 record가 계속 도착한다.
- global “최종 결과”가 없을 수 있다.
- key, window, session 또는 state TTL로 계산 범위를 제한한다.
- source progress와 checkpoint가 복구의 일부다.

같은 source를 다른 방식으로 볼 수 있다. Kafka topic의 offset 구간 `[100, 200)`은 bounded backfill input이고, 계속 tailing하는 consumer는 unbounded input이다.

## source record와 envelope

stream record는 업무 payload만으로 충분하지 않다.

```yaml
payload: {...}
event_id: evt-123
entity_id: order-17
occurred_at: 2026-08-09T01:03:12Z
source:
  stream: orders
  partition: 3
  offset: 98124
observed_at: 2026-08-09T01:03:13Z
schema_version: 7
```

source metadata는 재개·중복·순서·lineage를 판단하는 근거다. transform 중에 버리기 전에 downstream이 필요한 범위를 검토한다.

## event time

event time은 업무 사건이 속하는 시간이다. source가 제공하거나 deterministic하게 유도한다.

품질 질문:

- 누가 timestamp를 생성하는가?
- clock이 동기화돼 있는가?
- client offline 상태에서 얼마나 늦을 수 있는가?
- timezone과 precision은 무엇인가?
- 수정된 timestamp를 새 event로 보내는가?
- 미래 timestamp와 오래된 timestamp를 어떻게 처리하는가?

## processing time

processing time은 worker가 record를 처리한 wall clock이다.

사용처:

- pipeline latency와 backlog 측정
- processing-time trigger
- timeout과 state cleanup

업무 집계에 쓰면 restart와 backfill 시 결과가 달라질 수 있다.

## out-of-order

순서 역전은 여러 이유로 발생한다.

- 여러 producer와 partition
- retry와 network path 차이
- 모바일 offline queue
- CDC transaction과 connector batching
- broker 재할당과 consumer restart
- batch file의 늦은 도착

전역 timestamp sort를 시도하기보다 계산이 실제로 요구하는 순서 범위를 정한다.

- entity별 version order
- partition별 source order
- session gap
- commutative aggregation
- stale update rejection

## progress

unbounded source에서 “어디까지 처리했는가”는 여러 값으로 나뉜다.

### source position progress

partition별 마지막 checkpoint offset. 재개 위치를 알려주지만 event-time completeness를 직접 말하지 않는다.

### processing backlog

latest source position과 consumer position 차이. record 수 또는 bytes로 볼 수 있다.

### event-time progress

향후 도착할 record의 event time 하한을 추정한다. watermark가 대표적이다.

source offset이 최신이어도 producer가 과거 event를 나중에 보낼 수 있다. offset lag 0과 event-time completeness는 같은 말이 아니다.

## batch와 stream의 통합 모델

동일한 transform을 다음처럼 바라볼 수 있다.

```text
batch
bounded records + fixed interval + final trigger

stream
unbounded records + windows/state + repeated trigger
```

하지만 구현 통합만으로 의미가 같아지지는 않는다. 다음을 일치시켜야 한다.

- event time extraction
- key와 dedup
- window boundary와 timezone
- late correction
- reference data version
- output update/retraction 방식

batch backfill과 live stream 결과를 reconciliation해 같은 논리 계약인지 확인한다.

## restart와 checkpoint

checkpoint에는 보통 다음이 함께 필요하다.

- source positions
- operator keyed state
- timers/window state
- pending output 또는 sink transaction metadata
- schema/transform version

source offset만 저장하면 이미 state에 반영했지만 sink에 commit하지 못한 record를 구분하기 어렵다. source-state-sink commit 경계를 설명해야 한다.

## backlog와 overload

입력 속도가 처리 capacity보다 높으면 backlog가 증가한다.

관찰:

- partition별 lag
- event-time lag
- processing throughput
- state size와 checkpoint duration
- sink latency
- hot key와 backpressure

scale-out 전에 병목이 source read, shuffle, state, serialization, sink 중 어디인지 확인한다.

## 실패 모드

### event time is ingestion time

source의 실제 발생 시각을 잃어 late data와 업무 window가 잘못된다. ingestion time은 별도 field로 유지한다.

### offset lag zero means complete

현재 broker까지 읽었지만 offline client가 과거 event를 아직 보내지 않았을 수 있다. watermark와 correction window가 필요하다.

### global state without bounds

전체 unique user set을 영원히 보관해 state가 무한히 증가한다. window, TTL, approximate structure 또는 external state contract를 선택한다.

### restart loses pending output

offset을 먼저 commit하고 sink write가 실패해 data loss가 생긴다. source-state-sink commit 순서 또는 idempotent replay를 설계한다.

### partition order treated as global

다른 partition의 offset을 비교해 전역 순서를 만든다. ordering 보장을 partition/entity 범위로 제한한다.

## 검증 질문

1. input이 어떤 의미에서 unbounded인가?
2. source position과 event-time progress를 구분하는가?
3. event time의 생성자·timezone·오류 범위는 무엇인가?
4. state는 key, window 또는 TTL로 bounded되는가?
5. restart checkpoint에 source·state·sink 어느 경계가 포함되는가?
6. batch backfill과 live stream이 같은 결과 의미를 갖는가?

## 연결 연습

[`event-time windows`](../../exercises/03-stream-processing/01-event-time-windows/README.md)에서 arrival order가 뒤섞인 event를 event time으로 계산한다.

## 완료 기준

- bounded/unbounded를 input completion 관점에서 설명한다.
- source offset, backlog, watermark와 publish progress를 서로 바꾸어 쓰지 않는다.
- out-of-order와 restart를 포함한 stateful stream 경계를 설계한다.
- batch replay와 live 결과의 의미를 reconciliation할 수 있다.
