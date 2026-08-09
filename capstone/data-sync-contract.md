# Data·sync contract

## 1. local schema와 migration

- 현재 schema version:
- 지원 upgrade source version:
- fixture source revision/digest:
- 주요 table/index/foreign key:
- migration 중 종료·storage 부족·downgrade 정책:

## 2. storage와 owner

| 데이터 | 저장소/owner | 보호·backup | 변경 사건 | purge/reconciliation | 장애 우선순위 |
|---|---|---|---|---|---|
| record | | | | | |
| outbox/conflict | | | | | |
| attachment/staging | | | | | |
| credential envelope | | | | | |
| preference | | | | | |
| redacted diagnostic | | | | | |

## 3. save transaction

```text
입력 검증
→ app-owned file 준비·checksum
→ BEGIN record/attachment/outbox
→ 같은 사용자 의도와 command snapshot 기록
→ COMMIT
→ UI가 local 정본과 pending 상태 관찰
```

transaction 직전·중간·직후 종료에서 관측되는 DB/file/UI 상태:

## 4. attempted command 불변식

```ts
{
  commandId: "",
  entityId: "",
  operation: "upsert | delete | upload",
  baseVersion: null,
  localRevision: 0,
  payload: {},
  attemptCount: 0,
  leaseOwner: null,
  leaseExpiresAt: null
}
```

- 한 번 claim/전송한 뒤 바뀌지 않는 field:
- 아직 시도하지 않은 queued command의 coalescing 조건:
- active 중 newer edit가 만드는 새 command:
- server duplicate-result 보존과 client retry window:

## 5. outbox state machine

```text
pending → in_flight
in_flight → completed | retry_wait | conflict | blocked_auth | permanent_failure
expired lease → 같은 attempted command로 retry_wait
```

claim/lease, foreground/background overlap과 process restart recovery:

## 6. response 검증과 결과

| 입력 | durable final state | 자동 retry | 사용자 다음 행동 |
|---|---|---|---|
| valid success | | | |
| response loss/UNKNOWN | | | |
| duplicate result | | | |
| stale command response | | | |
| malformed payload | | | |
| server version regression | | | |
| 401/refresh failure | | | |
| 403/validation permanent | | | |
| version conflict | | | |

active success와 newer local edit의 local/remote/queued 최종 값:

## 7. conflict

- 보존할 base/local/remote/command 값:
- remote/local/merge/나중 결정 UX:
- 해결이 새 command id와 최신 base를 만드는 evidence:

## 8. attachment partial failure

| 실패 | durable final state | 재시도/cleanup | 사용자 관측 |
|---|---|---|---|
| temporary→owned copy 실패 | | | |
| file copy 성공, DB 실패 | | | |
| upload 성공, response loss | | | |
| upload 성공, local commit 실패 | | | |
| DB row가 가리키는 file 누락 | | | |
| record delete 중 cleanup 실패 | | | |

## 9. 통합 fault history

capstone README의 1~10을 한 timeline으로 첨부한다.

| 순서 | initial DB/file/outbox | 사건/fault | final DB/file/outbox/UI | invariant | test/log evidence |
|---:|---|---|---|---|---|
| 1 | | upgrade | | | |
| 2 | | offline save | | | |
| 3 | | media/location | | | |
| 4 | | process kill | | | |
| 5 | | response loss+retry | | | |
| 6 | | newer edit+late result | | | |
| 7 | | conflict | | | |
| 8 | | background not run | | | |
| 9 | | notification cold start | | | |

## 10. 보장과 비보장

- 결정적 model/fault server가 보장하는 것:
- SQLite/process/device test가 추가로 보장하는 것:
- production backend idempotency, OS file durability, store-delivered build 중 아직 보장하지 않는 것:
