# 데이터 제품과 소유권

## 학습 목표

이 문서를 마치면 다음을 할 수 있어야 한다.

- pipeline을 “파일을 옮기는 작업”이 아니라 producer와 consumer 사이의 장기 계약으로 설명한다.
- dataset의 grain, key, 의미, freshness, 품질과 변경 책임을 문서화한다.
- source system의 업무 정본과 분석용 파생 상태를 구분한다.
- task 성공, file 존재와 consumer가 신뢰할 수 있는 데이터 제품의 차이를 설명한다.

## 핵심 모델

데이터 제품은 table 이름이나 object storage 경로만을 뜻하지 않는다. 최소한 다음 계약의 묶음이다.

```text
producer가 제공하는 사실
+ record의 의미와 식별 방법
+ 언제 어느 범위가 사용 가능해지는지
+ 변경·correction·삭제가 반영되는 방식
+ consumer가 검사할 수 있는 품질과 lineage
+ 실패·지연·폐기 때 연락하고 복구하는 책임
```

좋은 pipeline은 data를 “어디로” 보낼지만 정하지 않는다. **누가 어떤 의미를 언제까지 유지하고, 소비자가 무엇을 근거로 신뢰할지**를 정한다.

## source of truth와 파생 상태

운영 서비스의 주문 table이 업무 정본이라고 해도 분석 dataset이 단순 복사본인 것은 아니다.

예를 들어 일별 매출 dataset은 다음 결정이 필요하다.

- 주문 생성 시각과 결제 완료 시각 중 어느 날의 매출인가?
- 취소·환불은 원래 날짜를 수정하는가, correction record를 추가하는가?
- test 계정과 내부 주문은 제외하는가?
- 통화 변환은 어느 환율 시점과 판본을 사용하는가?
- 늦게 도착한 결제가 이전 일자의 집계를 다시 바꾸는가?

이 결정이 없다면 column 이름이 정확해도 의미가 불안정하다.

### 세 높이

```text
업무 정본
  source 서비스가 명령과 transaction으로 소유하는 상태

canonical data
  여러 source 표현을 안정된 identity·time·schema로 정규화한 record

consumer product
  분석, ML, 검색, 리포팅 목적에 맞춘 파생 table·feature·index
```

각 높이는 다른 소유자가 있을 수 있다. canonical layer가 모든 조직에 반드시 필요한 것은 아니지만, 동일한 정규화 규칙을 여러 consumer가 반복하면 공통 소유권을 검토해야 한다.

## grain: 한 행이 무엇인가

가장 먼저 한 record의 grain을 한 문장으로 고정한다.

좋은 예:

> `order_payments`의 한 행은 하나의 결제 시도이며, 재시도는 다른 `payment_attempt_id`를 가진다.

모호한 예:

> 주문별 결제 데이터다.

두 번째 문장은 부분 결제, 재시도, 환불, 결제 수단 변경을 표현하지 못한다.

### grain 검토 질문

- 한 업무 사건이 여러 행을 만드는가?
- 한 행이 여러 업무 사건을 합치는가?
- update가 같은 사실의 수정인가, 새로운 사건인가?
- join 뒤 행 수가 늘어나는 것이 정상인가?
- snapshot table과 event table의 grain을 혼동하지 않았는가?

grain이 불명확하면 uniqueness 검사와 집계가 모두 불명확해진다.

## identity와 key

key에는 서로 다른 역할이 있다.

| 종류 | 역할 | 예 |
|---|---|---|
| business key | 업무 객체를 식별 | `order_id` |
| event key | 하나의 사건 또는 변경을 식별 | `payment_attempt_id`, `event_id` |
| source position | source log에서 재개·순서를 식별 | LSN, offset, file+row |
| partition key | 물리 배치와 병렬성 결정 | `event_date`, customer hash |
| surrogate key | warehouse 내부 관계 안정화 | dimension row key |

하나의 `id`가 모든 역할을 대신한다고 가정하지 않는다. event dedup에 entity key만 쓰면 같은 주문의 두 합법적 변경을 하나로 지울 수 있다. 반대로 business key가 없는 append-only event만 있으면 현재 상태를 만들 때 명시적 fold 규칙이 필요하다.

