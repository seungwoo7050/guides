# portability exit and deletion

## Scope

exit 범위는 source, build artifact, runtime/event semantics, database·object·queue data, identity, configuration, logs, encryption keys와 price·discount·commitment를 포함한다. source와 artifact는 reproducible build hash, data는 open documented schema와 manifest/checksum, configuration은 secret 없는 versioned export로 옮긴다. identity principal과 key material은 복사하지 않고 대상에서 새로 만들고 mapping·rotation evidence를 남긴다. provider가 아직 선택되지 않아 실제 export throughput, egress 단가, commitment와 backup retention은 `unmeasured/unknown`이다.

tenant export는 요청 후 24시간 안에 준비한다. deletion request는 새 write를 즉시 차단하고 active data를 7일 안에 제거하며, 법적·운영상 남기는 aggregate usage와 provider backup의 retention·erase 조건을 customer에게 별도로 고지한다. portability는 source가 있다는 주장 대신 representative migration의 bytes, duration, checksum, failure와 rollback으로 판정한다.

## Stage 1 — IaaS

signed artifact와 image recipe, declarative configuration, database backup와 object inventory로 빈 account/region의 isolated environment를 재구축한다. database·object의 authoritative state와 thumbnail 같은 derived state를 구분하고, derived output은 필요하면 원본에서 재생성한다. source freeze → final incremental copy → checksum·business invariant → endpoint cutover 순으로 실행하며 검증 실패 시 DNS/traffic을 source로 되돌리고 target write를 폐기한다.

zone 하나의 compute 손실 rehearsal은 RPO 15분·RTO 60분 안에 last-known-good artifact와 backup으로 복구되는지 측정한다. exit cleanup은 VM, volume, snapshot, address, image, load balancer, database, object, queue, log sink, human/workload identity와 key의 final inventory를 남긴다. 삭제는 inventory와 retention을 검토한 승인 절차에서만 수행하며 source를 예고 없이 제거하지 않는다.

## Stage 2 — Managed platform

managed database는 full export와 change/incremental catch-up, object storage는 version-aware listing과 checksum manifest, queue는 drain 또는 operation-ID 기반 dual processing으로 이동한다. managed runtime setting, private/public endpoint, DNS/TLS dependency, quota·limit, monitoring, backup schedule와 restore procedure를 target capability에 매핑한다. control plane이 실패해도 기존 data plane을 관찰·rollback할 경로를 별도로 둔다.

representative dataset에서 `throughput = verified bytes / elapsed seconds`, `estimated duration = total bytes / measured throughput`, `minimum export throughput = tenant export bytes / 86,400 seconds`를 계산한다. source/target record count, per-object SHA-256와 business invariant가 일치해야 한다. 전체 dataset size와 실제 provider egress price가 없으므로 전체 migration duration·egress cost는 `unknown`이며, provider 선택 뒤 sample 비율과 throttling 조건을 함께 보고한다.

## Stage 3 — FaaS

handler source 외에 event envelope/version, tenant-scoped operation ID, delivery acknowledgment, visibility, ordering, maximum attempts·age, timeout, partial batch, concurrency, DLQ/redrive, workload identity, log·metric·trace와 deterministic output key를 portability register에 넣는다. source와 target에서 같은 duplicate, timeout-after-write, invalid, transient, poison event를 재생해 output·usage·terminal state가 일치해야 한다.

평상시 2건/s와 평균 4초의 평균 동시성 8, peak 50건/s와 p99 40초의 보수적 stress 2,000을 target에서도 queue/backpressure로 처리한다. peak에서 평균 8 MB object는 400 MB/s, 최대 100 MB stress는 5 GB/s이므로 cutover 중 source와 target이 이중으로 전체 부하를 받는다고 가정하지 않는다. measured safe throughput 아래에서 분할하거나 producer를 throttle하고 queue age를 공개한다. 한 tenant 30% 부하에서 나머지 tenant가 진행하는 fairness도 재검증한다.

## Stage 4 — SaaS

export bundle은 schema version, tenant·membership·role, document metadata, original object, text·thumbnail result, plan version, quota·usage와 audit manifest를 포함한다. 각 file은 path, bytes와 checksum을 가지며 tenant-scoped one-time delivery identity로 제공한다. export request/ready timestamp 차이가 24시간 이하여야 하고 다른 tenant가 URL이나 object key를 사용할 수 없어야 한다. Starter 100건/월과 Pro 10,000건/월의 plan version과 usage도 함께 내보낸다.

deletion state는 `REQUESTED → IN_PROGRESS → ACTIVE_DATA_REMOVED → RETENTION_ONLY → COMPLETE`의 단방향이다. 요청 즉시 upload·new processing·DLQ replay를 막고 database, object/version, result, cache, queue/DLQ, search/index, analytics, support copy, export, identity grant와 key reference를 subsystem별로 reconcile한다. `ACTIVE_DATA_REMOVED`는 요청 후 7일 이내이며 active inventory가 0이어야 한다. backup, tombstone과 aggregate usage는 목적·scope·expiry를 고지하고 expiry 뒤 provider evidence와 final inventory로 `COMPLETE`를 판단한다.

## Evidence와 한계

| assertion | evidence | 합격 기준 | 한계 |
|---|---|---|---|
| tenant export | request/ready timestamps, schema manifest, count/hash | 24시간 이하, checksum·count 일치, cross-tenant deny | 실제 대용량 throughput 미측정 |
| active deletion | subsystem status, queue/DLQ audit, final inventory | 7일 이하, active copy 0, late write 0 | provider backup media 미관찰 |
| state portability | source/target count·checksum·business invariant | mismatch 0 또는 owner가 있는 예외 | full dataset 규모 unknown |
| event portability | duplicate/failure replay trace | output·usage·terminal state 동일 | provider outage/ordering 차이 미측정 |
| exit feasibility | bytes/s, duration, throttling, egress bytes | 24시간 목표와 RTO/RPO 판단 가능 | egress 가격·commitment unknown |

local rehearsal은 export schema, application deletion state와 checksum 방법을 검토하지만 provider physical deletion, hidden replica, backup media erase나 key-destruction 보장은 입증하지 않는다. 그 부분은 선택 provider의 공식 retention/deletion 계약과 support evidence가 필요하다. 자동 검사는 migration architecture를 승인하지 않는다.

## Open risks와 owner

| risk/condition | owner | due date | verification | rollback |
|---|---|---|---|---|
| provider backup retention과 customer wording 미확정 | data owner | 2026-09-22 | 공식 retention/deletion 계약을 notice와 대조하고 sample deletion evidence 검토 | `COMPLETE` 대신 `RETENTION_ONLY` 표시, 신규 provider 선택 보류 |
| representative export가 24시간 target을 외삽하지 못함 | data owner | 2026-09-15 | tenant bytes와 measured bytes/s로 86,400초 내 완료 여부 계산 | export를 shard하고 upload를 throttle, source read access 유지 |
| commitment·egress 가격과 total data size 미측정 | cost owner | 2026-09-29 | inventory bytes와 official price/term snapshot으로 exit estimate 작성 | 장기 commitment 체결 보류 |
| event runtime 차이로 duplicate/ordering 결과 변경 | runtime owner | 2026-09-22 | source/target failure replay에서 output·usage·terminal diff 0 | target cutover 중단 후 source consumer 재개 |
