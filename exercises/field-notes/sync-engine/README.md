# Field Notes bounded sync engine

Stage 04~05의 outbox 행동을 **repository·transport·clock·budget public port**로 분리한 TypeScript reference다. foreground와 background trigger가 같은 worker를 호출하고, 한 번 claim한 command마다 durable checkpoint를 한 번 시도한다.

이 package는 production SQLite adapter, HTTP authentication, UI, background scheduler를 구현하지 않는다. 포함된 `InMemorySyncRepository`와 `FaultServerTransport`는 상태·실패 계약을 결정적으로 검사하는 test adapter다.

## 실행

Node 24를 사용한다.

```sh
fnm exec --using=24.19.0 npm --prefix exercises/field-notes/sync-engine run typecheck
fnm exec --using=24.19.0 npm --prefix exercises/field-notes/sync-engine test
```

테스트는 sibling [`fault-server`](../fault-server/README.md)의 in-process API를 사용한다. network sleep이나 실제 port가 필요하지 않다.

## public ports

```ts
interface SyncRepository {
  claimNext(...): Promise<ClaimedCommand | null>;
  checkpoint(...): Promise<CheckpointResult>;
  resumeBlockedAuth(now: number): Promise<number>;
  resolveConflict(...): Promise<ConflictResolutionResult>;
  // read-only observation methods
}

interface SyncTransport {
  send(command: RecordCommand, signal: AbortSignal): Promise<WireResponse>;
}

interface SyncClock {
  now(): number;
}

interface SyncBudget {
  canStartNext(...): boolean;
  leaseDurationMs(): number;
  retryDelayMs(...): number;
}
```

`BoundedSyncWorker`는 SQLite, fetch, React, AppState나 background API를 import하지 않는다. production adapter가 위 의미를 보존하면 manual·app-active·foreground·background trigger가 같은 core를 사용할 수 있다.

## durable command 상태

| 상태 | 의미 | 자동 claim |
|---|---|---|
| `pending` | 아직 transport에 보내지 않은 command | 가능 |
| `in_flight` | immutable attempted snapshot과 live lease가 있음 | lease expiry 전 불가 |
| `retry_wait` | UNKNOWN/invalid response 등, next attempt 시각까지 대기 | 시각 이후 가능 |
| `blocked_auth` | 401 뒤 command 보존, credential 회복 대기 | explicit resume 전 불가 |
| `conflict` | local/remote/base/attempted evidence 보존 | resolution 전 불가 |
| `permanent` | validation/policy terminal failure | 자동 재시도 불가 |
| `completed` | remote success 또는 명시적 conflict resolution으로 더 처리할 일 없음 | 불가 |

첫 claim은 `RecordCommand` 전체를 attempted snapshot으로 capture한다.

```text
commandId, recordId, operation,
baseVersion, localRevision,
payload/tombstone, createdAt
```

retry, lease expiry, 401 resume와 response loss 뒤에도 같은 snapshot을 사용한다. repository는 internal snapshot을 deep-freeze하고 checkpoint의 claim과 다시 비교한다. getter가 반환한 clone을 바꿔도 internal attempted command는 바뀌지 않는다.

## 한 command checkpoint

worker loop는 다음 순서다.

```text
budget 확인
→ repository atomic claim + lease
→ transport send
→ status/body runtime parse
→ 정확히 한 command outcome checkpoint 시도
→ 다음 budget 또는 종료
```

checkpoint outcome은 `success`, `conflict`, `retry_wait`, `blocked_auth`, `permanent` 중 하나다. transport가 response를 잃거나 throw하면 server 적용 여부를 모르므로 `retry_wait`다. local checkpoint 자체가 실패하면 worker는 같은 command에 두 번째 checkpoint를 추측하지 않고 `checkpoint-failed`로 멈춘다. in-flight lease와 attempted snapshot이 남아 expiry 뒤 같은 command를 다시 보낸다.

이 package의 test repository는 `failNextCheckpoint()`로 “server success 뒤 local result transaction 실패”를 재현한다. fault-server memoization 때문에 재전송돼도 remote apply count는 1이다.

## claim·lease와 trigger overlap

- live `in_flight` lease가 있는 command는 다른 worker가 claim하지 못한다.
- 같은 record의 뒤 command도 앞 lease가 끝날 때까지 claim하지 않는다.
- lease가 expire하면 새 owner/token으로 claim하되 attempted snapshot과 command ID는 유지한다.
- 서로 다른 record는 bounded worker 두 개가 처리할 수 있어 delay/reorder를 관찰할 수 있다.
- `trigger`는 결과를 바꾸지 않는 관측 context다.

