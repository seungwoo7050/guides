# Stage 04 — sync·중복·순서 역전·conflict

## 목적

Stage 02의 outbox command를 remote contract와 연결한다. timeout, response loss, duplicate delivery, 응답 순서 역전, active sync 중 새 edit, authentication 만료, 잘못된 응답과 version conflict에서도 **시도한 사용자 의도와 최신 local 의도를 모두 보존**한다.

이 단계는 production backend 운영을 만들지 않는다. 결정적 fault server와 공개 port로 모바일 client의 durable sync 행동을 검증한다.

먼저 [network·session·오류 계약](../../../docs/04-networking-session-and-error-contracts.md)과 [local data·offline·sync](../../../docs/05-local-data-offline-and-sync.md)를 읽는다.

## 시작 상태와 의도적 미완성

이 절은 Stage 03을 끝낸 learner 작업 복사본의 Stage 04 기준선이다. 누적 reference에 sync source·package나 test가 있더라도 현재 package scripts와 verify 결과가 연결한 공개 행동, 이 Stage의 fault history와 완료 조건을 각각 확인한다.

시작할 때 다음 자원이 있어야 한다.

- Stage 02의 `records`·`outbox` transaction과 schema migration
- Stage 03의 attachment row와 app-owned file
- 공용 `RecordCommand`, `RecordConflict`, `SyncTransport`, `SyncResult` 계약
- time·UUID·network result를 통제할 수 있는 test port
- 정상 응답과 fault를 결정적으로 선택할 수 있는 test server

Stage 03을 마친 learner 작업 복사본에서 다음은 의도적으로 미완성이다.

- claim/lease와 terminal transition
- attempted command snapshot 보존
- response runtime validation과 remote version 단조성 검사
- newer edit와 stale result 조정
- conflict 저장·해결
- auth block, retry exhaustion과 permanent failure 정책

저장소의 제공 `skeleton`과 그 rejection runner는 **Stage 01의 navigation·form TODO만** 소유한다. Stage 04 전용 skeleton rejection이 있다는 뜻이 아니다. Stage 04에서는 위 learner 기준선에 public sync contract를 적용하고, production reference behavior suite 및 sync-model known-wrong mutation 결과와 비교한다. 미완성 learner 구현이 관련 Stage 04 behavior case를 통과하면 해당 검사의 판정력을 보정한다.

## 관찰할 상태와 불변식

| 상태·자원 | 소유자 | 바꾸는 사건 | 보존할 불변식 |
|---|---|---|---|
| local record와 `localRevision` | record repository | 사용자 save/delete, conflict 해결 | 오래된 remote result가 최신 local payload를 덮지 않는다. |
| queued/claimed command | outbox repository | local transaction, claim, lease expiry, result transaction | 전송을 시도한 command는 stable `commandId`와 immutable attempted snapshot을 가진다. |
| remote snapshot/version | sync result transaction | 검증된 success/conflict | 이미 아는 remote version이 회귀하지 않는다. |
| conflict | conflict repository | version mismatch, 사용자 해결 | local·remote·base·원 command 근거를 함께 보존한다. |
| session block | session/application layer | 401, 외부 재인증 확인, 명시적 resume, account change | 인증 실패가 unsynced data를 삭제하거나 busy retry를 만들지 않는다. resume 자체를 credential 회복으로 간주하지 않는다. |
| attachment bytes와 link | file/attachment repository | upload, link, cleanup | upload와 record link의 부분 성공을 같은 성공으로 표시하지 않는다. |

정상 경로는 한 pending command가 한 번 적용되고 local/remote version이 수렴하는 경우다. 대표 경계는 전송 중 newer local edit다. 대표 실패는 server 적용 뒤 response를 잃고 같은 command를 다시 보내는 경우다.

## public remote contract

최소 operation은 다음 의미를 제공한다.

```text
UPSERT_RECORD(commandId, recordId, baseVersion, payload)
DELETE_RECORD(commandId, recordId, baseVersion)
UPLOAD_ATTACHMENT(commandId, recordId, checksum, bytes)
GET_COMMAND_RESULT(commandId)                 선택
GET_RECORD(recordId)                          검사·reconciliation용
```

server 또는 deterministic simulator는 다음 행동을 가져야 한다.

