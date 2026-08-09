# Schema evolution과 호환성

## 학습 목표

- physical schema 변화와 semantic contract 변화를 구분한다.
- writer schema와 reader schema 관점에서 backward·forward 호환성을 설명한다.
- field 추가·삭제·rename·type 변경을 producer/consumer 배포 순서와 함께 설계한다.
- file, event, table이 장기간 보존될 때 과거 data를 계속 읽는 방법을 검토한다.

## 핵심 모델

schema는 data의 모양만이 아니라 producer와 consumer가 교환하는 판본 계약이다.

```text
writer schema
  producer가 record를 직렬화할 때 사용한 schema

reader schema
  consumer가 record를 해석할 때 기대하는 schema

compatibility rule
  서로 다른 판본이 공존할 때 허용되는 변화와 배포 순서
```

stream과 data lake에서는 새 코드가 오래된 record를 읽고, 이전 코드가 새 record를 잠시 읽는 혼합 판본이 흔하다. 현재 table만 맞는지 확인해서는 부족하다.

## 세 종류의 변화

### 표현 변화

- field 추가·삭제
- type 변경
- nested 구조 변경
- enum symbol 변경
- nullable/default 변경

serialization과 reader 호환성에 직접 영향을 준다.

### 의미 변화

- `amount`의 단위가 cent에서 won으로 바뀜
- `created_at`이 client time에서 server commit time으로 바뀜
- `status=ACTIVE`의 업무 정의가 바뀜
- 빈 문자열과 `null`의 의미가 바뀜

physical schema가 같아도 consumer 결과가 깨진다. schema registry만으로 막을 수 없다.

### 운영 변화

- topic/table/path 변경
- partition key 변경
- retention 단축
- update와 delete 전달 방식 변경
- ordering 보장 범위 변경

schema 외 계약이므로 별도 migration과 consumer 확인이 필요하다.

## 호환성 방향

용어는 “누가 무엇을 읽는가”로 확인한다.

### backward compatibility

새 reader가 이전 writer의 data를 읽을 수 있다.

```text
old data ──> new reader
```

오래 저장된 file을 새 코드가 읽고 과거 partition을 backfill해야 할 때 중요하다.

### forward compatibility

이전 reader가 새 writer의 data를 읽을 수 있다.

```text
new data ──> old reader
```

producer를 먼저 배포하고 consumer가 나중에 올라가는 기간에 중요하다.

### full compatibility

양방향이 가능하다. 모든 변화가 full compatibility를 유지할 수 있는 것은 아니다. 업무 의미가 크게 바뀌면 새 dataset/topic/version을 만드는 편이 명확할 수 있다.

### transitive compatibility

바로 이전 판본만이 아니라 모든 지원 판본과 비교한다. 오래된 file과 장기 보존 consumer가 있다면 최신 두 판본만 맞는 것으로 충분하지 않을 수 있다.

## 변화별 검토

### optional field 추가

대체로 backward-compatible하게 만들 수 있다. 하지만 다음을 확인한다.

- 과거 record에서 field가 없을 때 reader가 사용할 의미 있는 default가 있는가?
- `null`, missing, empty가 구분되는가?
- consumer가 field 존재를 새 feature 활성화 신호로 오해하지 않는가?

“default를 넣으면 호환”은 표현 수준 주장이다. default가 업무 사실을 만들어 내면 안 된다.

### required field 추가

과거 data에는 값이 없다. 다음 경로 중 하나를 선택한다.

1. optional로 추가하고 producer를 배포한다.
2. 과거 data를 backfill하거나 reader가 유도할 수 있는지 확인한다.
3. consumer가 새 field를 사용하도록 이동한다.
4. 품질 검사와 coverage가 충족된 뒤 required로 강화한다.

이는 database expand-contract migration과 유사하지만 file·event retention과 consumer 독립 배포를 함께 고려한다.

### field 삭제

producer에서 바로 제거하지 않는다.

```text
consumer 의존성 조사
→ consumer 읽기 제거
→ deprecation 기간
→ producer write 중단
→ schema와 historical read 정책 정리
```

lineage가 있어도 동적 query, export, 외부 consumer가 누락될 수 있다. 접근 log와 owner 확인을 병행한다.

### rename

많은 format에서 rename은 “old field 삭제 + new field 추가”로 보일 수 있다. alias 기능이 있어도 모든 engine이 같은 방식으로 해석하는지 확인한다.

안전한 일반 경로:

- 새 field를 추가한다.
- 호환 기간 동안 두 field를 일관되게 쓴다.
- consumer를 새 field로 이동한다.
- old field를 폐기한다.

두 field가 어긋나는 상황을 quality rule로 검사한다.

### type 변경

`int`에서 `long` 같은 promotion이 format 규칙상 허용돼도 다음을 확인한다.

- 모든 engine과 language binding이 같은 promotion을 지원하는가?
- precision과 range가 보존되는가?
- partition·sort·join key의 binary 표현이 바뀌는가?
- 기존 statistics와 index가 유효한가?

`string`에서 timestamp, float에서 decimal처럼 의미가 바뀌는 변환은 새 field와 명시적 migration이 더 안전하다.

### enum 변경

새 symbol을 이전 consumer가 모르면 실패하거나 unknown 처리할 수 있다. enum을 closed set으로 쓸지, unknown을 허용할지 계약한다. “기본값으로 OTHER”는 장애를 숨길 수 있으므로 count와 alert를 함께 둔다.

### nested 구조 변경

field path 변경은 projection, flattening, SQL engine, serializer마다 다르게 처리될 수 있다. schema compatibility 검사뿐 아니라 실제 reader matrix를 실행한다.

## schema ID와 canonical form

