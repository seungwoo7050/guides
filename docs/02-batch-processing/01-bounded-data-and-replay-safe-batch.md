# Bounded data와 replay-safe batch

## 학습 목표

- batch 입력을 “현재 보이는 모든 파일”이 아니라 고정된 snapshot과 interval로 정의한다.
- 재실행 가능성과 멱등성을 output publish 계약까지 설명한다.
- partial write, retry, code change와 upstream correction 뒤의 상태를 구분한다.
- backfill을 특별 작업이 아니라 동일한 pipeline의 다른 실행 범위로 설계한다.

## 핵심 모델

batch는 단순히 정해진 시간에 실행되는 프로그램이 아니다. **유한한 입력 집합에 대해 하나의 재현 가능한 결과를 publish하는 transaction에 가까운 작업**이다.

```text
run identity
+ input snapshot / data interval
+ transform artifact와 parameter
+ deterministic normalization
+ staged output
+ validation
+ atomic 또는 versioned publish
+ manifest와 lineage
```

이 중 하나가 없으면 “어제 결과를 같은 조건으로 다시 만들 수 있는가?”에 답하기 어렵다.

## bounded input

bounded data는 처리할 원소 수가 유한하다는 뜻이다. 그러나 input을 고정하지 않으면 실행 중 파일이 추가되거나 source table이 바뀔 수 있다.

### file input snapshot

나쁜 입력:

```text
s3://bucket/events/date=2026-08-08/*.json
```

실행 시작과 재시도 사이에 file이 추가되면 결과가 달라진다.

더 나은 계약:

- immutable object version 또는 content hash
- input manifest에 object key, version, size, checksum 기록
- manifest 자체의 ID를 run 입력으로 사용
- quarantine/late file은 다음 manifest 또는 correction run에 포함

### database input snapshot

`WHERE updated_at < cutoff`만으로는 같은 snapshot을 보장하지 않을 수 있다. 실행 중 update가 생기고 timestamp 정밀도·clock·transaction 경계가 다르면 누락이나 중복이 생긴다.

가능한 경로:

- repeatable read/exported snapshot
- source-generated monotonically increasing position
- CDC log를 특정 position까지 materialize
- source가 제공하는 immutable extract

어떤 방법이든 input coverage를 재현할 수 있어야 한다.

## data interval과 run time

orchestrator가 08:00에 실행했다고 “08:00 데이터”인 것은 아니다.

```text
logical interval: [2026-08-08T00:00Z, 2026-08-09T00:00Z)
run started:      2026-08-09T01:12Z
published:        2026-08-09T01:27Z
```

transform은 가능하면 wall clock `now()`가 아니라 명시적 interval과 `as_of`를 입력으로 받는다. 그래야 과거 interval을 같은 의미로 backfill할 수 있다.

## deterministic transform

같은 논리 입력과 같은 transform version이 같은 논리 출력을 만들어야 한다.

위험 요소:

- unordered collection iteration
- locale/timezone에 따른 parsing
- 랜덤 ID
- 외부 API의 현재 응답
- 처리 시각 `now()`
- floating-point reduction 순서
- nondeterministic tie-break
- mutable dimension을 현재 상태로 join

모든 byte가 같아야 하는 것은 아니다. compression metadata나 file ordering은 다를 수 있다. 대신 record set, key별 값, partition coverage 같은 **논리 동등성**을 정의한다.

## 멱등성과 재실행 가능성

### task-level idempotency

같은 run을 다시 실행해도 외부 상태가 중복되지 않는다.

### dataset-level repeatability

같은 input snapshot과 code version에서 같은 논리 dataset을 만든다.

### correction-aware reproducibility

source correction이나 dimension version이 달라졌다면 결과가 달라질 수 있다. 이때 어떤 source snapshot과 reference version을 사용했는지 manifest에 남긴다.

“재실행하면 같다”는 주장은 입력과 version을 명시하지 않으면 의미가 없다.

## output publish 패턴

### overwrite partition

작은 partition과 atomic table commit이 가능하면 interval partition을 교체한다.

조건:

- partition key가 logical interval과 정렬됨
- writer 간 충돌 방지
- validation 전 기존 partition을 지우지 않음
- table metadata commit이 원자적이거나 snapshot rollback 가능

### write-once version + pointer