- 처음 본 `commandId`는 업무 효과를 최대 한 번 적용하고 결과를 memoize한다.
- 같은 `commandId`와 같은 attempted payload를 다시 받으면 같은 업무 결과를 반환한다.
- 같은 `commandId`에 다른 operation/payload/baseVersion이 오면 계약 위반으로 거절한다.
- record의 remote version은 성공한 업무 변경에서 단조 증가한다.
- `baseVersion`이 current version과 다르면 current remote snapshot을 포함한 conflict를 반환한다.
- fault control로 delay, reorder, response drop, 401, retryable 5xx, malformed body와 explicit permanent failure를 재현한다.

HTTP를 구현하는 모양은 필수가 아니다. `SyncTransport` fake와 fault server가 같은 공개 의미를 보이면 된다. 실제 backend를 쓰는 경우에도 동일한 acceptance case를 격리된 test data로 실행해야 한다.

제공 fault server와 production reference suite가 자동으로 다루는 wire command는 record upsert/delete다. `UPLOAD_ATTACHMENT`와 remote record-link protocol은 learner가 선택한 public contract로 구현하고 아래 partial-failure evidence를 별도로 제출한다. 제공 server에 해당 endpoint가 없다는 사실을 attachment 성공 근거로 바꾸지 않는다.

## attempted command는 불변입니다

local save transaction은 한 번의 사용자 의도를 다음 snapshot으로 기록한다.

```text
commandId
operation
recordId
baseVersion
localRevision
payload 또는 tombstone
createdAt
```

worker가 request를 시작한 순간 이 값은 **attempted command**가 된다.

- timeout·response loss·process restart 뒤 retry는 같은 `commandId`, operation, `baseVersion`, `localRevision`, payload를 사용한다.
- active request 중 사용자가 다시 편집하면 기존 command를 바꾸지 않고 새 local revision과 새 command intent를 만든다.
- retry할 때 최신 record payload를 다시 읽어 이미 시도한 command에 덮어쓰지 않는다.
- queue 압축이나 rebase가 필요하면 아직 시도하지 않은 command만 transaction 안에서 대체할 수 있다. 새 base/payload는 새 `commandId`로 기록한다.
- attempted command를 삭제하기 전에 success/conflict/permanent 같은 terminal 근거가 durable하게 남아야 한다.

이 불변식은 server가 같은 `commandId`를 idempotency key로 신뢰할 수 있게 한다. payload를 바꾸면서 ID만 유지하면 response loss 뒤 어느 의도가 적용됐는지 설명할 수 없다.

## bounded worker 계약

foreground manual/app-active와 이후 Stage 05의 background trigger는 같은 bounded worker를 호출한다.

```text
실행 가능한 command claim
→ attempted snapshot과 in-flight lease 기록
→ session/network 준비
→ request with deadline
→ response runtime validation
→ commandId·version·revision 기준 result transaction
→ lease 완료 또는 expiry 복구
```

worker는 한 번에 처리할 item/time budget을 가진다. queue 전체를 비울 때까지 component나 background callback을 붙잡지 않는다.

terminal/visible 상태는 최소 다음을 구분한다.

| 결과 | durable 전이 | 자동 다음 행동 |
|---|---|---|
| success | 검증된 remote snapshot/version과 command 완료 근거 저장 | newer command가 있으면 다음 기회에 실행 |
| conflict | local/remote/base/command를 conflict로 저장 | 자동 retry하지 않음 |
| retry-wait | attempted command, attempt count와 next eligible time 보존 | bounded backoff 뒤 같은 command retry |
| blocked-auth | command를 보존하고 account/session block 표시 | credential 회복 전 자동 전송 중단 |
| permanent-failure | command와 normalized reason을 terminal evidence로 보존 | 사용자 수정·discard 없이 자동 retry하지 않음 |

cancel이나 timeout은 server 적용 여부를 모르면 success도 확정 failure도 아닌 UNKNOWN이다. 이때 `retry-wait`로 이동해 같은 command를 재조정한다.

## success와 순서 역전

### active revision이 아직 최신일 때

```text
result.commandId == claimed commandId
result.remoteVersion >= known compatible version
current localRevision == attempted localRevision
→ remote snapshot/version 갱신
→ server normalization을 허용한 필드만 local에 반영
→ command 완료
→ syncState=synced
```

### 전송 중 newer edit가 생겼을 때

```text
result.commandId == older attempted command
current localRevision > attempted localRevision
→ 검증된 remote snapshot/version만 sync base로 기록
→ current local payload 보존
→ 아직 미시도인 newer intent를 새 base와 새 commandId로 재기록
→ syncState=pending
```

A와 B response가 역순으로 도착해도 response 도착 순서를 정본으로 쓰지 않는다. `commandId`, attempted revision, 현재 local revision과 known remote version으로 판정한다.

### remote version regression