lease는 exactly-once network delivery를 만들지 않는다. 두 process의 원자적 claim과 compare-and-set은 production repository transaction이 제공해야 하며 remote idempotency가 함께 필요하다.

## newer edit와 rebase

A가 in-flight인 동안 사용자가 B를 저장할 수 있다.

```text
A attempted(localRevision=1, base=null)
→ B pending(localRevision=2, base=null)
→ A success(remoteVersion=1)
→ local payload B 보존
→ known remote base만 1로 전진
→ 아직 미시도인 B를 새 command ID + base=1로 transactionally 대체
```

A의 attempted payload/base/ID는 바꾸지 않는다. `pending`만 rebase 대상이다. 이미 `in_flight`, `retry_wait`, `blocked_auth`, `conflict`, `permanent`, `completed`인 command는 attempted evidence가 있으므로 수정하지 않는다.

`InMemorySyncRepository`는 `CommandIdGenerator`를 주입받아 이 동작을 검사한다. production ID 생성과 pending command 대체는 success checkpoint와 같은 SQLite transaction에 있어야 한다.

## response parser

`parseTransportResponse()`는 TypeScript assertion으로 wire body를 신뢰하지 않는다.

- 모든 response에서 `commandId` required/match
- success/conflict의 `recordId` match
- remote `version`이 positive integer이며 known version보다 작지 않음
- success version이 attempted `baseVersion`보다 실제로 전진
- non-deleted payload의 `title`, `notes`, `status`, `observedAt` required field
- optional location의 numeric/date field
- delete success는 `deleted=true`와 `payload=null`
- conflict current snapshot과 expected base
- 401/permanent/validation status의 kind·reason

malformed success나 version regression은 local success로 checkpoint하지 않는다. `retry_wait` 뒤 같은 ID를 보내 fault-server의 memoized canonical result로 reconciliation한다.

## conflict와 resolution

conflict checkpoint는 다음을 별도 evidence로 보존한다.

```text
attempted command/base
현재 local payload/localRevision
remote current payload/version 또는 null
createdAt
```

`remote` resolution은 remote snapshot을 local에 적용한다. `local`/`merge` resolution은 remote current version을 base로 **새 command ID**를 만든다. 원 conflict evidence는 resolution metadata와 함께 남는다. 같은 base/ID로 원 command를 다시 보내지 않는다.

## 결정적 검사 범위

테스트는 다음을 확인한다.

- response loss → same attempted ID retry → remote apply 1회
- local checkpoint loss → duplicate delivery/memoized response
- controlled delay와 A/B response reorder
- foreground/background live-lease overlap
- 401 durable block와 explicit resume
- malformed success와 version regression 거부/reconciliation
- permanent terminal state
- conflict 양측 보존과 새 resolution command
- lease expiry recovery
- active command 중 newer edit 보존과 unattempted-only rebase
- parser의 command ID, required payload field, version monotonicity

## production adapter가 추가로 보장해야 하는 것

`InMemorySyncRepository`는 process memory에서만 동작한다. snapshot을 새 instance에 넘겨 restart 모양을 검사할 수 있지만 실제 durability가 아니다. SQLite adapter는 최소 다음을 한 transaction 또는 동등한 atomic boundary로 구현해야 한다.

- local record save/delete와 initial outbox insert
- eligible claim, attempted snapshot과 lease token 기록
- lease token compare-and-set checkpoint
- success의 remote base 갱신, current local preservation과 pending rebase
- conflict의 양측 snapshot 저장
- auth/retry/permanent state와 attempt/checkpoint history
- crash/migration 뒤 state 복원

추가 비보장 범위:

- `FaultServerTransport`는 in-process call 전 abort만 확인한다. 실제 HTTP timeout/cancellation, TLS, auth header와 response streaming은 production transport가 구현해야 하며 cancellation 뒤 결과는 UNKNOWN일 수 있다.
- `FixedSyncBudget`은 command count·lease·retry delay의 결정적 fixture다. 실제 background expiration, battery/network quota와 wall-time deadline을 보장하지 않는다.
- process 간 lock, SQLite busy/rollback, device clock 변경과 lease time domain은 실제 adapter에서 검증해야 한다.
- queue fairness, attachment dependency와 대규모 resumable upload는 이 최소 record engine 밖이다.
- React UI의 pending/auth/conflict 접근성·설명은 구현하지 않는다.
- fault-server는 production backend authorization, storage, backup나 운영 관측을 대체하지 않는다.

자동 test 통과는 실제 SQLite durability, background 실행, 실제 network나 `stable` 사람 승인을 증명하지 않는다.
