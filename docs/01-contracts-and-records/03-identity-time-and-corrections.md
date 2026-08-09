# Identity, 시간과 correction

## 학습 목표

- entity identity, event identity, source position과 실행 identity를 분리한다.
- event time, observed time, ingestion time, processing time과 publish time을 구분한다.
- update·delete·late correction이 과거 결과를 어떻게 바꾸는지 명시한다.
- dedup과 ordering이 어떤 key와 범위에서만 유효한지 설명한다.

## 핵심 모델

데이터 엔지니어링의 많은 오류는 “무슨 사건인지”와 “언제 일어났는지”를 한 field에 몰아넣을 때 생긴다.

```text
entity identity      어떤 업무 객체인가
record/event identity 어떤 사실 또는 변경인가
source position       source에서 어디까지 읽었는가
run identity          어떤 pipeline 실행이 만들었는가

occurred_at           업무 세계에서 사건이 발생한 시각
observed_at           source가 사건을 관찰·기록한 시각
ingested_at           pipeline 경계에 들어온 시각
processed_at          transform이 처리한 시각
published_at          consumer가 읽을 수 있게 된 시각
```

각 시간이 다른 질문에 답한다. 하나의 `timestamp`로 대체하지 않는다.

## entity와 event

예를 들어 주문 `O-17`은 여러 사건을 가진다.

```text
order_created
payment_authorized
address_corrected
order_cancelled
refund_completed
```

`order_id`는 entity key다. 각 사건을 구분하려면 `event_id` 또는 source transaction+position이 필요하다.

### 잘못된 dedup

`order_id`만으로 dedup하면 생성 이후의 합법적 변경을 모두 제거할 수 있다.

### 불안정한 event ID

payload 전체 hash를 event ID로 쓰면 non-semantic metadata나 serialization 순서가 바뀔 때 같은 사건이 다른 ID가 된다. 반대로 업무상 다른 두 사건이 우연히 같은 payload를 가질 수 있다.

가능하면 producer가 stable event ID를 생성한다. 없다면 source partition+offset, transaction ID+row identity, immutable file ID+row number처럼 재현 가능한 compound identity를 사용한다.

## source position

source position은 업무 identity가 아니라 읽기 진행 상태다.

예:

- Kafka topic partition과 offset
- PostgreSQL LSN과 transaction order
- object key, version ID와 row group
- API cursor와 page token
- file snapshot manifest ID

position은 다음에 사용한다.

- restart 후 재개
- snapshot과 change stream 연결
- 중복 범위 판단
- 특정 결과의 source coverage 증명

모든 source position이 전역 순서를 제공하지는 않는다. partition별 offset은 같은 partition 안에서만 순서를 보장한다. 여러 partition의 사건을 wall clock으로 완전 정렬할 수 있다고 가정하지 않는다.

## event time과 processing time

### event time

업무 결과가 어느 시간 구간에 속하는지 결정한다. 예를 들어 사용자의 클릭이 10:03에 발생했지만 네트워크 단절 뒤 10:20에 도착해도 10:00~10:05 event-time window에 속할 수 있다.

### processing time

시스템이 실제로 처리하는 시각이다. 운영 지연과 resource scheduling을 측정하는 데 유용하지만 업무 발생 순서를 대신하지 않는다.

### observed/ingested time

source가 사실을 기록한 시각과 pipeline이 받은 시각을 분리하면 upstream 지연과 pipeline 지연을 구분할 수 있다.

```text
source delay   = observed_at - occurred_at
ingestion delay = ingested_at - observed_at
processing delay = published_at - ingested_at
end-to-end delay = published_at - occurred_at
```

clock skew와 missing timestamp 때문에 값이 음수가 될 수 있다. 음수를 바로 잘라내지 말고 clock quality 문제로 분류한다.

## timezone과 calendar

- 저장과 전달에는 가능한 한 timezone-aware UTC instant를 사용한다.
- 업무 일자·월 마감은 지역 timezone과 calendar 규칙을 별도 contract로 둔다.
- `2026-08-09` 같은 date는 instant가 아니다.
- daylight saving 전환이 있는 지역에서는 하루가 항상 24시간이 아니다.
- client timestamp를 신뢰할 수 없다면 신뢰 수준과 fallback을 기록한다.

“UTC로 바꾸면 모든 시간 문제가 해결된다”는 말은 틀리다. 업무 grouping에 어떤 timezone을 쓸지 여전히 결정해야 한다.

## update와 correction 모델

### overwrite snapshot

현재 상태만 필요하면 business key별 최신 상태를 materialize할 수 있다. 그러나 과거 상태와 correction 경로를 잃을 수 있다.

### append-only event

각 변경을 보존하고 fold 규칙으로 현재 상태를 만든다. ordering, duplicate와 schema evolution을 더 명확히 처리해야 한다.

### effective dating