- result version이 현재 known remote version보다 작으면 stale/malformed result로 거절하고 success로 표시하지 않는다. 이미 terminal인 older command의 duplicate면 관측만 남기고, 현재 claimed command의 result면 malformed-response retry/permanent 정책을 적용한다.
- 같은 version의 duplicate result는 같은 command와 같은 remote snapshot을 가리킬 때만 idempotent하게 수용한다.
- 같은 version인데 payload가 다르거나 미래/음수/비정수 version이면 malformed response다.
- version validation 실패는 local record를 바꾸지 않고 normalized trace와 attempted command를 보존한다.

## response loss·duplicate·malformed·401·permanent

| 주입 사건 | 기대 공개 행동 | 금지되는 행동 |
|---|---|---|
| server apply 후 response loss | UNKNOWN으로 기록하고 동일 command를 retry; server effect 1회 | 새 ID로 같은 effect 재실행 |
| duplicate request/response | 같은 memoized result를 idempotent하게 적용 | local revision/version 두 번 증가 |
| response reorder | stale result는 최신 local payload를 덮지 않음 | arrival order로 synced 판정 |
| 401 | `blocked-auth`, unsynced record/outbox 보존; 외부 재인증 확인 뒤 명시적 resume | busy retry, local data 삭제, resume를 credential 생성·refresh 증거로 표시 |
| malformed success body | success 전이 금지, `malformed-response` retry-wait; 제한 초과 시 permanent evidence | type assertion으로 record/version 저장 |
| explicit permanent failure | `failed`와 reason, attempted snapshot 보존; 사용자 수정/discard action | 무한 retry 또는 command 조용히 삭제 |

malformed response의 retry limit과 backoff 값은 구현이 정하되 deterministic test에서 clock으로 통제하고 evidence에 기록한다. permanent 전환은 transport 실패를 사용자 업무가 실패했다고 과장하지 않도록 reason과 recovery action을 분리한다.

## conflict 전이와 해결

server current version과 payload를 runtime 검증한 뒤 다음 의미를 durable하게 저장한다.

```text
RecordConflict {
  commandId,
  recordId,
  baseVersion,
  local payload,
  remote payload + version
}
```

UI는 최소 다음 선택을 제공한다.

1. **remote 사용**: local record를 remote로 갱신하고 conflict를 종료한다.
2. **local 재제출**: remote version을 새 base로 새 command ID와 함께 만든다.
3. **field 병합**: 사용자가 만든 새 payload를 새 command로 기록한다.
4. **나중에 결정**: conflict와 두 snapshot을 그대로 보존한다.

해결 도중 remote가 다시 바뀌면 새 conflict를 만든다. 원래 command를 같은 base로 계속 보내거나 두 snapshot 중 하나를 조용히 버리지 않는다.

## attachment와 queue 경계

- attachment checksum과 byte size를 upload command에 포함한다.
- 같은 command/checksum의 duplicate upload를 remote가 식별한다.
- upload bytes 성공과 record link 성공을 분리한다.
- response loss 뒤에는 command result를 조회하거나 같은 attempted command를 재실행한다.
- local file이 없으면 network retry가 아니라 `missing-local-file` 또는 permanent 사용자 조치 상태다.
- delete 뒤 이전 upsert/upload가 record를 되살리지 않도록 dependency를 판정한다.
- 한 record의 반복 실패가 다른 entity의 eligible command를 영원히 막지 않도록 fairness를 둔다.

대규모 resumable upload와 media transcoding은 선택 확장이다.

제공 Stage 04 자동 suite는 record command의 lease/checkpoint와 fault history를 검사한다. attachment upload 성공 뒤 local checkpoint/link 실패, local file 누락과 remote link reconciliation은 learner 구현의 결정적 fake 또는 격리된 test endpoint 결과와 사람 검토 trace를 함께 제출한다. 실제 bytes, private URI와 사용자 record 내용은 evidence에 넣지 않는다.

## 필수 failure matrix

다음은 구현 모양이 아니라 event 뒤 DB/outbox/remote/UI 관측 결과로 검사한다.

1. 같은 command 두 번 전달
2. server 성공 직후 response drop, client restart와 retry
3. command A/B response 순서 역전
4. A in-flight 중 newer local edit
5. baseVersion conflict와 해결 중 다시 remote 변경
6. 401과 동시에 여러 command claim
7. retryable 5xx와 bounded backoff
8. malformed success body와 retry limit
9. current remote version보다 낮은 success response
10. explicit permanent failure
11. foreground/background worker 동시 claim
12. process 종료로 만료된 lease
13. attachment upload 성공 후 local result transaction 실패 — learner 자동 trace + 사람 검토
14. local attachment file 누락 — learner 자동 trace + 사람 검토

