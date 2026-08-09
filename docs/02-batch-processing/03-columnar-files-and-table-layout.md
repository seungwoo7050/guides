# Columnar file과 table layout

## 학습 목표

- row-oriented와 column-oriented layout의 trade-off를 workload로 설명한다.
- file, row group, page, partition과 table snapshot을 서로 다른 단위로 구분한다.
- partition pruning, column projection, statistics와 compression이 scan cost를 줄이는 과정을 설명한다.
- small-file 문제와 compaction을 correctness·concurrency·비용 관점에서 설계한다.

## 핵심 모델

분석 시스템의 물리 layout은 다음 계층으로 볼 수 있다.

```text
table snapshot / catalog metadata
  어떤 data file과 delete file이 현재 table을 구성하는가

dataset partition
  date, region 등 query pruning을 위한 논리 grouping

data file
  object storage의 immutable file

row group / stripe
  독립적으로 scan·skip할 수 있는 column chunk 집합

page / encoded block
  compression과 encoding의 세부 단위
```

모든 engine이 같은 용어를 쓰지는 않지만, metadata가 어떤 단위의 skip과 commit을 가능하게 하는지 확인한다.

## row와 column layout

### row-oriented

한 record의 field가 가까이 저장된다.

유리한 경우:

- point lookup과 작은 row update
- 한 record의 대부분 column을 읽는 transactional workload
- 낮은 write latency

### column-oriented

같은 column의 값이 함께 저장된다.

유리한 경우:

- 많은 row에서 일부 column만 scan
- 반복 값과 유사한 값의 compression
- vectorized execution
- min/max와 dictionary statistics로 block skip

columnar format을 쓴다고 모든 query가 빨라지는 것은 아니다. 작은 point lookup, 지나치게 많은 file, 잘못된 partition과 nested projection은 여전히 비쌀 수 있다.

## Parquet를 읽는 모델

Parquet 같은 columnar file을 사용할 때 다음을 구분한다.

- schema: field와 nested structure
- row group: 독립 scan 단위
- column chunk: row group 안의 한 column data
- page: encoding/compression 단위
- footer metadata: schema, row group와 statistics

query engine은 필요한 column만 projection하고, predicate와 statistics가 맞으면 row group/file을 skip한다. statistics가 없거나 부정확하고 predicate가 transform돼 pushdown되지 않으면 전체 scan이 발생할 수 있다.

## partitioning

좋은 dataset partition은 다음을 균형 있게 만족한다.

- 자주 사용하는 filter와 정렬됨
- partition 수가 통제됨
- 각 partition file size가 충분히 큼
- late data와 correction을 업데이트 가능
- 개인정보 삭제와 retention 단위에 맞음

### 과도한 cardinality

`user_id`처럼 cardinality가 매우 높은 field를 directory partition으로 쓰면 작은 file과 metadata가 폭증한다.

### coarse partition

연 단위 partition은 일별 query가 거의 전체 file을 scan할 수 있다.

### hidden partition transform

table format이 timestamp에서 day/hour transform을 metadata로 관리하면 consumer가 physical path를 직접 조립하지 않아도 된다. path를 API로 삼지 말고 table metadata를 사용한다.

## file size

너무 작은 file:

- object listing과 metadata overhead
- scheduler task 증가
- footer open 요청 증가
- compression 효율 저하

너무 큰 file:

- 병렬성 감소
- rewrite와 recovery 비용 증가
- row group pruning이 나쁘면 과도한 scan

target size는 storage, engine, network, partition, query concurrency에 따라 측정한다. 문서에 고정된 숫자를 보편 법칙처럼 복사하지 않는다.

## compression과 encoding

- dictionary encoding: 낮은 cardinality에 유리
- run-length encoding: 반복 값에 유리
- delta encoding: 증가하는 수치·timestamp에 유리
- general compression: CPU와 I/O trade-off

compression ratio만 보지 않는다. decode CPU, predicate pushdown, memory와 downstream engine 지원을 함께 측정한다.