## producer 계약

producer는 최소한 다음을 제공하거나 제약을 공개한다.

- record schema와 field 의미
- stable identity
- event time과 timezone
- update·delete·correction 표현
- 순서 보장의 범위
- 재전송·중복 가능성
- 초기 snapshot과 이후 증분의 연결 방식
- schema 변경 통지와 호환 기간
- 보존 기간과 재읽기 가능 범위

producer가 내부 table schema를 그대로 공개했다고 계약이 완성되는 것은 아니다. 내부 column은 업무 의미가 아닌 구현 세부일 수 있으며 무통지 변경 가능성이 크다.

## consumer 계약

consumer도 책임이 있다.

- 어떤 field와 의미에 의존하는지 명시한다.
- 필요 freshness와 허용 지연을 정한다.
- late correction을 받을 수 있는 기간을 정한다.
- 잠정 결과와 확정 결과를 구분한다.
- 누락·중복·schema mismatch 때 fail, quarantine, default 중 무엇을 하는지 정한다.
- 더 이상 사용하지 않는 field와 dataset 의존성을 제거한다.

“누군가 쓸 수 있으니 영원히 유지한다”는 계약은 운영할 수 없다. 실제 consumer와 deprecation 절차를 추적해야 한다.

## 네 책임 높이와 인계

한 팀이 여러 역할을 맡을 수 있지만 책임은 섞지 않는다.

| 역할 | 소유하는 결정 | 인계할 근거 |
|---|---|---|
| source owner | 업무 정본, transaction, source schema와 변경 통지 | consistent snapshot 또는 source position, 보존·부하 한계 |
| producer owner | canonical record, grain·identity·time·correction 계약 | schema/semantic version, input coverage, publish·quality 상태 |
| operator owner | 실행, retry, backfill, 비용, 사고와 복구 | run/attempt, input·output snapshot, quality·lineage, runbook |
| consumer owner | 사용하는 field·metric, freshness와 finality 요구 | 실제 의존성, 허용 correction, migration 완료와 sign-off |

`source task success → producer publish → consumer read`를 한 success 상태로 줄이지 않는다. 각 인계에서 owner, version, quality gate와 consumer-visible state를 확인한다. 특히 producer가 schema를 호환되게 바꿔도 consumer가 의미 변경을 승인했다는 뜻은 아니다.

## SLO와 품질 차원

서비스 SLO처럼 데이터 제품도 소비자가 관찰할 수 있는 목표가 필요하다.

### freshness

예:

> UTC 일자 `D`의 `sales_daily` partition은 `D+1 02:00`까지 publish되며 99%의 run이 이를 만족한다.

freshness는 “DAG가 성공한 시각”이 아니라 consumer가 올바른 partition을 읽을 수 있는 시각이다.

### completeness

- source 범위의 기대 record 수
- 필수 entity의 포함 비율
- source position 또는 interval coverage
- late data 허용 범위

### validity

- type과 domain
- non-null 조건
- referential expectation
- state transition 규칙

### uniqueness

반드시 grain과 key에 연결한다. “중복 없음”이 아니라 어떤 key 조합이 어떤 시간 범위에서 유일한지 적는다.

### consistency

서로 다른 dataset이 같은 업무 정의를 사용하고, 합계나 상태가 허용 오차 안에서 대사되는지 확인한다.

## 소유권과 운영 책임

소유자는 코드를 작성한 사람만이 아니다. 다음 책임을 맡는 팀 또는 역할이다.

- 의미와 contract 변경 승인
- pipeline과 dataset on-call 또는 incident routing
- source와 consumer 사이 change coordination
- quality rule과 threshold 유지
- backfill과 correction 승인
- retention·access·deletion 정책 집행
- deprecation과 migration

### ownership metadata 예시

```yaml
dataset: analytics.sales_daily
owner: data-platform/sales
producer: checkout/order-service
consumers:
  - finance/monthly-close
  - growth/revenue-dashboard
grain: one row per sales_date and currency
freshness_slo: D+1 02:00 UTC
correction_window: 35 days
classification: confidential
runbook: runbooks/sales_daily.md
```