`valid_from`, `valid_to`로 사실이 유효한 업무 기간을 표현한다. pipeline이 record를 알게 된 시각과 구분하려면 system time도 필요할 수 있다.

### correction record

원본을 삭제하지 않고 `reverses_event_id`, `correction_of`, signed amount 같은 방식으로 수정 사실을 남긴다. 재무·감사 영역에서 유용하다.

### restatement

과거 partition 또는 table snapshot을 다시 계산해 교체한다. consumer가 snapshot identity와 변경 통지를 관찰할 수 있어야 한다.

## delete 의미

delete는 여러 의미를 가질 수 있다.

- 업무 객체가 취소·폐기됨
- source 내부 row가 compact됨
- 개인정보 삭제 요구
- retention 만료
- CDC tombstone으로 key 제거

sink에서 무조건 row를 지우면 audit나 correction 요구를 깨뜨릴 수 있고, 무조건 보존하면 개인정보·retention 의무를 위반할 수 있다. delete reason과 downstream propagation 계약이 필요하다.

## late data와 correction window

모든 과거를 영원히 수정하는 것은 비싸고 운영하기 어렵다. 제품별 correction window를 정한다.

예:

```text
0~2일 늦음     자동 재집계와 즉시 publish
3~35일 늦음    일일 correction run
35일 초과      quarantine 후 owner 승인
회계 마감 이후 correction journal로 별도 기록
```

window는 단지 비용 정책이 아니다. consumer가 결과의 finality를 해석하는 계약이다.

## dedup 범위와 보존

중복 제거 상태를 영원히 보관할 수 없는 경우 TTL을 둔다. 그러면 보장은 다음처럼 제한된다.

> 같은 `event_id`가 14일 안에 다시 도착하면 한 번만 반영한다. 14일 이후 replay는 별도 backfill namespace와 output replace 계약을 사용한다.

TTL보다 오래된 replay를 online dedup에 넣으면 과거 duplicate가 다시 반영될 수 있다. backfill과 live processing의 identity namespace 또는 publish 경계를 분리한다.

## ordering

전역 순서가 필요하다는 요구를 먼저 의심한다.

- entity별 상태 전이는 entity key partition 안의 순서면 충분한가?
- commutative aggregation으로 순서 의존을 제거할 수 있는가?
- version number 또는 source position으로 stale update를 거부할 수 있는가?
- 서로 다른 source의 사건은 causal relation만 필요한가?

wall clock timestamp만 비교하면 clock skew와 같은 timestamp tie를 처리하지 못한다.

## 실패 모드

### processing time으로 업무 집계

재처리 시각에 따라 과거 결과가 달라진다. event time과 deterministic calendar를 사용한다.

### entity key를 event key로 사용

합법적 여러 변경이 dedup된다. grain과 event identity를 다시 정의한다.

### late update overwrites new state

오래된 event가 늦게 도착해 최신 상태를 덮는다. version/source position 또는 domain transition을 검사한다.

### missing delete

insert/update만 처리해 sink에 삭제된 row가 영원히 남는다. tombstone과 hard/soft delete 의미를 contract에 포함한다.

### local time ambiguity

DST 전환 구간의 같은 local time이 두 instant를 가리킨다. timezone-aware source와 disambiguation policy가 필요하다.

### replay changes IDs

run마다 무작위 surrogate/event ID를 만들면 같은 입력의 재처리가 새 record를 만든다. source identity 기반 deterministic ID 또는 replace publish를 사용한다.

## 검증 질문

1. entity, event, source position과 run ID를 각각 말할 수 있는가?
2. 업무 grouping은 어느 timestamp와 timezone을 사용하는가?
3. timestamp가 없거나 잘못됐을 때 fallback과 품질 표시는 무엇인가?
4. update·delete·correction은 append, overwrite, reversal 중 어떤 방식인가?
5. late data가 과거 결과를 언제까지 자동 변경하는가?
6. dedup state의 TTL과 replay 범위가 일치하는가?
7. ordering 보장은 전역, partition, entity 중 어디까지인가?

## 연결 연습

- [`event-time windows`](../../exercises/03-stream-processing/01-event-time-windows/README.md)에서 event time과 arrival order를 분리한다.
- [`CDC snapshot merge`](../../exercises/04-ingestion-and-storage/01-cdc-snapshot-merge/README.md)에서 source position과 stale update를 처리한다.
- 자신의 event schema에 `occurred_at`, `observed_at`, `event_id`, `entity_id`, `source_position`을 표시하고 누락된 계약을 기록한다.

## 완료 기준

- 각 identity와 timestamp가 답하는 질문을 구분한다.
- replay·dedup·ordering 보장을 key와 시간 범위로 제한해 표현한다.
- delete와 correction이 downstream state를 바꾸는 규칙을 명시한다.
- late data와 finality를 소비자에게 숨기지 않는다.