## 자동 검증

자동 근거는 서로 다른 세 층을 구분한다.

```sh
npm run test:stage04
python3 scripts/expect_skeleton_rejection.py
python3 scripts/verify_mutants.py
```

- `test:stage04`는 production reference의 SQLite adapter·fetch transport와 sync-engine/fault-server 공개 행동을 검사한다. response loss 뒤 같은 snapshot과 apply count 1, newer edit·reorder·version regression, 401 block, malformed bounded exhaustion, permanent, conflict, lease expiry와 concurrent claim을 판정한다.
- `expect_skeleton_rejection.py`는 Stage 01 reference baseline과 Stage 01 learner skeleton의 두 명명된 behavior rejection만 확인한다. Stage 04 TODO rejection이라고 확대하지 않는다.
- `verify_mutants.py`는 순수 [`examples/sync-model`](../../../examples/sync-model/README.md)의 permanent-as-synced, version regression 수용, malformed payload 수용 mutant를 거부한다. production SQLite/fetch source mutation이나 attachment protocol을 검사하지 않는다.
- attachment upload/link partial failure는 제공 reference 자동 suite 밖이다. learner가 같은 상태·불변식을 자신의 deterministic test와 사람 trace로 증명한다.

검사는 내부 SQL 문자열, 함수 이름이나 정답 source를 찾지 않는다. public port 호출, normalized trace, repository snapshot과 server apply history를 판정한다.

[`examples/sync-model`](../../../examples/sync-model/README.md)의 전이와 fault server 결과를 자신의 구현에도 연결한다.

## 사람·실제 기기 검토

- offline save 뒤 network 복구 중 UI가 pending/retry/conflict/auth 상태와 다음 action을 설명하는가?
- app background/foreground 또는 process restart 중 같은 업무 의도가 중복 표시되지 않는가?
- conflict 화면을 TalkBack/VoiceOver와 큰 글자에서 비교·해결할 수 있고 draft가 보존되는가?
- 큰 attachment 처리 중 app 이동·중단에서 spinner가 무한히 남지 않는가?
- upload bytes 성공과 record link/checkpoint 실패가 서로 다른 상태와 recovery action으로 보이는가?
- account 만료 뒤 local unsynced data의 owner와 삭제/재인증 선택을 오해 없이 설명하는가?

UI 명료성·접근성은 screenshot 하나로 자동 판정하지 않는다. device/build, 수행자, 질문별 판단과 screen recording 또는 accessibility trace를 남긴다.

## 제출 증거

```text
stage-04/
├── remote-contract.md
├── outbox-state-machine.md
├── fault-history/
│   ├── response-loss-and-duplicate.md
│   ├── reorder-and-newer-edit.md
│   ├── auth-malformed-permanent.md
│   └── conflict-and-version-regression.md
├── attachment-upload-link-review.md
├── automated-test-output.txt
└── conflict-ui-review.md
```

각 fault history에는 source revision, 초기 DB/outbox/remote 상태, fault control, command snapshot, event 순서, final local/remote 상태와 test exit status를 적는다.

## 완료 조건

- duplicate·timeout·response loss가 remote 업무 변경을 두 번 만들지 않는다.
- attempted command는 retry·newer edit 뒤에도 바뀌지 않는다.
- response reorder와 remote version regression이 최신 local state를 덮지 않는다.
- 401·malformed response·permanent failure를 구분하고 command evidence를 보존한다. 외부 재인증 확인과 명시적 resume를 credential 생성 증거와 구분한다.
- conflict는 local과 remote를 모두 보존하고 새 command로 명시적으로 해결한다.
- process restart와 concurrent trigger에서 eligible outbox가 다시 진행된다.
- attachment upload와 record link의 부분 실패를 learner 자동 trace와 사람 검토로 설명하고 재조정할 수 있다.
- 자동 검사와 사람 UI/device evidence의 보장 범위를 구분했다.

## 비범위와 알려진 한계

- real-time collaborative text merge와 CRDT
- distributed transaction 또는 exactly-once network delivery 보장
- 무제한 offline 기간의 모든 server authorization/policy 보장
- production backend·identity provider 운영
- 대규모 resumable media upload/transcoding

deterministic server 통과는 실제 radio, proxy, TLS, production policy나 service outage를 보장하지 않는다. 이 단계가 보장하는 것은 정의한 command 계약과 주입한 event에서 client 상태·불변식이 보존된다는 범위다.
