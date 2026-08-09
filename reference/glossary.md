# 용어

이 문서는 가이드 전체에서 반복 사용하는 용어의 **최소 계약**을 고정한다. 특정 제품이 같은 단어를 다른 의미로 사용할 수 있으므로 실제 구현에서는 해당 제품의 공식 문서를 함께 확인한다.

## Record와 계약

### Record

파이프라인이 식별·전달·변환하는 논리 단위다. 파일 한 줄, table row, message 하나와 항상 같지는 않다.

### Grain

record 하나가 표현하는 업무 사실의 정확한 단위다. 예: 주문 1개, 주문 항목 1개, 매장×5분 window 1개.

### Stable key

같은 논리 record를 재처리·중복 제거·수정할 때 다시 식별하는 key다. 실행 시각이나 파일 순번처럼 재실행마다 바뀌는 값은 적합하지 않다.

### Data contract

producer와 consumer가 합의한 grain, key, schema, 시간 의미, correction/delete, 품질, freshness, 접근과 보존 계약이다.

### Data product

명확한 소비자·소유자·계약·운영 책임·품질 근거를 가진 데이터셋 또는 데이터 서비스다. table이 존재한다는 사실만으로 data product가 되지는 않는다.

## 시간

### Event time

업무 사건이 발생한 시간이다. source가 생성하거나 업무 규칙으로 정한다.

### Ingestion time

record가 ingestion 경계를 통과한 시간이다.

### Processing time

연산자가 record를 실제 처리한 시간이다. 부하·재시작·재실행에 따라 달라질 수 있다.

### Data interval

한 run이 처리할 논리 입력 범위다. 일반적으로 `[start, end)`처럼 경계를 명시한다.

### Watermark

event-time 진행도에 관한 시스템의 추정 또는 정책 경계다. 그 이전 event가 절대 오지 않는다는 물리적 보장은 아니다.

### Allowed lateness

watermark 이후에도 correction을 위해 state를 유지하고 late record를 수용하는 범위다.

### Trigger

window 결과를 언제 emit할지 정하는 정책이다. early, on-time, late emission을 만들 수 있다.

## 실행과 상태

### Bounded data

처리 시작 전에 유한한 입력 범위를 고정할 수 있는 데이터다.

### Unbounded data

새 record가 계속 도착해 전체 끝을 알 수 없는 데이터다.

### Replay

같은 source event 또는 input snapshot을 다시 처리하는 작업이다.

### Backfill

과거 interval의 누락·오류를 수정하거나 새 logic으로 다시 계산해 consumer-visible 결과를 채우는 운영 작업이다.

### Idempotency

같은 논리 작업을 여러 번 실행해도 추가적인 잘못된 외부 효과 없이 같은 최종 상태에 도달하는 성질이다.

### Determinism

고정된 입력·code·configuration·reference data에서 같은 논리 결과를 만드는 성질이다. idempotency와 동일하지 않다.

### Checkpoint

처리 state와 source progress를 함께 복구할 수 있도록 고정한 상태다.

### Source position

source log 또는 partition 안에서 change의 순서를 식별하는 offset, LSN, binlog position 등의 위치다.

### Tombstone

삭제 사실과 마지막 source position을 보존하는 record 또는 state다. 오래 지연된 update에 의한 부활을 막는 데 사용한다.

## 저장과 publish

### Partition

데이터를 저장·처리·소유하는 단위다. source partition, compute partition, file/table partition은 서로 다를 수 있다.

### Shuffle

key 또는 partition 기준을 바꾸기 위해 record를 worker 사이에서 재분배하는 작업이다.

### Snapshot

특정 시점에 consumer가 일관된 하나의 table 상태로 읽을 수 있는 version이다.

### Manifest

입력 파일·snapshot·schema·transform version 또는 output file 집합을 재현할 수 있도록 기록한 목록이다.

### Staged publish

output을 consumer-visible 위치와 분리해 완성·검증한 뒤 pointer나 metadata commit을 교체하는 패턴이다.

### Compaction

logical content를 유지하면서 작은 파일이나 변경 조각을 더 적은 physical file로 다시 작성하는 유지보수 작업이다.

## 검증과 운영

### Reconciliation

source와 sink의 count, key 집합, aggregate, hash 또는 표본을 비교해 누락·중복·오염을 찾는 작업이다.

### Freshness

업무 사건 또는 source position이 consumer-visible dataset에 반영되기까지의 지연 상태다.

### Completeness

계약된 입력 범위에서 필요한 record가 모두 반영됐는지에 관한 품질 차원이다.

### Lineage

어떤 run·job·code revision·input snapshot이 어떤 output snapshot을 만들었는지 연결한 근거다.

### Data observability

파이프라인 process뿐 아니라 데이터 volume, schema, distribution, freshness, quality와 lineage 상태를 관찰하는 능력이다.

### Publish gate

품질·대사·승인 조건을 통과하기 전 consumer-visible pointer를 바꾸지 않는 경계다.
