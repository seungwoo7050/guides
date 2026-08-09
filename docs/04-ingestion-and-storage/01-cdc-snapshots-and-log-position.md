# CDC snapshot과 log position

## 학습 목표

- query polling과 log-based CDC의 차이를 source semantics로 설명한다.
- 초기 snapshot과 이후 change stream을 틈이나 중복 없이 연결하는 조건을 설명한다.
- transaction boundary, update before/after, delete와 schema change를 downstream record로 보존한다.
- connector restart, retention 초과와 re-snapshot을 복구 절차로 설계한다.

## 핵심 모델

Change Data Capture는 table의 현재 행을 주기적으로 다시 읽는 것과 다르다. source database가 기록한 변경 순서와 position을 읽어 downstream에 전달한다.

```text
consistent snapshot at position P
+ log records strictly after P
→ source state history 또는 current-state projection
```

핵심은 snapshot과 stream 사이의 경계 `P`다. snapshot 중 발생한 변경을 잃거나 두 번 적용하지 않아야 한다.

## polling과 CDC

### updated_at polling

```sql
SELECT *
FROM orders
WHERE updated_at > :last_seen
  AND updated_at <= :cutoff;
```

장점:

- 구현이 단순하다.
- source가 log access를 제공하지 않아도 된다.

한계:

- 같은 timestamp의 tie와 clock precision
- transaction commit 전후 visibility
- hard delete 관찰 불가
- update가 timestamp를 갱신하지 않으면 누락
- large scan과 source 부하
- pagination 중 row 변화

정확히 사용하려면 stable compound cursor, snapshot isolation, delete marker와 reconciliation이 필요하다.

### log-based CDC

source의 transaction log 또는 logical replication stream을 읽는다.

장점:

- insert·update·delete 관찰
- commit order와 source position
- source table full scan 반복 감소

한계:

- log retention과 slot 관리
- schema change 해석
- connector 권한과 source 부하
- transaction이 매우 클 때 buffering
- source-specific semantics

CDC라고 자동으로 무손실인 것은 아니다. connector와 sink 사이의 checkpoint·retry를 검증해야 한다.

## consistent initial snapshot

새 connector는 과거 row와 이후 변경을 모두 전달해야 한다.

### 잘못된 순서

```text
1. table 전체 SELECT
2. SELECT 종료 뒤 현재 log position 기록
3. 그 position부터 stream 시작
```

snapshot 중 commit된 변경이 snapshot 결과와 position 사이에서 누락될 수 있다.

### 필요한 계약

구현은 source마다 다르지만 논리는 다음과 같다.

1. source position `P`를 snapshot 일관성 경계와 함께 확보한다.
2. `P`와 일관된 snapshot을 읽는다.
3. snapshot record에 snapshot marker와 source identity를 붙인다.
4. log `P` 이후의 committed change를 처리한다.
5. snapshot과 log에 같은 row/version이 겹치면 deterministic rule로 합친다.

snapshot이 오래 걸리는 동안 log retention이 충분해야 한다.

## CDC envelope

예시 논리 구조:

```json
{
  "source": {
    "database": "shop",
    "table": "orders",
    "position": "lsn:0/16B6C50",
    "tx_id": "7421",
    "sequence": 3,
    "commit_time": "2026-08-09T03:12:01Z"
  },
  "key": {"order_id": "O-17"},
  "operation": "UPDATE",
  "before": {"status": "NEW"},
  "after": {"status": "PAID"},
  "schema_version": 12,
  "snapshot": false
}
```

모든 connector가 같은 field를 제공하지 않는다. downstream canonical envelope가 어떤 source 보장을 보존하고 어떤 정보를 잃는지 문서화한다.

## transaction boundary

하나의 source transaction이 여러 table과 row를 바꿀 수 있다.

consumer가 row event를 즉시 처리하면 transaction 내부 중간 상태를 볼 수 있다. 필요한 경우 다음을 사용한다.

- transaction begin/end metadata
- transaction ID와 event count/order
- commit 시점까지 buffer
- downstream atomic merge
- 업무적으로 허용되는 eventual projection과 reconciliation

모든 downstream이 source transaction atomicity를 유지할 수 있는 것은 아니다. 어떤 소비자에게 필요한지 구분한다.

## update 모델

### before/after image

둘 다 있으면 change amount, old join key와 audit에 유용하다. source 설정이나 storage 비용 때문에 before가 없을 수 있다.

### patch

변경 field만 전달한다. current state를 만들려면 이전 state가 필요하고 schema default와 null semantics를 주의한다.

### full after image

current-state sink에 적용하기 쉽지만 큰 row와 sensitive field를 반복 전송한다.

