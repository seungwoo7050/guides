# Stage 02 — offline record·file·outbox

## 학습 결과

UI의 local 정본을 SQLite로 옮기고, network 없이 record를 생성·편집·삭제한 뒤 process restart에서도 committed state와 sync 근거를 복원한다. app-owned file과 SQLite가 하나의 transaction이 될 수 없다는 경계를 숨기지 않고 partial state를 조정한다.

이 Stage를 마치면 다음을 수행할 수 있어야 한다.

- draft, committed record, attachment bytes, attachment metadata와 outbox의 소유자를 구분한다.
- record 변경·attachment metadata·outbox command를 필요한 범위의 한 SQLite transaction으로 commit한다.
- filesystem 작업과 SQLite commit 사이 중단을 orphan·missing-file 상태로 수렴시킨다.
- local revision, stable command id와 base version의 의미를 보존한다.
- offline create/edit/delete와 duplicate save가 local repository 결과를 기준으로 UI에 반영되게 한다.
- 실제 v1 database fixture를 현재 schema로 data loss 없이 migration한다.
- 자동 fault test, process 종료와 actual device storage evidence의 차이를 설명한다.

## 시작 상태와 의도적 미완성

시작점은 Stage 01을 완료한 별도 learner 작업 복사본이다. 아래 목록은 **Stage 02 시작 직전 기준선**이며 누적 [`../reference`](../reference/)의 현재 기능 목록이 아니다. reference에는 후속 Stage 결과가 누적될 수 있으므로, Stage 02 연습에서는 Stage 01 결과를 보존한 learner 복사본에서 다음 미완성 상태를 채운다.

- record는 process memory의 fixture뿐이다.
- `Stage01RecordRepository`에는 durable save와 outbox가 없다.
- Stage 02 시작 기준의 sync 화면은 placeholder이며 실제 server·worker가 없다.
- Stage 02 시작 기준의 attachment 화면은 placeholder이고 app-owned file lifecycle이 없다.
- process restart 뒤 Stage 01에서 만든 record와 draft는 사라진다.

Stage 02는 route·validation·dirty-back·malformed/stale link behavior를 유지한 채 repository adapter를 교체한다. 실제 remote server, request retry와 conflict resolution은 Stage 04까지 의도적으로 미완성이다.

media picker UI는 Stage 03에서 추가하지만, 이 Stage는 고정된 비민감 test file을 통해 file ownership과 partial file reconciliation을 먼저 완성한다. 사진 기능이 아직 없다는 이유로 file 경계 검사를 미루지 않는다.

## public contract

정본은 [`../shared/src/contracts.ts`](../shared/src/contracts.ts)와 [`../shared/src/ports.ts`](../shared/src/ports.ts)다.

```ts
interface RecordRepository {
  ready(): Promise<void>;
  list(): Promise<FieldRecord[]>;
  get(id: string): Promise<FieldRecord | null>;
  saveWithCommand(input: {
    id: string;
    expectedLocalRevision: number | null;
    payload: RecordPayload;
  }): Promise<{ record: FieldRecord; command: RecordCommand }>;
  deleteWithCommand(input: {
    id: string;
    expectedLocalRevision: number;
  }): Promise<{ record: FieldRecord; command: RecordCommand }>;
}
```

file 경계는 다음 port가 시작점이다.

```ts
interface AttachmentFileStore {
  takeOwnership(temporaryUri: string): Promise<{
    ownedUri: string;
    checksum: string;
    byteSize: number;
  }>;
  remove(ownedUri: string): Promise<void>;
  listOrphans(): Promise<string[]>;
}

interface AttachmentRepository {
  attachOwnedFile(input: Omit<Attachment, "state">): Promise<Attachment>;
  markMissing(id: string): Promise<void>;
}
```

이 interface는 필요한 의미를 보여 주는 최소 경계다. SQLite table 이름, ORM, hook과 class 구조는 public contract가 아니다. 여러 port를 한 application use case에서 조합하더라도 다음 final behavior를 보존한다.

- 성공한 save는 record와 정확히 연결된 durable command를 함께 반환한다.
- revision mismatch나 transaction fault는 record·outbox를 모두 이전 상태로 둔다.
- attachment row는 검증된 app-owned URI, checksum, byte size와 state를 가진다.
- ephemeral picker/provider URI는 record·outbox의 durable payload가 아니다.
- outbox serialization에 attachment manifest가 필요하면 stable attachment id·checksum을 companion command나 versioned payload로 표현한다. 특정 JSON 모양보다 restart 뒤 같은 의도를 재구성할 수 있는지가 기준이다.

## 상태 소유권과 불변식