```text
runs/run-123/output/...
runs/run-123/manifest.json
published/current -> run-123
```

새 version을 검증한 뒤 pointer 또는 catalog snapshot을 전환한다. consumer는 incomplete staging 경로를 보지 않는다.

### merge/upsert

business key별 update가 필요할 수 있다. source version과 delete 처리, stale update 거부, duplicate key를 명확히 해야 한다. merge가 있다는 이유로 멱등성이 자동 보장되지는 않는다.

### append

append-only 결과는 간단하지만 retry가 duplicate를 만들 수 있다. deterministic record ID, run ID와 consumer dedup 또는 commit protocol이 필요하다.

## staged publish

권장 순서:

```text
input manifest 고정
→ staging에 transform
→ schema·count·key·domain 검사
→ source와 reconciliation
→ final metadata commit
→ lineage/freshness event
→ 이전 staging 정리
```

validation 실패 때 production-visible dataset은 바뀌지 않아야 한다.

## run manifest

예:

```json
{
  "run_id": "sales_daily__2026-08-08__v3",
  "data_interval": ["2026-08-08T00:00:00Z", "2026-08-09T00:00:00Z"],
  "input_snapshot": "manifest-sha256:...",
  "code_revision": "git:abc123",
  "parameters": {"timezone": "Asia/Seoul"},
  "output_snapshot": "table-snapshot:987",
  "quality": {"rows": 18420, "duplicate_keys": 0},
  "status": "PUBLISHED"
}
```

manifest는 로그 요약이 아니라 재현·대사·rollback의 정본이다.

## 실패 모드

### partial publish

일부 partition만 final 경로에 있고 task가 실패한다. consumer가 half dataset을 읽을 수 있다. staging과 metadata commit을 분리한다.

### delete-then-write

기존 partition을 먼저 지운 뒤 write 실패가 발생한다. 검증된 새 version이 준비될 때까지 기존 snapshot을 유지한다.

### retry appends duplicates

run ID와 record identity 없이 append한다. retry가 새 record를 만든다. deterministic key 또는 atomic commit을 사용한다.

### mutable dimension join

과거 fact를 현재 customer segment와 join해 backfill할 때마다 과거 결과가 바뀐다. dimension snapshot/as-of contract를 고정한다.

### hidden current time

코드 내부 `datetime.now()`로 interval을 정해 manual retry가 다른 범위를 처리한다. orchestrator가 명시적 interval을 전달한다.

### success before validation

file write가 끝나면 task를 success로 표시하고 quality job은 나중에 실패한다. publish 여부와 실행 여부를 분리하고 consumer-visible 상태를 quality gate 뒤에 전환한다.

## 검증 전략

### deterministic fixture

작은 input manifest와 기대 record set을 버전 관리한다.

### rerun test

같은 interval을 빈 output과 기존 output 양쪽에 실행해 같은 logical snapshot이 되는지 확인한다.

### interruption test

staging 중간, validation 직전, metadata commit 직전 실패를 주입한다. 기존 published snapshot이 유지되고 retry가 복구하는지 확인한다.

### correction test

source record 하나가 수정된 새 snapshot을 넣고 영향받는 output과 lineage가 예상대로 바뀌는지 확인한다.

### concurrent run test

같은 interval의 두 run이 충돌할 때 한 run만 publish하거나 versioned conflict로 명확히 실패해야 한다.

## 검증 질문

1. input set을 나중에 다시 열거할 수 있는가?
2. data interval과 run start time을 구분했는가?
3. code, parameter, reference data version을 기록하는가?
4. validation 실패 때 consumer가 이전 정상 snapshot을 계속 읽는가?
5. retry와 concurrent run이 duplicate 또는 lost partition을 만들지 않는가?
6. 같은 byte가 아니라 어떤 논리 동등성을 검사하는가?

## 연결 연습

[`replay-safe batch`](../../exercises/02-batch-processing/01-replay-safe-batch/README.md)에서 input manifest, staging, validation과 pointer publish를 구현한다.

## 완료 기준

- batch run을 interval·snapshot·artifact·publish transaction으로 설명한다.
- partial failure와 retry 뒤의 consumer-visible 상태를 정의한다.
- backfill이 동일 code path와 parameter를 사용하도록 설계한다.
- run manifest와 reconciliation으로 결과를 재현하고 증명한다.