## delete와 tombstone

- delete event: key와 before image 또는 reason을 전달
- tombstone: compacted log에서 key의 이전 value 제거를 알림
- soft delete: source row는 남고 flag/status가 바뀜
- retention delete: downstream physical data 제거

서로 같은 의미가 아니다. current-state table은 delete event에서 row를 제거할 수 있지만 audit history는 delete fact를 보존할 수 있다.

## schema change

CDC는 table schema와 log decoding에 의존한다.

검토할 변화:

- column 추가·삭제·rename
- type 변경
- primary key 변경
- table rename
- generated/default column
- large object와 unsupported type

connector가 DDL event를 전달하는지, schema registry와 sink table이 어떤 순서로 바뀌는지 확인한다. rename이 drop+add로 보이면 history 연결이 끊길 수 있다.

## current-state projection

CDC record를 key별 최신 row로 materialize할 때 최소 비교값이 필요하다.

```text
if incoming position/version is newer than stored:
    INSERT/UPDATE -> upsert after image
    DELETE        -> remove or mark deleted
else:
    ignore stale duplicate
```

position이 partition/source별이라면 서로 비교 가능한 범위를 제한한다. multi-table join current state는 transaction과 event-time correction을 별도로 다룬다.

## connector checkpoint와 restart

checkpoint에는 source position과 sink 반영 상태가 연결돼야 한다.

실패 경우:

1. source read 후 sink write 전 crash
2. sink write 후 position commit 전 crash
3. position commit 후 sink durability 전 crash
4. schema change 직전/후 restart

at-least-once replay를 허용하고 sink를 idempotent하게 만드는 방식이 일반적이다. connector label만 믿지 말고 위 네 지점을 시험한다.

## retention 초과와 rebootstrap

connector outage가 source log retention보다 길면 checkpoint position을 더 이상 읽을 수 없다.

runbook:

- 영향 source/table/position 식별
- downstream publish 중지 또는 stale 표시
- 새 consistent snapshot 계획
- live change와 연결할 새 position 확보
- old/current sink 대사
- consumer cutover
- duplicate/omission 검증
- old state 정리

“offset을 최신으로 옮기고 계속”하면 outage 구간 변경을 잃는다.

## source 부하와 권한

- snapshot scan의 I/O와 lock/transaction 영향
- replication slot/log retention disk
- connector 계정의 최소 권한
- PII column의 불필요한 capture
- schema metadata 접근
- network encryption과 credential rotation

일반 보안 원리는 `cybersecurity`와 `web-infra`가 소유한다. 이 문서는 데이터 capture 범위와 source 운영 영향만 다룬다.

## 실패 모드

### snapshot-stream gap

snapshot 완료 뒤 position을 잡아 중간 변경을 잃는다.

### delete ignored

after image만 처리해 source에서 삭제된 row가 sink에 남는다.

### stale replay overwrites current

position/version 비교 없이 replay 순서대로 upsert한다.

### log retention exhaustion

connector가 멈췄는데 replication slot 때문에 source disk가 가득 찬다. lag와 retained bytes alert, pause/drop 정책이 필요하다.

### primary key change

old key delete와 new key insert 관계를 처리하지 않아 두 row가 남는다.

### huge transaction

connector나 downstream buffer가 한 transaction 전체를 memory에 보관하다 실패한다. transaction size limit와 spill/backpressure를 검토한다.

## 검증 질문

1. snapshot과 stream의 일관성 position은 무엇인가?
2. source transaction과 row order를 어느 범위까지 보존하는가?
3. insert·update·delete·key change가 sink에 어떻게 적용되는가?
4. duplicate/stale event를 어떤 position으로 거부하는가?
5. schema change 배포 순서와 rollback은 무엇인가?
6. checkpoint가 retention을 벗어나면 어떤 re-snapshot 절차를 쓰는가?
7. source DB에서 snapshot·slot·lag의 운영 비용을 관찰하는가?

## 연결 연습

[`CDC snapshot merge`](../../exercises/04-ingestion-and-storage/01-cdc-snapshot-merge/README.md)에서 snapshot row와 log change를 source position 기준으로 합친다.

## 완료 기준

- snapshot+position+stream을 하나의 무손실 capture 계약으로 설명한다.
- transaction, delete, key와 schema change를 downstream에 보존한다.
- connector restart와 retention 초과를 실제 복구 절차로 설계한다.
- source와 sink를 key·count·position으로 reconciliation한다.

## 공식 자료 연결

Debezium architecture와 source connector 문서의 snapshot, log-based change event 개념을 참고한다. 링크는 [`reference/official-sources.md`](../../reference/official-sources.md)에 있다.