| 상태·자원 | 정본 | 바꾸는 사건 | 불변식 |
|---|---|---|---|
| form draft | memory 또는 명시한 draft store | input, checkpoint, discard/save | draft checkpoint와 업무 save를 같은 것으로 표시하지 않는다. |
| committed record·tombstone | SQLite | save/delete/migration/sync result | commit된 local intent는 process restart 뒤 남는다. |
| attachment bytes | app-owned file directory | ownership copy, cleanup, storage pressure | provider/cache URI 수명에 의존하지 않는다. |
| attachment metadata | SQLite | attach, reconcile, upload result | row/file 불일치를 명시적 state로 표현한다. |
| outbox command | SQLite | record transaction, worker result | committed 변경마다 재시도 가능한 근거가 있다. |
| remote version | server response를 반영한 SQLite field | sync success/conflict | local save만으로 remoteVersion을 증가시키지 않는다. |

정상 경로는 offline record save와 즉시 local UI 반영이다. 대표 경계는 owned file copy와 DB transaction 사이의 중단이고, 대표 실패는 record update 뒤 outbox insert가 실패하거나 v1 migration이 중단되는 경우다.

## local schema의 행동 계약

최소 의미는 다음과 같다.

- `records`: payload, local revision, remote version, sync state, local update와 tombstone
- `attachments`: record identity, app-owned URI, checksum, byte size, MIME, lifecycle state
- `outbox`: stable command id, entity/operation, base version, local revision, versioned payload, attempt state
- `schema metadata`: 현재 version과 migration history
- 선택한 경우 `drafts`: unfinished input checkpoint와 owner

index, column 이름과 library는 자유지만 다음 query가 가능해야 한다.

1. 일반 목록에서 tombstone을 제외하고 record를 정렬한다.
2. record와 현재 attachment state를 조회한다.
3. 실행 가능한 outbox command를 stable 순서로 찾는다.
4. row 없는 orphan file과 file 없는 attachment row를 조정한다.
5. migration이 어느 version까지 성공했는지 판정한다.

## record·outbox SQLite transaction

save의 application 순서는 다음 의미를 가진다.

```text
현재 record/localRevision 확인
→ domain validation
→ BEGIN
→ record upsert 또는 tombstone
→ attachment metadata/reference 검증
→ stable command snapshot insert/coalesce
→ COMMIT
→ repository 결과로 UI 갱신
```

필수 불변식:

- record가 commit됐는데 전송할 command가 없는 상태를 만들지 않는다.
- command만 commit되고 해당 local record revision이 없는 상태를 만들지 않는다.
- `expectedLocalRevision`이 다르면 최신 row를 덮지 않고 명시적 mismatch로 거부한다.
- local revision은 성공한 업무 save마다 증가한다.
- `remoteVersion`은 local save로 바뀌지 않는다.
- 아직 전송하지 않은 같은 entity upsert를 coalesce한다면 정확한 규칙과 command identity 변화를 검사한다.
- 이미 claim·전송한 command의 id, payload snapshot과 base version은 수정하지 않는다.

빠른 double tap을 button disable만으로 막았다고 끝내지 않는다. repository에서도 같은 expected revision 또는 idempotency policy로 중복 업무 effect를 거부해야 한다.

## filesystem과 SQLite의 원자성 한계

filesystem copy와 SQLite transaction은 하나의 원자 transaction이 아니다. 따라서 “file+record+outbox가 모두 원자적”이라고 선언하지 않는다. 원자적으로 보장하는 것은 SQLite 안의 record·attachment metadata·outbox 관계이며, file 경계는 staging과 reconciliation으로 보완한다.

허용되는 sequence 한 가지:

```text
비민감 test input URI
→ app-owned staging으로 copy
→ byte size·checksum·허용 type 검증
→ 가능한 경우 같은 filesystem 안의 owned final path로 이동
→ SQLite transaction: record/attachment row/outbox
→ commit 뒤 staging/final marker 정리
```

다른 two-phase sequence를 사용해도 된다. 대신 모든 중단 지점의 final state가 결정돼야 한다.

| 중단·불일치 | durable 관측 상태 | 필수 수렴 행동 |
|---|---|---|
| copy 전/중 실패 | record·outbox 이전 상태, partial staging 가능 | partial file을 attachment로 노출하지 않고 재시도/정리 |
| owned file 성공, DB transaction 실패 | row 없는 orphan file | 즉시 삭제하거나 다음 startup maintenance에서 식별·삭제 |
| DB commit 뒤 file 손실 | attachment row + missing file | `missing-local-file`, upload claim 차단, 제거/재선택 action |
| record tombstone, file delete 실패 | tombstone + cleanup pending | 업무 delete를 되돌리지 않고 cleanup 재시도 |
| 같은 file result 재처리 | 같은 identity/checksum 후보 | attachment·outbox를 중복 생성하지 않음 |

