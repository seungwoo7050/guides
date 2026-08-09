# 분석 모델과 역사 보존

## 학습 목표

이 문서를 마치면 다음을 할 수 있어야 한다.

- 분석 dataset의 grain을 먼저 고정하고 fact, dimension과 measure를 구분한다.
- event, current state, periodic snapshot과 accumulating snapshot이 서로 어떤 질문에 답하는지 설명한다.
- slowly changing dimension과 late-arriving fact를 valid time·system time·source position으로 다룬다.
- additive, semi-additive, non-additive measure를 잘못 합산하지 않는다.
- 과거 fact를 당시 dimension 상태와 연결하는 as-of join과 version 계약을 설계한다.
- metric 이름이 아니라 분자·분모·필터·시간·중복·수정 규칙을 데이터 계약으로 기록한다.

관계형 정규화와 일반 schema 설계는 [`database-systems`](https://github.com/seungwoo7050/guides/tree/database-systems)가 소유한다. 이 문서는 **분석 소비자가 시간에 따라 변하는 업무 사실을 어떤 grain과 역사로 읽는가**에 집중한다.

## 핵심 모델

```text
업무 사건과 상태
→ 분석 질문
→ grain
→ fact와 dimension
→ 시간·version 연결
→ measure와 aggregation 규칙
→ consumer metric
```

좋은 분석 모델은 table 모양에서 시작하지 않는다. 먼저 소비자가 묻는 질문과 한 record가 표현할 사실을 정한다.

예:

```text
질문: 날짜·통화별 실제 결제액은 얼마인가?
grain: 결제 event 1개
fact key: payment_id
업무 시간: payment_captured_at
measure: captured_amount_minor
수정: refund event를 별도 fact로 기록
```

```text
질문: 매일 자정의 계좌 잔액은 얼마인가?
grain: account_id × snapshot_date
업무 시간: snapshot_date boundary
measure: closing_balance_minor
수정: source correction version을 가진 새 snapshot
```

같은 source table이라도 질문이 다르면 올바른 grain과 시간 모델이 다르다.

## Fact

fact는 측정하거나 집계할 수 있는 업무 사건 또는 상태를 표현한다.

### Transaction fact

업무 사건 하나를 한 record로 둔다.

```text
order placed
payment captured
refund issued
shipment delivered
```

장점:

- source event와 stable identity가 명확하다.
- late event와 correction을 추가 event로 보존하기 쉽다.
- 임의 기간을 다시 집계할 수 있다.

주의:

- 여러 event를 한 row에 덮어쓰면 사건의 순서와 correction을 잃는다.
- source transaction과 분석 event의 경계를 문서화해야 한다.

### Periodic snapshot fact

일·시간·월처럼 일정한 경계의 상태를 저장한다.

```text
account_id × snapshot_date
inventory_item × warehouse × hour
subscription × billing_month
```

장점:

- 특정 시점 상태 질의가 단순하다.
- source가 history를 보존하지 않아도 정기 상태를 남길 수 있다.

주의:

- snapshot이 누락된 날과 값이 0인 날을 구분해야 한다.
- snapshot 생성 기준 시각과 timezone을 명시해야 한다.
- 같은 상태를 반복 저장하므로 보존·압축 비용이 커질 수 있다.

### Accumulating snapshot fact

하나의 업무 흐름이 여러 milestone을 지날 때 한 row를 갱신한다.

```text
order_created_at
paid_at
packed_at
shipped_at
delivered_at
```

처리 lead time을 보기 쉽지만 다음 계약이 필요하다.

- 어떤 key가 한 업무 흐름을 식별하는가?
- milestone correction을 overwrite하는가, version history를 남기는가?
- 흐름이 취소·재개·분기될 때 한 row 모델이 여전히 맞는가?

사건 자체의 audit가 중요하면 transaction fact를 함께 보존한다.

### Factless fact

measure가 없어도 관계나 사건의 존재가 분석 대상일 수 있다.

```text
student attended class
user was eligible for campaign
device entered region
```

row count가 measure 역할을 하지만 중복과 grain을 명확히 해야 한다.

## Dimension

dimension은 fact를 분류하고 설명하는 속성 집합이다.

```text
customer
product
store
campaign
currency rule
```

분석 dimension의 핵심 질문은 “현재 값이 무엇인가?”뿐 아니라 “fact가 발생했을 당시 어떤 값이었는가?”다.

### Natural key와 surrogate key

- natural key: source 업무 entity를 식별한다.
- surrogate key: warehouse 안에서 dimension의 특정 version row를 식별한다.

예:

```text
customer_id = C42             natural key
customer_version_key = 9012   특정 역사 version
```

surrogate key를 사용한다고 source identity가 사라지는 것은 아니다. source key, valid interval, source position과 version 생성 근거를 함께 보존한다.

## Slowly changing dimension

### Type 1: 현재 값으로 교체

과거 fact를 조회해도 현재 dimension 속성을 본다.

적합한 예:

- 오탈자 수정
- history가 의미 없는 표시 이름 정리

위험:

- 과거 보고서 결과가 오늘 다시 실행했을 때 달라질 수 있다.
- 실제 역사와 단순 data correction을 구분하지 못할 수 있다.

### Type 2: version row 추가

속성이 바뀔 때 새 version을 만들고 유효 기간을 둔다.

```text
customer_id
customer_version_key
segment
valid_from
valid_to
source_position
is_current
```

불변식:

- 같은 natural key의 valid interval이 의도 없이 겹치지 않는다.
- 각 fact의 event time이 정확히 한 dimension version과 연결된다.
- 경계는 `[valid_from, valid_to)`처럼 일관된다.
- source correction으로 과거 interval을 수정할 때 affected fact를 다시 대사한다.

`is_current`는 편의 column이지 history 판정의 유일한 근거가 아니다.

### Type 3과 혼합 모델

현재 값과 직전 값을 같은 row에 보존하거나 일부 속성만 history로 관리할 수 있다. field별 변화 의미와 소비자 요구가 명확할 때만 사용한다. “SCD type 번호” 자체보다 어떤 역사 질문을 보장하는지가 중요하다.

## Valid time과 system time

두 종류의 시간을 구분한다.

```text
valid time
업무 세계에서 그 값이 사실이었던 기간

system time
데이터 플랫폼이 그 사실을 알고 저장한 기간
```

예:

- 고객의 등급은 8월 1일부터 GOLD였지만 source correction은 8월 9일 도착했다.
- `valid_from=2026-08-01`, `known_at=2026-08-09`가 된다.

valid time만 보존하면 “당시 시스템이 무엇을 알고 있었는가?”를 재현하기 어렵다. system time만 보존하면 업무 역사에 맞는 as-of 분석을 하기 어렵다. 모든 dataset이 bitemporal이어야 하는 것은 아니지만 어느 시간을 보존하고 포기했는지 명시한다.

## As-of join

과거 fact와 당시 dimension version을 연결한다.

```text
fact.dimension_natural_key = dimension.natural_key
AND fact.event_time >= dimension.valid_from
AND fact.event_time <  dimension.valid_to
```

실제 구현에서는 다음을 검증한다.

- fact 하나에 dimension version이 0개 또는 2개 이상 연결되지 않는가?
- timezone과 timestamp precision이 같은가?
- open-ended `valid_to` 표현이 일관적인가?
- late-arriving dimension이 들어왔을 때 기존 unmatched fact를 다시 연결하는가?
- source position상 더 오래된 correction이 최신 version을 덮지 않는가?

현재 dimension table과 단순 join하면 과거 결과가 현재 분류로 다시 쓰일 수 있다.

## Late-arriving fact와 dimension

### Late-arriving fact

업무 발생 시각보다 늦게 수집된 fact다.

정책 선택:

- 원래 event-time partition을 수정한다.
- correction table/event를 추가한다.
- 마감 이후에는 quarantine하고 승인된 backfill로 반영한다.

어떤 방식을 선택하든 consumer-visible version과 correction 범위를 명시한다.

### Late-arriving dimension

fact는 도착했지만 당시 dimension version이 아직 없다.

선택:

- unknown surrogate key에 임시 연결한 뒤 재처리한다.
- fact publish를 지연한다.
- natural key만 보존하고 query-time as-of join을 수행한다.

unknown을 현재 dimension에 임의로 연결하면 조용한 역사 오염이 생긴다.

## Measure와 aggregation

### Additive measure

모든 관심 dimension과 시간에 합산할 수 있다.

```text
payment_amount
units_sold
request_count
```

### Semi-additive measure

일부 dimension에는 합산할 수 있지만 시간에는 그대로 합산할 수 없다.

```text
account balance
inventory level
active subscription state
```

일별 closing balance를 한 달 동안 합하면 월말 잔액이 되지 않는다. last, average, minimum 같은 시간 aggregation 계약이 필요하다.

### Non-additive measure

직접 합산하면 의미가 없다.

```text
ratio
percentage
average
unique user count
quantile
```

평균의 평균 대신 분자와 분모를 보존하거나 가중치를 사용한다. unique count의 approximate sketch를 사용하면 merge 가능성과 오차 범위를 계약에 포함한다.

## Metric 계약

metric 이름만으로 의미가 고정되지 않는다.

```text
metric: conversion_rate
numerator: paid orders
numerator grain: order_id
numerator event time: paid_at
 denominator: eligible sessions
filter: internal/test account 제외
window: Asia/Seoul calendar day
late correction: 7일
refund treatment: 결제 전환은 유지, 매출 metric에서 별도 차감
version: metric-contract-v3
```

metric 계약에는 최소한 다음이 필요하다.

- 분자와 분모
- 각 grain과 stable key
- filter와 exclusion
- event time·timezone·window
- join과 attribution 규칙
- duplicate·correction·delete
- missing/unknown 값
- finality와 revision

semantic layer나 BI tool이 metric을 중앙화해도 source contract와 history가 잘못되면 결과는 정확하지 않다.

## 실패 모드

### Grain mismatch

주문 grain과 주문 항목 grain을 join한 뒤 주문 금액을 합해 금액이 항목 수만큼 늘어난다. join 전후 cardinality와 key uniqueness를 검사한다.

### Current dimension rewrites history

과거 fact를 현재 고객 segment와 join해 지난달 보고서가 매일 바뀐다. as-of version 또는 pinned dimension snapshot을 사용한다.

### Overlapping SCD intervals

한 fact가 dimension version 두 개에 연결돼 중복된다. natural key별 interval overlap 검사를 publish gate에 둔다.

### Missing dimension silently dropped

inner join이 late dimension의 fact를 제거한다. unmatched count와 key를 별도로 측정하고 정책에 따라 quarantine 또는 unknown 처리한다.

### Average of averages

그룹별 평균을 단순 평균해 전체 평균이 틀린다. 합계와 count처럼 merge 가능한 구성 요소를 보존한다.

### Snapshot summed over time

일별 잔액을 월 합계로 계산한다. measure의 semi-additive 시간 규칙을 contract에 기록한다.

### Metric definition drift

서로 다른 팀이 같은 이름의 active user를 다른 event, timezone과 dedup으로 계산한다. versioned metric contract와 consumer migration을 사용한다.

## 검증 질문

1. dataset의 한 row가 정확히 무엇을 뜻하는가?
2. source event와 current state 중 어느 것을 보존하는가?
3. fact의 event time과 dimension의 valid time을 어떻게 연결하는가?
4. 과거 결과를 재실행할 때 어떤 dimension/reference snapshot을 고정하는가?
5. measure는 어떤 dimension과 시간 범위에서 합산 가능한가?
6. unmatched, duplicate와 overlapping history를 어떤 검사로 찾는가?
7. metric의 분자·분모·filter·timezone·correction version을 다시 찾을 수 있는가?

## 연결 연습

[`batch 데이터 제품 capstone`](../../exercises/06-capstones/01-batch-data-product/README.md)의 `data-contract.md`에 다음을 추가한다.

- payment와 refund fact의 grain
- account/customer dimension의 history 전략
- internal account 분류의 as-of snapshot
- gross/refund/net measure의 additive 범위
- 과거 correction이 영향을 주는 partition과 metric version

`input-manifest.json`에는 dimension/reference snapshot ID를 고정하고 `reconciliation.md`에는 unmatched fact와 SCD interval overlap 검사를 추가한다.

## 완료 기준

- fact, dimension, snapshot을 table 이름이 아니라 분석 질문과 grain으로 구분한다.
- Type 1/2 선택이 과거 결과에 미치는 영향을 설명한다.
- fact event time과 dimension valid interval을 이용한 as-of join을 설계한다.
- late fact/dimension과 history correction의 재처리 범위를 정한다.
- additive·semi-additive·non-additive measure를 구분하고 올바른 aggregation을 기록한다.
- metric 의미를 versioned contract로 만들고 consumer migration과 대사 기준을 제시한다.
