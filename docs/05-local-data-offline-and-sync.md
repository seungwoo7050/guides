# local data·offline·sync

오프라인 지원은 response를 cache하는 기능이 아니다. 사용자가 연결 없이 만든 변경을 durable하게 보존하고, 중단·중복·순서 역전·conflict 뒤에도 local과 server 상태를 설명 가능한 방식으로 수렴시키는 설계다.

## 목표

- UI가 읽는 local 정본과 server 정본의 역할을 구분한다.
- SQLite, app-owned file, secure storage와 preference storage의 용도를 나눈다.
- record 변경과 outbox command를 하나의 transaction으로 기록한다.
- command identity와 base version으로 중복·UNKNOWN 결과·충돌을 처리한다.
- sync worker를 중단·재시작 가능한 작은 단계로 만든다.
- local draft, local committed record, remote snapshot과 conflict를 동시에 보존한다.
- schema migration, orphan file와 storage pressure를 정상 운영 문제로 다룬다.

연결 실습은 [Stage 02](../exercises/field-notes/specs/02-offline-records.md)와 [Stage 04](../exercises/field-notes/specs/04-sync-conflicts.md)다. 순수한 전이 모델은 [`examples/sync-model`](../examples/sync-model/README.md)에 있다.

## local-first의 의미를 제한합니다

이 가이드에서 local-first는 다음을 뜻한다.

```text
핵심 화면은 local database를 읽는다.
사용자 save는 먼저 local transaction으로 완료된다.
remote 동기화는 outbox를 통해 별도 수명으로 진행된다.
서버 policy와 authorization은 여전히 remote가 소유한다.
```

모든 data가 영구적으로 local 정본이라는 뜻은 아니다. 예를 들어 account 권한, server-side workflow와 다른 사용자의 최신 변경은 server가 소유한다.

## 저장소를 데이터 성격으로 나눕니다

| 데이터 | 저장 위치 | 이유 |
|---|---|---|
| record·outbox·remote version | SQLite | transaction·query·migration·restart 복원 |
| 사진·첨부 bytes | app-owned file directory | 큰 binary와 streaming·upload |
| refresh token·작은 secret | SecureStore 계열 | platform-backed 보호 |
| theme·마지막 filter | preference/AsyncStorage 계열 | 작은 비민감 key-value |
| 일시 thumbnail·download | cache directory | 삭제돼도 재생성 가능 |
| UI press·loading | memory | process와 함께 사라져도 됨 |

AsyncStorage는 encrypted secret store가 아니다. SecureStore도 큰 JSON database가 아니다. 저장 API 하나로 모든 상태를 통합하지 않는다.

## Field Notes의 최소 schema

개념 schema:

```sql
CREATE TABLE records (
  id TEXT PRIMARY KEY,
  title TEXT NOT NULL,
  notes TEXT NOT NULL,
  status TEXT NOT NULL,
  observed_at TEXT NOT NULL,
  local_revision INTEGER NOT NULL,
  remote_version INTEGER,
  sync_state TEXT NOT NULL,
  updated_at_local TEXT NOT NULL,
  deleted_at_local TEXT
);

CREATE TABLE attachments (
  id TEXT PRIMARY KEY,
  record_id TEXT NOT NULL,
  local_uri TEXT NOT NULL,
  checksum TEXT NOT NULL,
  byte_size INTEGER NOT NULL,
  mime_type TEXT NOT NULL,
  remote_id TEXT,
  upload_state TEXT NOT NULL,
  FOREIGN KEY (record_id) REFERENCES records(id)
);

CREATE TABLE outbox (
  command_id TEXT PRIMARY KEY,
  entity_type TEXT NOT NULL,
  entity_id TEXT NOT NULL,
  operation TEXT NOT NULL,
  base_version INTEGER,
  payload_json TEXT NOT NULL,
  attempt_count INTEGER NOT NULL,
  next_attempt_at TEXT,
  state TEXT NOT NULL,
  created_at TEXT NOT NULL
);
```

실제 schema에는 index, foreign key 정책과 migration version이 필요하다. 핵심은 record와 command가 별도 row로 존재하고 안정적인 identity를 갖는다는 점이다.

## save와 outbox를 같은 transaction에 둡니다

잘못된 순서:

```text
record update commit
→ app 종료
→ outbox insert 실행되지 않음
```

이 record는 화면에는 저장됐지만 server로 보낼 근거가 없다.

반대 순서도 잘못될 수 있다.

```text
outbox insert
→ record update 실패
```

따라서 local 업무 변경과 command 생성을 하나의 SQLite transaction으로 묶는다.

```text
BEGIN
→ current local revision 확인
→ record update
→ 새 command id와 base version으로 outbox upsert/insert
→ attachment 참조 검증
COMMIT
```

commit 성공 뒤 UI는 `로컬에 저장됨, 동기화 대기`를 표시할 수 있다. remote 성공까지 form을 잠그지 않는다.

## command는 요청보다 오래 삽니다

HTTP request는 한 번의 실행이다. command는 사용자의 업무 의도다.