schema registry를 사용하면 schema content와 ID를 분리할 수 있다. 그러나 ID만 유효하다고 record 의미가 맞는 것은 아니다.

검사 계층:

1. payload가 등록된 schema로 decode되는가?
2. 새 schema가 정책상 호환되는가?
3. field의 semantic contract가 유지되는가?
4. 실제 consumer query와 transform이 혼합 판본에서 동작하는가?
5. 과거 partition을 새 reader로 backfill할 수 있는가?

canonical form과 fingerprint는 동일 schema를 안정적으로 식별하는 데 유용하지만 field 설명, 품질과 업무 의미의 검토를 대체하지 않는다.

## table schema evolution

table format은 column ID를 사용해 rename과 reorder를 안전하게 지원할 수 있다. 그래도 다음은 별도 문제다.

- query engine별 지원 범위
- old snapshot과 new snapshot을 읽는 reader 호환성
- partition evolution 뒤 file pruning
- write schema와 table schema mismatch
- streaming reader가 metadata change를 언제 관찰하는지

metadata-only change라도 소비자 결과와 운영 비용이 바뀔 수 있다.

## schema migration plan

변경 문서에 최소한 다음을 포함한다.

```yaml
change: add order.channel
old_schema: v7
new_schema: v8
compatibility: backward_transitive
producer_order:
  - register v8
  - deploy dual-capable writer
consumer_order:
  - deploy readers accepting missing channel
historical_data:
  - no backfill; missing means UNKNOWN_SOURCE
validation:
  - mixed v7/v8 fixture
  - old partitions read by new job
  - unknown rate dashboard
rollback:
  - writer can emit v7 until cutover complete
sunset:
  - v7 support removed after retention boundary
```

## 혼합 판본과 cutover 증거

계획은 배포 순서만이 아니라 실제 조합의 결과를 남겨야 한다.

| writer | reader | 확인할 data | 판정 근거 |
|---|---|---|---|
| old | old | 기존 production fixture | 변경 전 baseline |
| old | new | 오래된 partition·event | backward와 historical read |
| new | old | 혼합 배포 기간의 새 record | forward 또는 명시적 차단 |
| new | new | 새 field·의미와 correction | 새 contract의 정상 경로 |

의미가 호환되지 않으면 registry 설정을 완화하지 말고 versioned dataset/topic을 사용한다. 안전한 cutover에는 다음 근거가 필요하다.

1. old/new output이 같은 source cutoff와 reference version을 사용한다.
2. key·count·aggregate·sample 차이를 expected/unexplained로 분류한다.
3. 대표적인 canary consumer가 새 결과와 correction/finality를 읽는다.
4. consumer별 migration 상태와 old contract 사용을 추적한다.
5. rollback은 writer, reader, state, dataset pointer 중 어느 높이를 되돌리는지 밝힌다.
6. deprecation 종료 뒤에도 historical record와 lineage를 해석할 metadata를 보존한다.

Dual write가 오래 지속되면 두 contract가 서로 다른 정본이 될 수 있다. Cutover 종료 조건과 mismatch alert를 미리 정한다.

## 실패 모드

### schema check passes, meaning breaks

field type은 같지만 unit이나 timezone이 바뀐다. semantic version과 distribution/reconciliation 검사가 필요하다.

### latest-only compatibility

v1→v2, v2→v3는 호환되지만 v1→v3는 깨질 수 있다. 오래된 data를 읽으면 실패한다. retention과 backfill 요구에 맞춰 transitive 정책을 선택한다.

### default creates false facts

과거 record의 `country`를 `KR`로 default하면 unknown을 사실로 바꾼다. 표현상 읽을 수 있는 것과 업무상 올바른 것은 다르다.

### consumer shadow dependency

ad-hoc query나 export가 field를 사용하지만 catalog에 owner가 없다. 접근 log, query history와 deprecation 공지를 사용한다.

### dual write diverges

rename migration에서 old/new field가 서로 다른 값이 된다. 한 source expression에서 두 값을 만들고 equality 검사와 mismatch alert를 둔다.

## 검증 질문

1. 지원해야 하는 writer와 reader 판본 범위는 무엇인가?
2. 과거 data를 새 코드가 읽어야 하는가?
3. 이전 consumer가 새 data를 읽는 혼합 배포 기간이 있는가?
4. 변화가 표현, 의미, 운영 중 어디에 속하는가?
5. missing, null, default가 각각 어떤 업무 의미인가?
6. incompatible change라면 새 topic/table/version과 migration을 선택했는가?
7. 실제 reader matrix와 historical fixture를 실행했는가?

## 연결 연습

[`schema evolution exercise`](../../exercises/01-contracts-and-records/01-schema-evolution/README.md)에서 field 추가·rename·type 변경을 분류하고, old/new reader matrix를 구현한다.

추가로 자신이 사용하는 event 또는 table schema 하나를 선택해 다음을 작성한다.

- 현재 지원 판본
- reader/writer 배포 순서
- historical read 범위
- incompatible change 절차
- semantic change 검증 방법

## 완료 기준

- backward와 forward 호환성을 읽는 주체 기준으로 설명한다.
- physical compatibility와 semantic correctness를 구분한다.
- field 변화에 대해 producer·consumer·historical data·rollback·sunset 계획을 제시한다.
- schema registry 통과를 최종 품질 증거로 오해하지 않는다.
- old/new writer·reader matrix와 consumer별 cutover 증거를 남긴다.

## 공식 자료 연결

- Apache Avro specification의 schema resolution
- Schema Registry의 compatibility mode 설명
- Apache Iceberg의 schema·partition evolution

검토 링크는 [`reference/official-sources.md`](../../reference/official-sources.md)에 정리한다.