`AttachmentFileStore.takeOwnership()` 성공과 `AttachmentRepository.attachOwnedFile()` 성공 사이에 process가 죽는 경우를 반드시 주입한다. cleanup이 best effort여도 durable record/outbox 불변식은 손상되면 안 된다.

## delete와 draft 정책

offline delete는 row를 즉시 완전히 제거하지 않는다.

```text
record tombstone
+ delete command
+ attachment retention/cleanup marker
```

delete command가 처리되기 전까지 sync 근거가 남아야 한다. 일반 목록에서는 숨기더라도 restart 뒤 tombstone과 command를 조회할 수 있어야 한다.

명시적 save 전 draft policy는 다음 중 하나를 선택하고 UI에 맞게 설명한다.

- process와 함께 버리는 memory-only draft
- screen/record별 local checkpoint
- 별도 draft table의 versioned payload

checkpoint는 sync command를 만들지 않는다. 사용자가 Save를 확정했을 때만 record+outbox transaction이 발생한다.

## v1 migration 계약

문서로만 SQL을 보여 주지 말고 실제 v1 database fixture를 만든다.

v1 fixture에는 최소 다음이 있어야 한다.

- title·notes·observed time이 있는 기존 record 둘 이상
- Unicode/긴 text와 nullable 또는 legacy default 사례
- 현재 schema에 없는 status·sync/revision field
- migration 전 schema version `1`

현재 app이 처음 열 때 한 단계씩 migration한다. Field Notes 기본 정책:

- 기존 payload와 stable id를 보존한다.
- 새 local revision·sync state에 설명 가능한 default를 둔다.
- v1 record를 전송했다고 추측해 remote version을 만들지 않는다.
- migration만으로 사용자 의도를 뜻하는 outbox command를 임의 생성하지 않는다. 다음 명시적 edit/save가 새 command를 만든다.
- migration이 실패하면 schema version을 올리거나 기존 DB를 자동 삭제하지 않는다.
- 재시작 뒤 같은 migration을 안전하게 재시도하거나 복구 가능한 오류 화면을 제공한다.

v1→현재 migration 성공 뒤 record 수, 핵심 field, outbox 수와 schema version을 비교한다. downgrade 지원 여부는 known limits에 기록한다.

## 정상·경계·대표 실패 시나리오

| ID | 초기 persisted 상태 | 사건 | 기대 DB/file/outbox | 기대 UI |
|---|---|---|---|---|
| DB-01 | offline, new draft | Save | record revision 1 + pending command 한 transaction | 즉시 local 저장·동기화 대기 |
| DB-02 | existing revision 3 | edit/save | revision 4 + matching command snapshot | remote를 기다리지 않고 새 값 표시 |
| DB-03 | record update 지점 | outbox insert fault | record/outbox 모두 이전 상태 | 실패와 retry, draft 유지 |
| DB-04 | commit 성공 직후 | process 종료/restart | record·pending command 복원 | pending 상태 표시 |
| DB-05 | 같은 revision | double save/동시 edit | 한 commit 또는 명시적 revision mismatch | 중복 성공으로 속이지 않음 |
| DB-06 | saved record | offline delete/restart | tombstone + delete command + cleanup 근거 | 일반 목록에서 정책대로 숨김/설명 |
| FILE-01 | ownership copy 중 | zero-byte/partial/storage fault | attachment row 없음, partial staging만 가능 | record save 유지, attachment 실패 |
| FILE-02 | owned file 있음 | DB transaction fault | orphan 식별 가능, record/outbox 이전 상태 | attachment 연결 안 됨 |
| FILE-03 | attachment row 있음 | file 외부 삭제/storage loss | `missing-local-file`, upload claim 불가 | 제거·재선택 action |
| MIG-01 | 실제 v1 fixture | current app open | data 보존, current schema, fabricated command 없음 | 정상 목록 표시 |
| MIG-02 | v1 fixture | migration fault/저장 공간 부족 fake | v1 data·version 보존 | DB 삭제 없이 복구 안내 |
| ROW-01 | unknown enum/malformed row | list/get | 안전한 parse error/격리 정책 | crash 대신 지원 가능한 오류 |

## 자동 검사와 실패 거부

시간, ID, filesystem, SQLite fault point를 제어 가능한 adapter로 둔다. 최소 자동 검사는 다음 행동을 관찰한다.