## statistics와 pruning

file/row group의 min, max, null count, distinct estimate, bloom filter가 scan 범위를 줄일 수 있다.

주의:

- 문자열 truncation과 collation
- NaN과 null semantics
- encrypted column의 statistics 노출
- 오래된 statistics
- transform된 predicate
- highly overlapping ranges

“partition pruning이 됐다”는 주장은 query plan과 실제 scanned files/bytes로 확인한다.

## immutable files와 table update

object storage file은 일반적으로 in-place update보다 새 file 작성에 적합하다. update/delete/merge는 다음처럼 구현될 수 있다.

- 영향 file rewrite
- position/equality delete file 추가
- 새 snapshot metadata commit
- background compaction에서 materialize

consumer가 file path를 직접 캐시하면 snapshot semantics가 깨질 수 있다. catalog/table API를 통해 현재 snapshot을 읽는다.

## small-file compaction

compaction은 단순 파일 합치기가 아니다.

입력:

- compact 대상 snapshot
- partition/bucket 범위
- target file size와 sort order

출력:

- 새 data files
- 제거할 old files 목록
- 새 table snapshot

필수 조건:

- concurrent writer 변경을 잃지 않음
- old snapshot reader를 retention 기간 동안 지원
- compaction 실패 시 old files가 여전히 유효
- commit 성공 뒤 orphan file 정리
- row count, key set과 aggregate 대사

## schema와 layout 변화

schema, partition spec, sort order는 서로 독립적으로 발전할 수 있다.

예:

- column 추가는 과거 file rewrite 없이 reader default로 처리 가능
- day partition에서 hour partition으로 새 write만 변경
- sort order 변경은 새 file에 적용되고 old file은 그대로 존재

query engine은 여러 spec과 file layout을 동시에 읽어야 한다. “metadata-only evolution”이 즉시 모든 data를 새 layout으로 바꾸는 것은 아니다.

## 실패 모드

### path is the contract

consumer가 `date=.../country=...` path를 직접 조립해 partition evolution을 못 한다. catalog와 logical predicate를 사용한다.

### partition explosion

고유값이 많은 field로 partition해 수백만 작은 file이 생긴다. workload와 cardinality를 다시 측정한다.

### compaction deletes live files

concurrent commit을 고려하지 않고 오래된 목록을 기준으로 삭제한다. snapshot isolation과 optimistic commit/conflict handling이 필요하다.

### stale cache

consumer가 file list를 장기 cache해 새 snapshot이나 delete를 보지 못한다. snapshot ID와 refresh contract를 둔다.

### wrong statistics trust

statistics가 truncated/absent인데 file을 잘못 skip하면 correctness 문제다. format과 engine의 보장을 확인한다.

## 검증 질문

1. table, partition, file, row group 중 어느 단위에서 skip·commit·rewrite가 일어나는가?
2. 주요 query가 어떤 predicate와 column projection을 사용하는가?
3. 실제 scanned files/bytes와 task 수를 측정했는가?
4. file size 분포와 small-file count를 보는가?
5. compaction이 concurrent write와 old snapshot reader를 보존하는가?
6. schema·partition·sort evolution 뒤 mixed-layout read를 시험했는가?

## 연결 연습

- [`examples/partition_cost.py`](../../examples/partition_cost.py)로 partition cardinality와 file count trade-off를 관찰한다.
- batch capstone에서 output manifest에 file size, row count, min/max와 snapshot ID를 포함한다.

## 완료 기준

- columnar layout이 query scan을 줄이는 조건을 설명한다.
- partition과 file size를 workload·cardinality·운영 비용으로 선택한다.
- immutable file과 snapshot commit을 기준으로 update·compaction을 설계한다.
- query plan과 scanned bytes로 pruning 주장을 검증한다.

## 공식 자료 연결

Apache Parquet의 column-oriented format 설명과 Apache Iceberg의 table evolution·snapshot 문서를 참고한다. 검토 링크는 [`reference/official-sources.md`](../../reference/official-sources.md)에 있다.
