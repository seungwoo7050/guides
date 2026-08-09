# portability exit and deletion

## Scope

source, artifact, runtime, data, identity, configuration, logs, keys와 commercial commitment를 lock-in register에 기록한다. tenant export는 24시간 안에 준비하고 deletion request 뒤 active data는 7일 안에 제거하되 backup retention은 별도로 고지한다.

| dependency | portable representation | owner | exit trigger | 현재 측정 |
|---|---|---|---|---|
| source/artifact | TODO | TODO | TODO | TODO |
| runtime/event contract | TODO | TODO | TODO | TODO |
| database/object/queue | TODO | TODO | TODO | TODO |
| identity/config/log/key | TODO | TODO | TODO | TODO |
| price/discount/commitment | TODO | TODO | TODO | unknown |

## Stage 1 — IaaS

image, reproducible configuration, database backup와 object inventory로 clean environment를 재구축한다. volume, snapshot, address, image, log sink와 key까지 final inventory에서 0인지 확인한다.

TODO: source environment freeze, copy, checksum, cutover, rollback 순서와 zone 하나 손실 시 RPO 15분·RTO 60분을 검증하는 restore rehearsal을 작성한다.

## Stage 2 — Managed platform

database full/incremental export, object listing, queue drain/dual-write, identity·network mapping, provider backup retention과 control-plane dependency를 작성한다.

TODO: representative dataset으로 throughput, duration, checksum, downtime와 egress bytes를 측정한다. dataset 총량과 provider egress 단가가 없으므로 전체 기간·비용은 unmeasured/unknown으로 둔다.

## Stage 3 — FaaS

handler source만이 아니라 event source schema, acknowledgment, retry·ordering, maximum age/attempts, concurrency, timeout, DLQ, identity, logs와 metric을 대상 runtime에 매핑한다.

TODO: 평상시 2/s·peak 50/s, 평균 4초·p99 40초에서 평균 동시성 8과 보수적 peak 2,000을 대상에 재현한다. 평균 크기 peak ingress 400 MB/s와 최대 크기 5 GB/s stress가 migration/cutover 중에도 처리되는지 또는 명시적으로 throttle하는지 적는다.

## Stage 4 — SaaS

tenant export에는 membership, role, metadata, original object, derived result, plan version, quota·usage와 audit manifest를 포함한다. export는 요청 후 24시간 이내 준비되며 tenant-scoped delivery identity와 checksum을 제공한다.

삭제 상태를 `REQUESTED → BLOCKED|IN_PROGRESS → ACTIVE_DATA_REMOVED → RETENTION_ONLY → COMPLETE`로 정의한다. TODO: 새 write 차단, queue/DLQ/cache/search/analytics/support copy, key, export, usage evidence와 backup expiry를 subsystem별로 매핑한다. active data 7일 목표와 실제 backup retention 고지를 분리한다.

## Evidence와 한계

| assertion | evidence | pass condition | limitation |
|---|---|---|---|
| export 24시간 | TODO: request/ready timestamps·manifest | 24시간 이하 | TODO |
| active deletion 7일 | TODO: subsystem status·final inventory | active copy 0 | TODO |
| portable data | TODO: count/hash/sample restore | source와 일치 | TODO |
| exit feasibility | TODO: measured bytes/s·duration·egress | 정의한 threshold 충족 | 가격 unknown |

TODO: provider physical deletion과 backup media erase는 application inventory만으로 증명할 수 없으며 provider contract evidence가 필요하다고 기록한다.

## Open risks와 owner

| risk/condition | owner | due date | verification | rollback |
|---|---|---|---|---|
| TODO: backup retention과 customer wording | TODO | TODO: YYYY-MM-DD | TODO | TODO |
| TODO: export가 24시간을 초과 | TODO | TODO: YYYY-MM-DD | TODO | TODO |
| TODO: commitment/egress 비용 | TODO | TODO: YYYY-MM-DD | TODO | TODO |
