# Evolution, compaction과 maintenance

## 학습 목표

- schema, partition, sort order와 physical file layout의 변화를 독립적으로 관리한다.
- compaction, snapshot expiration, orphan cleanup을 서로 다른 maintenance 작업으로 구분한다.
- maintenance가 live writer와 reader의 correctness를 깨뜨리지 않도록 conflict와 retention을 설계한다.
- data platform 비용을 단순 storage 용량이 아닌 metadata·scan·rewrite·recovery 비용으로 본다.

## 핵심 모델

데이터 table은 한 번 배치하고 끝나는 산출물이 아니다.

```text
continuous writes
+ schema/partition evolution
+ small files와 deletes
+ snapshots와 metadata history
+ reader/writer version 혼합
→ 반복 maintenance와 검증
```

maintenance는 성능 작업이면서도 data correctness 작업이다.

## schema evolution

column identity를 field name과 분리하는 table format은 rename/reorder를 더 안전하게 처리할 수 있다. 그래도 다음을 확인한다.

- old files에 없는 field의 read semantics
- required 강화 전 coverage
- type promotion과 precision
- nested field identity
- writer schema validation
- engine별 support

schema metadata가 바뀌었다고 old data가 물리적으로 rewrite되는 것은 아니다.

## partition evolution

data volume과 query가 바뀌면 partition spec도 바뀔 수 있다.

예:

```text
spec 1: days(event_time)
spec 2: hours(event_time)
```

새 file은 spec 2, 과거 file은 spec 1을 사용할 수 있다. query engine은 logical predicate를 각 spec에 적용해 file을 prune해야 한다.

주의:

- consumer가 physical path를 조립하는 경우
- overwrite predicate가 여러 spec을 정확히 포함하는지
- retention/compaction job이 old spec을 이해하는지
- partition cardinality와 file size 변화

## sort order evolution

새 write를 자주 filter/join하는 key로 sort하면 data skipping과 compression이 좋아질 수 있다. old file은 이전 order를 유지한다.

sort order는 전역 ordering 보장이 아니다. file 내부 또는 clustering contract의 범위를 명시한다.

## small-file lifecycle

발생 원인:

- 높은 write concurrency
- 짧은 micro-batch
- high-cardinality partition
- retry와 task별 file commit
- sparse late update
- merge/delete file 누적

관찰 지표:

- partition별 file count
- file size p50/p95/p99
- manifest/metadata size
- query planning time
- scanned file/row group 수
- delete file ratio

## compaction

### bin-packing compaction

작은 files를 target size에 맞춰 합친다. record set과 partition semantics는 유지한다.

### sort/clustering compaction

file을 다시 정렬해 pruning/locality를 개선한다. rewrite cost가 크고 concurrent write와 conflict할 수 있다.

### delete materialization

base file에 delete를 적용해 read amplification을 줄인다.

### state compaction

CDC current state나 changelog를 key별 최신 상태로 축약한다. audit/history 요구와 구분한다.

## safe compaction 절차

```text
base snapshot S 선택
→ candidate files 고정
→ 새 files 작성
→ row/key/aggregate 검증
→ S 기준 replace commit 시도
→ conflict면 재계산 또는 안전한 subset retry
→ commit 성공 뒤 old snapshot retention 대기
→ 만료된 file 정리
```

새 file write와 table commit 사이 실패는 orphan을 만든다. orphan cleanup이 live uncommitted file을 지우지 않도록 age와 metadata reference를 검사한다.

## snapshot expiration

snapshot history를 영원히 유지하면 metadata와 old files가 계속 쌓인다. 그러나 expiration은 다음 능력을 없앨 수 있다.

- time travel
- rollback
- 과거 snapshot 기반 audit
- incremental reader의 시작점
- reproducible backfill

정책에 포함할 것:

- 최소 보존 시간/개수
- active reader와 branch/tag
- legal hold
- backfill 최대 lookback
- rollback 목표
- expiration dry-run과 영향 보고

## orphan cleanup

orphan은 storage에는 있지만 어떤 live metadata에서도 참조되지 않는 file이다.

위험:

- long-running writer의 아직 commit되지 않은 file
- delayed catalog visibility
- 다른 environment/catalog가 참조하는 shared path
- clock skew와 잘못된 age

reference graph와 안전한 age threshold를 사용하고, 삭제 전 candidate manifest를 보존한다.

## metadata maintenance

manifest가 너무 많아지면 planning이 느려진다. metadata file rewrite/merge가 필요할 수 있다. data file compaction과 별도 작업으로 관찰한다.

## retention과 삭제

세 종류를 구분한다.

- snapshot metadata retention
- physical file retention
- 업무/개인정보 record retention

snapshot을 만료했다고 개인정보 row가 모든 backup과 derived dataset에서 삭제된 것은 아니다. 반대로 physical file을 너무 일찍 지우면 live snapshot을 깨뜨릴 수 있다.

## 비용 모델

### storage

current files + old snapshots + staging/orphan + backup + delete files

### compute

ingestion + compaction + clustering + backfill + quality/reconciliation

### query

planning metadata + scanned bytes + delete merge + shuffle

### operational

incident, failed rewrite cleanup, schema coordination, catalog recovery

한 비용만 줄이면 다른 비용이 증가할 수 있다. micro-batch를 짧게 해 freshness를 낮추면 small-file와 compaction 비용이 커질 수 있다.

## 실패 모드

### compaction without snapshot conflict

old file 목록을 기준으로 commit해 concurrent insert/delete를 잃는다.

### expiration breaks streaming reader

장기간 멈춘 incremental consumer가 필요한 snapshot/position을 잃는다. reader lag와 retention을 연결한다.

### orphan cleaner deletes pending writes

너무 짧은 age와 path scan만 사용한다. writer lease/metadata와 conservative threshold가 필요하다.

### partition evolution hidden from jobs

maintenance script가 old path 규칙만 알아 새 spec file을 놓치거나 삭제한다. table metadata를 source of truth로 사용한다.

### compaction success without reconciliation

file 수만 줄고 duplicate/loss가 생긴다. key set, row count, aggregate와 table snapshot diff를 검사한다.

## 검증 질문

1. schema, partition, sort와 file layout 변화가 각각 어떤 metadata에 기록되는가?
2. mixed-spec/mixed-schema file을 모든 reader가 읽는가?
3. compaction base snapshot과 conflict detection이 있는가?
4. snapshot expiration이 backfill·rollback·incremental reader 요구를 보존하는가?
5. orphan candidate가 정말 어떤 live metadata에서도 참조되지 않는가?
6. maintenance 전후 row/key/aggregate와 scanned cost를 함께 비교하는가?

## 연결 연습

- batch capstone의 file size distribution을 관찰하고 compaction plan을 작성한다.
- CDC capstone에서 old snapshot retention과 rebootstrap 가능한 source position 범위를 맞춘다.

## 완료 기준

- table evolution과 physical rewrite를 구분한다.
- compaction을 snapshot-aware replace transaction으로 설계한다.
- expiration과 cleanup의 안전 조건을 backfill·reader·법적 보존과 연결한다.
- maintenance 전후 correctness와 비용을 evidence로 비교한다.