```ts
type RecordCommand = {
  commandId: string;
  recordId: string;
  operation: "upsert" | "delete";
  baseVersion: number | null;
  payload: RecordPayload;
  localRevision: number;
};
```

server는 같은 `commandId`가 반복될 때 동일한 업무 결과를 반환하거나 이미 처리된 결과를 찾을 수 있어야 한다. client가 timeout 뒤 새 id를 만들면 중복 방지 계약이 깨진다.

command payload를 현재 record에서 매번 다시 계산할지, 생성 시 snapshot으로 저장할지도 결정한다.

- snapshot은 사용자의 당시 의도를 보존한다.
- 최신 상태로 압축하면 중간 command를 줄일 수 있지만 audit와 delete/update 순서를 고려해야 한다.

Field Notes 기본 실습은 entity별 pending upsert를 최신 local revision으로 압축하되, active request의 command id는 유지한다.

여기서 `pending`은 **아직 한 번도 전송을 시도하지 않은 command**만 뜻한다. 한 번이라도 claim·전송한 command의 `commandId`, payload snapshot과 `baseVersion`은 UNKNOWN 결과를 재조회할 수 있도록 불변이다. 그동안 새 편집이 생기면 시도된 command를 바꾸지 않고 새 command를 만든다. 아직 시도하지 않은 동일 entity의 queued upsert만 명시된 coalescing policy에 따라 교체할 수 있다.

## outbox 상태를 명시합니다

```ts
type OutboxState =
  | "pending"
  | "in_flight"
  | "retry_wait"
  | "conflict"
  | "blocked_auth"
  | "permanent_failure"
  | "completed";
```

`in_flight`를 memory에만 두면 process 종료 뒤 영원히 멈출 수 있다. 시작 시 오래된 in-flight row를 pending으로 되돌리거나 lease expiration을 사용한다.

worker claim 예:

```text
transaction 시작
→ 실행 가능한 pending row 한 개 선택
→ lease owner·expiry와 in_flight 기록
→ commit
→ network request
→ 결과별 새 transaction
```

여러 worker나 foreground/background trigger가 동시에 실행돼도 같은 row를 무제한 중복 실행하지 않게 한다. 중복이 생겨도 command id로 server 결과가 안전해야 한다.

## sync worker는 하나의 bounded step입니다

나쁜 worker:

```text
모든 record가 끝날 때까지 while(true)
```

OS가 background 시간을 회수하거나 app가 inactive가 되면 중간 상태를 알기 어렵다.

권장 step:

1. 현재 session과 network hint를 확인한다.
2. 실행 가능한 command를 claim한다.
3. request에 deadline과 cancellation을 적용한다.
4. response를 runtime 검증한다.
5. success·conflict·retry·auth blocked 중 하나로 transaction한다.
6. 다음 실행 필요 여부를 scheduler에 알린다.
7. time budget이 남으면 다음 command로 이동한다.

각 command 뒤 durable checkpoint가 있으므로 어느 지점에서도 중단할 수 있다.

## 성공 response도 local newer edit를 덮을 수 있습니다

시나리오:

```text
local revision 3을 command A로 전송
→ 전송 중 사용자가 revision 4로 편집
→ command A 성공 response(version 8) 도착
```

response를 record 전체에 그대로 덮으면 revision 4가 사라진다.

완료 처리:

```text
active command의 localRevision 확인
remote snapshot과 remoteVersion은 version 8로 갱신
현재 localRevision이 active revision과 같으면 server normalized value로 clean
더 새 local revision이 있으면 local draft 유지
pending command의 baseVersion을 version 8로 재기준화
```

단, 재기준화 대상도 아직 시도하지 않은 queued command뿐이다. 이미 시도한 command의 payload나 `baseVersion`을 성공 response에 맞춰 고치면 idempotency identity가 달라진다. 새 base가 필요한 편집은 새 command로 표현한다.

성공 response도 무조건 신뢰하지 않는다. response의 command id가 active command와 다르거나, required field가 없거나, server version이 저장된 remote version보다 작으면 transaction 전에 `malformed_response` 또는 `version_regression`으로 거부한다. 이런 terminal contract 오류를 `synced`로 표시하거나 자동 retry loop에 넣지 않는다.

이 전이는 [`examples/sync-model`](../examples/sync-model/README.md)의 테스트가 보여 준다.

## version conflict에서 둘 다 보존합니다

server version 7을 기반으로 수정했지만 server가 이미 version 8이면 단순 last-write-wins는 다른 사용자의 변경을 잃을 수 있다.

conflict 상태에 필요한 값:

```ts
type RecordConflict = {
  baseVersion: number | null;
  local: RecordPayload;
  remote: RecordPayload & { version: number };
  commandId: string;
};
```

UI는 최소 다음 선택을 제공한다.

- remote를 사용하고 local 변경 폐기
- local을 새 baseVersion으로 다시 제출
- field별 비교·병합 후 새 command 생성
- 지금 결정하지 않고 conflict 목록에 보존

기존 command를 같은 baseVersion으로 무한 재시도하지 않는다. 해결은 새로운 명시적 command다.

