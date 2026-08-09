# Warehouse, lake와 table format

## 학습 목표

- data warehouse, object-storage data lake와 lakehouse table format의 책임을 구분한다.
- file set, catalog metadata와 table snapshot이 consumer-visible state를 만드는 과정을 설명한다.
- append·overwrite·merge·delete를 immutable file과 metadata commit으로 해석한다.
- engine 독립성과 공통 table contract의 trade-off를 설명한다.

## 핵심 모델

도구 이름보다 다음 계층을 분리한다.

```text
storage
  bytes와 object/file의 내구성

file format
  record를 columnar/row 형태로 encode

table format
  어떤 file이 table에 포함되고 schema·partition·snapshot이 무엇인지 관리

catalog
  table name에서 metadata/current snapshot을 찾음

compute engine
  scan·join·aggregate·write를 수행

orchestrator/governance
  언제 실행하고 누가 접근·변경하는지 관리
```

object storage에 Parquet file을 놓았다고 자동으로 transaction table이 되는 것은 아니다.

## warehouse

일반적인 warehouse는 storage, catalog, transaction, optimizer, access control과 compute 경험을 통합해 제공한다.

장점:

- 일관된 SQL과 관리 경계
- transaction과 concurrency 제어
- statistics·optimizer·workload 관리
- 권한·감사 통합

trade-off:

- 특정 vendor/engine semantics 의존
- storage와 compute 비용 모델
- open file access와 engine interoperability 제한 가능

warehouse를 선택해도 grain, schema, replay와 품질 계약은 별도로 설계한다.

## data lake

object storage에 다양한 raw/processed file을 저장한다.

장점:

- 저렴하고 확장 가능한 storage
- 다양한 format과 engine
- raw history와 대규모 scan

위험:

- path와 file naming이 사실상 API가 됨
- concurrent writer와 partial file set
- schema drift와 orphan files
- small-file explosion
- delete·update·snapshot semantics 부족

“schema-on-read”는 schema가 없다는 뜻이 아니다. reader마다 다르게 추론하면 계약이 분산될 수 있다.

## table format

table format은 immutable data file 위에 metadata와 snapshot commit을 추가한다.

일반적으로 관리하는 것:

- schema와 field identity
- partition spec와 sort order
- data/delete files 목록
- snapshot history와 parent
- atomic metadata commit
- statistics와 manifest
- time travel/rollback

구현마다 세부 보장은 다르다. table format이 storage 자체의 durability나 catalog availability를 대신하지 않는다.

## table snapshot

snapshot은 특정 시점 table을 구성하는 metadata와 file set이다.

```text
snapshot 100
  manifests -> file A, B, C

snapshot 101
  manifests -> file A, C, D + delete E
```

consumer가 snapshot 100을 읽는 동안 writer가 101을 commit해도 일관된 file set을 볼 수 있다. retention이 지나 old files가 삭제되기 전까지만 가능하다.

## write 패턴

### append

새 data file과 metadata를 snapshot에 추가한다. retry duplicate를 막기 위해 commit identity와 input run을 추적한다.

### overwrite

predicate/partition 범위의 old files를 새 files로 교체한다. concurrent writer와 predicate conflict를 검사한다.

### merge/upsert

key matching을 통해 insert/update/delete를 적용한다. engine과 table format이 copy-on-write 또는 merge-on-read 전략을 사용할 수 있다.

### delete

- file rewrite
- position delete
- equality delete

consumer engine이 delete file을 지원하지 않으면 잘못된 row를 읽을 수 있다. interoperability test가 필요하다.

## copy-on-write와 merge-on-read

### copy-on-write

변경 시 영향 file을 다시 작성한다.

- read가 단순하고 빠를 수 있음
- write amplification과 commit latency 증가

### merge-on-read

base file과 change/delete log를 read 때 합친다.

- ingest가 빠를 수 있음
- read와 compaction 복잡성 증가

workload, update frequency, freshness와 query latency로 선택한다.

## catalog

catalog는 current metadata pointer와 namespace를 관리한다.

실패 질문:

- catalog commit은 compare-and-swap/transaction인가?
- 두 writer가 같은 base snapshot에서 commit하면 conflict를 어떻게 처리하는가?
- catalog unavailable 때 reader는 cached snapshot을 얼마나 쓸 수 있는가?
- backup과 disaster recovery에서 storage와 catalog를 어떻게 함께 복원하는가?
- environment 간 table identifier를 어떻게 이동하는가?

file만 backup하고 catalog/history를 잃으면 table state를 복원하기 어렵다.

## raw, canonical, serving layer

고정된 medal 이름보다 각 layer의 계약을 설명한다.

### raw capture

source record와 metadata를 가능한 한 충실히 보존한다. 무제한 보존을 뜻하지 않는다.

### canonical/cleaned

identity, type, time, delete/correction을 공통 규칙으로 정규화한다.

### consumer/serving

특정 분석·ML·검색 요구에 맞춘 grain, aggregate와 latency를 제공한다.

layer가 늘어날수록 lineage, storage, correction propagation과 owner도 늘어난다. 목적 없는 복사를 피한다.

## engine interoperability

같은 table을 여러 engine이 읽고 쓸 때 확인한다.

- 지원 table format version
- schema/partition evolution
- delete files
- timestamp/decimal semantics
- case sensitivity
- commit conflict
- snapshot expiration
- encryption/compression codec

“읽을 수 있음”과 “모든 write feature를 안전하게 공유함”은 다르다. writer를 제한하거나 compatibility matrix를 운영한다.

## 실패 모드

### raw path queried directly

consumer가 unstable raw file path에 의존해 schema/partition 변경이 불가능해진다. published table/view contract를 둔다.

### file write without table commit

data file은 존재하지만 metadata에 포함되지 않은 orphan이다. 반대의 경우 metadata가 없는 file을 가리켜 read failure가 난다. commit과 orphan cleanup을 분리한다.

### concurrent overwrite loses data

두 writer가 같은 partition을 old snapshot 기준으로 교체한다. optimistic conflict detection과 retry/recompute가 필요하다.

### unsupported delete reader

한 engine이 equality delete를 무시해 삭제된 record를 노출한다. engine matrix를 검증한다.

### snapshot expiration breaks backfill

retention을 줄인 뒤 과거 snapshot 기반 재현이 불가능해진다. audit/backfill 요구와 retention을 맞춘다.

### catalog and storage restored separately

서로 다른 시점으로 복원돼 metadata가 missing/orphan file을 가리킨다. 공동 recovery point와 reconciliation이 필요하다.

## 검증 질문

1. storage, file format, table format, catalog와 engine의 책임을 구분했는가?
2. consumer가 어떤 snapshot identity를 읽는가?
3. writer conflict와 partial commit을 어떻게 처리하는가?
4. append·overwrite·merge·delete의 retry identity가 있는가?
5. 모든 reader가 schema evolution과 delete semantics를 지원하는가?
6. storage와 catalog를 같은 recovery contract로 복원하는가?

## 연결 연습

CDC capstone에서 raw capture, canonical current state와 consumer aggregate의 table snapshot을 분리한다.

## 완료 기준

- 단순 file lake와 snapshot table의 차이를 설명한다.
- immutable file 위의 atomic metadata commit으로 table update를 모델링한다.
- catalog·engine·storage failure를 분리하고 reconciliation한다.
- interoperability를 실제 feature matrix와 fixture로 검증한다.

## 공식 자료 연결

Apache Iceberg의 snapshots와 evolution, Apache Parquet의 columnar file 설명을 참고한다. 링크는 [`reference/official-sources.md`](../../reference/official-sources.md)에 있다.