YAML 형식 자체보다 정보의 검증 가능성이 중요하다.

## Consumer inventory와 폐기

지원 중인 contract에는 실제 consumer inventory가 있어야 한다.

```text
consumer identity
사용 중인 dataset/schema/field/metric
freshness·finality·correction 요구
owner와 연락 경로
마지막 사용 근거
migration/deprecation 상태
```

Breaking change와 retirement는 다음 순서로 운영한다.

```text
실제 의존성 조사
→ replacement와 old/new 의미 차이 공개
→ dual output 또는 versioned contract
→ consumer별 reconciliation과 canary cutover
→ migration 완료 기록
→ deprecation 기간
→ read 차단·metadata 보존·retention에 따른 physical cleanup
```

Lineage나 query history는 동적 export와 외부 consumer를 놓칠 수 있으므로 owner 확인을 함께 사용한다. 사용자가 없다는 추정만으로 dataset을 지우지 않고, 반대로 owner 없는 가능성만으로 영구 지원하지도 않는다.

## 실패 모드

### task green, data wrong

코드가 예외 없이 끝났지만 source 범위가 잘못됐거나 join이 fan-out을 만들 수 있다. task 상태는 실행 성공일 뿐 데이터 정확성 증거가 아니다.

### silent contract drift

producer가 enum 의미, timezone, null 의미를 바꾸지만 physical type은 같아 schema 검사에 걸리지 않는다. semantic contract와 실제 분포 검사가 필요하다.

### orphan dataset

owner와 consumer가 불명확해 실패해도 영향과 우선순위를 결정할 수 없다. lineage만 있고 운영 책임이 없으면 복구가 늦어진다.

### shared table as integration API

여러 팀이 한 table의 column을 직접 참조하면 source 내부 migration이 사실상 조직 전체 API 변경이 된다. 공개 contract 또는 안정된 view/event 경계를 둔다.

### metric definition fork

팀마다 “활성 사용자”, “매출”, “전환”을 다르게 계산해 서로 맞지 않는 dashboard가 생긴다. 이름 통일이 아니라 grain·filter·time·correction 계약을 통일해야 한다.

## 설계 절차

1. consumer가 내릴 결정을 적는다.
2. 그 결정에 필요한 업무 사실과 grain을 적는다.
3. stable identity와 time을 정한다.
4. source의 update·delete·correction을 파생 상태에 어떻게 반영할지 정한다.
5. publish 단위와 freshness를 정한다.
6. 품질과 reconciliation을 consumer-visible 기준으로 정한다.
7. owner, escalation, change와 deprecation 절차를 정한다.
8. 실제 sample과 실패 사례로 계약을 검토한다.

## 검증 질문

1. 한 행의 grain을 “~당 한 행”으로 말할 수 있는가?
2. entity ID와 event ID, source position을 구분했는가?
3. task 성공과 dataset publish 성공을 구분했는가?
4. late correction이 과거 결과를 바꾸는지, 별도 record를 만드는지 정했는가?
5. consumer가 freshness·completeness를 독립적으로 확인할 수 있는가?
6. owner 부재, source 변경과 backfill 실패 때 누구에게 어떤 근거를 전달하는가?

## 연결 연습

- [`schema evolution`](../../exercises/01-contracts-and-records/01-schema-evolution/README.md)에서 producer와 consumer 호환성 계약을 구현한다.
- 자신의 프로젝트에서 자주 쓰는 report 하나를 골라 grain·key·time·correction·freshness를 한 페이지로 작성한다.
- 동일 metric을 계산하는 두 query가 있다면 filter·join·time zone·late data 처리 차이를 비교한다.

## 완료 기준

- dataset을 path나 table 이름이 아닌 의미·시간·품질·운영 계약으로 설명한다.
- source of truth, canonical record와 consumer product의 소유자를 구분한다.
- grain과 key를 기반으로 uniqueness와 reconciliation 규칙을 제안한다.
- task 성공만으로 데이터가 맞다고 주장하지 않고 소비자 관점의 evidence를 설계한다.
- source·producer·operator·consumer 책임과 인계 근거를 분리한다.
- consumer inventory를 근거로 변경, cutover, deprecation과 retirement를 운영한다.