- domain validation과 successful local revision 증가
- record+outbox transaction 성공 시 두 row의 identity/revision 일치
- record update 뒤 또는 outbox insert 전 fault에서 전체 rollback
- commit 직후 repository reopen에서 record·pending command 복원
- stale expected revision과 duplicate tap의 중복 effect 거부
- tombstone과 delete command의 동시 commit
- app-owned file checksum/byte size와 ephemeral URI 비보존
- partial copy, orphan file, missing row/file reconciliation decision
- v1 fixture migration의 row/field/version 보존
- migration fault 뒤 기존 DB 보존과 재시도
- unknown enum·malformed persisted row가 assertion crash가 아닌 명시적 failure가 됨

검사는 특정 SQL 문자열이나 table 순서가 아니라 transaction 전후의 observable snapshot을 비교한다. known-wrong repository에서 record만 남기거나 outbox만 남기는 fault가 반드시 거부되는지 확인한다.

## 실제 기기 관찰

Android와 iOS development build에서 각각 다음을 수행한다.

1. airplane mode에서 create·edit·delete하고 entity별 pending 상태를 본다.
2. save commit 직후 app process를 종료하고 launcher로 다시 열어 record·outbox를 확인한다.
3. memory draft와 committed record가 서로 다르게 복원되는지 확인한다.
4. 비민감 test file ownership 뒤 process를 종료해 orphan/missing policy를 실행한다.
5. v1 fixture DB를 설치한 이전 상태에서 현재 app로 upgrade/open한다. reinstall로 DB를 지우지 않는다.
6. 1,000개 fixture에서 목록·검색/scroll과 save의 기본 interaction을 기록한다.

disk-full은 실제 기기 storage를 위험하게 채우지 말고 fault adapter나 제한된 test volume으로 재현한다. 이것은 실제 filesystem durability evidence가 아니므로 simulation이라고 표시한다.

## 제출 evidence

```text
stage-02/
├── schema-and-migrations.md
├── v1-fixture-and-migration-output.txt
├── storage-ownership.md
├── transaction-fault-history.md
├── file-reconciliation-history.md
├── android-restart-results.md
├── ios-restart-results.md
├── automatic-test-output.txt
└── known-limits.md
```

`transaction-fault-history.md`의 각 행에는 initial record/outbox, fault 위치, transaction result와 reopen 뒤 final snapshot을 적는다. `file-reconciliation-history.md`에는 directory listing 자체를 무분별하게 공개하지 말고 익명 fixture id, checksum 일부, row state와 cleanup result만 남긴다.

사람 검토 질문:

1. 사용자가 보는 “저장됨”이 SQLite commit을 뜻하는가, remote success를 뜻하는가?
2. 어떤 실패에서도 committed record만 있고 command가 없는 상태가 생기지 않는가?
3. row/file 불일치가 조용히 사라지거나 무한 retry되지 않고 설명 가능한 상태인가?
4. migration 실패가 사용자 data 삭제로 자동 복구되는가?
5. Android/iOS storage·backup 차이와 실제로 검사하지 않은 범위를 밝혔는가?

## 자동 검증이 보장하지 않는 범위

- in-memory fake transaction은 실제 SQLite locking, WAL, fsync와 process kill durability를 보장하지 않는다.
- SQLite test는 platform filesystem rename·provider URI 수명과 storage pressure를 보장하지 않는다.
- fault adapter의 disk-full은 실제 기기·OS의 저용량 행동 전체를 보장하지 않는다.
- migration unit test는 signed previous app에서 current app로의 install/upgrade 경로를 보장하지 않는다.
- Stage 02 outbox는 server-side idempotency, timeout, response loss와 conflict 수렴을 보장하지 않는다.

## 비범위

- 실제 remote server와 HTTP request
- command claim/retry·UNKNOWN result·conflict resolution
- camera/photo picker permission UI
- background scheduler와 notification
- database/file encryption-at-rest 전체
- backup/restore와 multi-device merge의 완전한 정책
- store install/upgrade gate

## 완료 기준

- offline create·edit·delete가 SQLite 결과를 읽고 remote response를 기다리지 않는다.
- save/tombstone과 outbox가 같은 SQLite transaction이고 fault가 전체 rollback을 만든다.
- process restart 뒤 committed record, tombstone과 pending command가 복원된다.
- app-owned test file을 사용해 partial copy, orphan와 missing-file 상태를 감지·수렴시킨다.
- filesystem과 SQLite 사이의 비원자 경계와 그 한계를 문서화한다.
- draft checkpoint와 업무 save/outbox 의미가 분리돼 있다.
- 실제 v1 fixture를 data loss·fabricated outbox 없이 migration하고 실패 시 기존 DB를 보존한다.
- Android와 iOS development build에서 offline/restart 결과를 각각 기록하거나 미실사 platform을 `미검사`로 남긴다.

Stage 02 완료는 remote sync의 정확성을 증명하지 않는다. 다음 Stage는 같은 repository/file 불변식 위에 picker·camera와 필수 foreground location adapter를 연결한다.