## timestamp만으로 충돌을 해결하지 않습니다

client clock은 틀릴 수 있고 time zone·manual change·sleep 뒤 크게 달라질 수 있다. `updatedAt`은 사용자 표시와 진단에 유용하지만 authoritative ordering에는 server version, logical sequence 또는 명시적 conflict token을 사용한다.

## delete는 tombstone이 필요할 수 있습니다

offline delete 직후 row를 완전히 제거하면 sync할 command와 attachment cleanup 근거를 잃는다.

```text
record tombstone
+ delete command
+ local attachment retention policy
```

server delete 성공 뒤 일정 기간 tombstone을 유지할지, 즉시 purge할지 정한다. 다른 device에서 오래된 record가 다시 들어오는 resurrection도 고려한다.

## attachment와 DB의 원자성 한계를 다룹니다

filesystem write와 SQLite transaction은 하나의 원자 transaction이 아니다.

권장 순서 한 가지:

```text
system picker/camera 임시 URI
→ app-owned staging file로 copy
→ checksum·size 확인
→ DB transaction으로 attachment row 연결
→ commit 뒤 staging을 durable state로 표시
```

실패 정리:

- DB row 없는 오래된 staging file을 startup/maintenance에서 삭제
- row가 가리키지만 file이 없으면 `missing-local-file` 상태
- upload 성공 후 remote id 저장이 실패하면 command id로 remote 결과 재조회
- record delete와 file purge를 별도 재시도 가능한 cleanup job으로 처리

## migration은 release contract입니다

새 app version은 오래된 local DB를 열어야 한다.

migration 원칙:

- schema version을 명시한다.
- 한 단계씩 forward migration한다.
- transaction 가능한 migration은 원자적으로 실행한다.
- 큰 table rewrite는 storage·시간·중단을 고려한다.
- migration 실패 시 기존 DB를 무조건 삭제하지 않는다.
- downgrade 지원 여부를 명시한다.
- preview build에서 실제 이전 version DB fixture를 사용한다.

새 column default가 업무 의미를 바꾸는지, outbox payload schema와 server compatibility가 유지되는지도 확인한다.

## storage pressure와 backup 정책

모바일 storage는 무한하지 않다.

분류:

```text
삭제되면 안 됨
- unsynced record와 outbox
- 필요한 credential

재생성 가능
- remote snapshot 일부
- thumbnail
- downloaded attachment cache

정책에 따라 보존
- sync 완료된 원본 사진
- audit data
```

OS backup에 포함돼야 하는지, 새 device 복원 시 credential과 local DB 조합이 안전한지도 platform별로 결정한다. 민감 data와 device-specific key를 무심코 backup하지 않는다.

## offline UI는 상태를 숨기지 않습니다

record마다 최소 다음을 표현할 수 있다.

```text
저장되지 않은 draft
local 저장·sync 대기
sync 중
sync 완료
retry 대기
auth 차단
conflict
local file 누락
영구 실패 또는 지원 필요
```

상단의 단일 `offline` banner만으로 entity 상태를 대체하지 않는다. 사용자는 어떤 변경이 안전하게 local에 저장됐는지 알아야 한다.

## 결정적 검사 사례

- save transaction 직전·중간·직후 process 종료
- 같은 command 두 번 전송
- request timeout 뒤 server는 성공
- active sync 중 새 local edit
- response 순서 역전
- server version conflict
- 401 뒤 credential refresh
- attachment file copy 뒤 DB 실패
- DB row 뒤 file 삭제
- schema migration 중 storage 부족
- foreground와 background worker 동시 실행

시간·UUID·network·repository를 port로 분리해 pure state와 transaction policy를 검사한다.

## Stage 02 완료 기준

- offline에서 record를 생성·편집·삭제하고 재시작 뒤 복원한다.
- save와 outbox 생성이 한 transaction이다.
- UI는 SQLite를 읽고 remote request 완료를 직접 기다리지 않는다.
- credential, record, media와 preference 저장소가 분리돼 있다.
- orphan file과 missing file을 감지·정리한다.
- 실제 이전 schema fixture로 migration을 검사한다.

## Stage 04 완료 기준

- stable command id와 base version이 있다.
- timeout·중복·순서 역전에서 업무 변경이 중복 적용되지 않는다.
- active sync 중 새 edit가 success response에 덮이지 않는다.
- conflict가 local과 remote를 모두 보존한다.
- worker는 각 command 뒤 checkpoint하고 언제든 중단·재개된다.
- foreground와 background trigger가 동시에 와도 claim이 안전하다.

결정적 model 검사는 이 불변식의 전이를 증명하지만 SQLite의 실제 locking, OS process kill, file-system durability와 server-side idempotency까지 증명하지 않는다. repository fixture, fault server, process kill과 실제 기기 evidence를 함께 검토한다.

다음은 local data와 연결되는 camera·photo·location이 사용자 권한과 privacy를 어떻게 바꾸는지 다룬다. [permission·기기 기능·privacy](06-permissions-device-capabilities-and-privacy.md)로 이어간다.
