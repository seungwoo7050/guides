# 누적 실습: Field Notes

Field Notes는 현장 조사자가 network가 불안정한 장소에서 기록·사진·선택적 위치를 저장하고, 나중에 server와 동기화하는 모바일 앱이다.

이 디렉터리는 빈 프로젝트 생성 지시만 제공하지 않는다. 실행 가능한 Stage 01 앱, 의도적으로 미완성인 learner skeleton, framework와 분리된 public contract, 단계별 대표 실패와 사람이 검토할 evidence 형식을 함께 제공한다. reference의 구현 모양이나 화면 문자열을 복사하는 것이 목표가 아니라 같은 사건 뒤 같은 업무 상태와 관측 결과를 만드는 것이 목표다.

## 디렉터리 역할

| 경로 | 역할 | 완료를 의미하지 않는 것 |
|---|---|---|
| [`shared`](shared/) | 단계가 공유하는 domain type, port, fixture와 framework-neutral contract runner | type을 구현했다는 사실만으로 device 동작을 보장하지 않는다. |
| [`skeleton`](skeleton/) | compile·launch 가능하지만 Stage 01 parser, deduplication, back policy와 일부 UI 검사가 의도적으로 미완성인 시작점 | 처음부터 test가 통과하는 정답 프로젝트가 아니다. |
| [`reference`](reference/) | list/detail/new/edit/sync/settings와 link·restoration 경계를 연결한 완전한 Stage 01 실행 예시 | SQLite, media, 실제 sync와 release 품질까지 완성된 앱이 아니다. |
| [`specs`](specs/) | Stage별 학습 결과, 시작 상태, public behavior, 실패 주입과 evidence 계약 | 문서를 읽거나 체크박스를 채운 것만으로 Stage를 통과하지 않는다. |
| `checks/` | acceptance matrix, device matrix와 evidence template | 자동 생성된 stable 판정표가 아니다. |

`reference/app/`은 route entry, `reference/src/`는 application·adapter·component 경계다. Stage 01의 정답 문자열을 찾기보다 [`shared/src/testkit.ts`](shared/src/testkit.ts)가 요구하는 public behavior와 실제 device 관찰을 함께 읽는다.

## 왜 하나의 누적 프로젝트인가

모바일 문제는 화면마다 분리되지 않는다.

```text
사진 선택 중 process 종료
→ app-owned file과 SQLite 조정
→ record와 outbox transaction
→ background 실행 기회 중단
→ notification으로 conflict 화면 진입
→ 새 binary/update compatibility
```

작은 독립 예제만 만들면 이 연결을 경험할 수 없다. Field Notes는 같은 record, attachment와 outbox를 Stage 01부터 06까지 확장한다.

## 기본 사용자 이야기

현장 조사자는 다음을 수행한다.

1. 연결이 없어도 record를 작성하고 저장한다.
2. picker 또는 camera로 사진을 추가하고, 원할 때만 현재 위치를 첨부한다.
3. app process가 종료되거나 기기가 offline이어도 committed record와 재시도 근거를 잃지 않는다.
4. 연결이 돌아오면 foreground 또는 허용된 background 기회에 동기화한다.
5. 다른 사용자의 변경과 충돌하면 local·remote를 비교해 선택한다.
6. notification이나 link를 통해 최신 sync 문제·record 화면으로 진입한다.
7. Android와 iOS에서 같은 업무 결과를 얻고 platform 차이와 미검사 범위를 기록한다.

## 핵심 상태와 소유권

```ts
type RecordSyncState =
  | "local-only"
  | "pending"
  | "syncing"
  | "synced"
  | "retry-wait"
  | "blocked-auth"
  | "conflict"
  | "failed";
```

최소 entity와 정본은 다음과 같다.

| 상태·자원 | 정본 | 바꾸는 사건 |
|---|---|---|
| `Record`·local revision | Stage 01 memory, Stage 02부터 SQLite | create, edit, delete, migration, sync result |
| `Attachment` metadata | SQLite | owned-file 연결, file reconciliation, upload result |
| attachment bytes | app-owned file directory | picker/camera result copy, cleanup, storage failure |
| `OutboxCommand` | SQLite | local save transaction, worker claim/result |
| `RecordConflict` | SQLite | version conflict, 사용자 resolution |
| credential | platform secure storage | login, refresh, logout/revocation |
| `NavigationIntent` | application coordinator의 bounded state | link, notification, restoration, internal action |
| process·permission·system UI | OS | launch/termination, Settings 변경, picker/camera, scheduler |

공개 type과 port는 [`shared/src/contracts.ts`](shared/src/contracts.ts)와 [`shared/src/ports.ts`](shared/src/ports.ts)가 소유한다. Stage가 진행되면서 adapter는 바뀌어도 application이 관찰하는 의미와 불변식은 유지한다.

## 시작과 기준 실행

저장소 root에서 재현 pin과 lockfile을 사용한다.

```sh
npm ci
npm run typecheck
npm run test:stage01
```

`npm run test:stage01`은 reference contract가 통과해야 한다. 아래 명령은 learner TODO가 남은 최초 skeleton에서 **실패해야 정상**이며, Stage 01을 구현한 뒤 통과시킨다.

```sh
npm run test:stage01:skeleton
```

reference의 Metro를 시작하려면 다음을 사용한다.

```sh
npm run start:dev-client --workspace=@field-notes/reference
```

이 가이드는 Stage 01부터 development-build-first다. 첫 native binary를 만들고 설치할 때는 host·Android/iOS 준비를 마친 뒤 다음 workspace script를 사용한다. 실제 기기에는 `--device`를 전달한다.

```sh
npm run run:android --workspace=@field-notes/reference -- --device
npm run run:ios --workspace=@field-notes/reference -- --device
```

한 platform만 가능한 host에서는 다른 platform을 통과로 추정하지 말고 `미검사`와 필요한 대체 evidence를 남긴다. Expo Go는 일부 JavaScript/UI를 빠르게 관찰하는 선택 경로일 뿐, custom scheme·native configuration·실제 permission·설치 binary의 Stage evidence가 아니다.

## 단계

| Stage | 누적 결과 | 대표 실패 |
|---:|---|---|
| [01](specs/01-runtime-navigation.md) | app shell, route, layout, cold/warm link와 restoration | malformed·stale·duplicate intent, dirty back, process restart |
| [02](specs/02-offline-records.md) | SQLite CRUD, app-owned file 경계와 outbox transaction | transaction rollback, partial file, v1 migration, restart |
| [03](specs/03-media-permissions.md) | picker·camera·foreground location adapter와 permission degradation | denied·revoked·unavailable, cancel, process recreation |
| [04](specs/04-sync-conflicts.md) | idempotent sync, timeout·중복·순서 역전·conflict | response loss, newer edit, version conflict |
| [05](specs/05-background-notifications.md) | opportunistic background sync와 notification intent | task 미실행·중복, cold notification entry |
| [06](specs/06-quality-release.md) | device matrix, native boundary, install·upgrade와 release evidence | runtime mismatch, migration/upgrade, 미검사 release gate |

Stage 01부터 순서대로 진행한다. React Native 경험자는 단순 화면 구현을 줄일 수 있지만, 각 Stage의 실패와 durable state를 동등한 프로젝트 evidence로 증명해야 건너뛸 수 있다.

## 권장 dependency 방향

```text
app/ 또는 routes/
  → features/application
      → domain·repository port
          ← SQLite/file/network/native adapter
```

권장 디렉터리 예시는 다음과 같다.

```text
app/                         Expo Router route
src/
├── domain/                  record·sync·conflict pure model
├── application/             use case·startup/sync coordinator
├── repositories/            local contract
├── adapters/
│   ├── sqlite/
│   ├── files/
│   ├── secure-session/
│   ├── http/
│   ├── permissions/
│   └── notifications/
├── features/                screen/view model
└── observability/
modules/                     필요한 경우 local Expo module
```

이 구조를 기계적으로 복제할 필요는 없다. domain이 Expo API나 route component를 직접 소유하지 않고, OS raw result가 application union으로 정규화되는 dependency 방향을 보존한다.

## 각 Stage의 진행 순서

```text
시작 상태와 의도적 미완성 확인
→ public contract와 소유자 확인
→ 정상·경계·대표 실패의 기대 결과 작성
→ 최소 구현
→ 자동 contract·fault 검사를 실행
→ Android/iOS development build에서 관찰
→ 실제 결과·차이·미검사 범위를 evidence에 기록
```

자동 검사에 맞는 class 이름이나 정답 문자열을 만드는 대신 다음을 검증한다.

- 최종 record·attachment·outbox 상태
- 사용자가 다음 action을 선택할 수 있는 UI
- process restart 뒤 복원되는 상태와 버려지는 상태
- 중단·중복·순서 역전 뒤 보존되는 불변식
- raw platform 결과가 application 의미로 정규화되는지

## 공통 evidence 계약

모든 Stage 결과에는 최소 다음을 기록한다.

```text
source revision
platform/device/OS
app version/build/runtime와 build profile
초기 DB·outbox·file·permission 상태
사용자 action과 주입한 실패 순서
기대 결과와 실제 결과
자동 test 이름·출력 또는 실제 device 기록
보장하지 않는 범위와 후속 작업
```

사람 판단이 필요한 화면 흐름은 억지로 screenshot 문자열 비교로 바꾸지 않는다. 대신 다음 질문에 답하는 recording 또는 단계 기록을 제출한다.

1. 실패 뒤 record와 draft를 잃지 않았는가?
2. 사용자가 현재 상태와 다음 행동을 이해할 수 있는가?
3. Android와 iOS에서 같은 업무 결과를 얻었는가? 차이는 무엇인가?
4. simulator·mock·development build evidence가 각각 무엇을 보장하지 않는가?

`checks/acceptance-matrix.md`와 `checks/evidence-template.md`를 자신의 실제 결과로 채운다. `미검사`를 `통과`로 바꾸지 않으며, record text·credential·정확한 위치·private file URI를 evidence에 넣지 않는다.

## 금지하는 지름길

- 화면 state만 만들고 process restart를 검사하지 않음
- network 성공 뒤에만 local record를 저장함
- record 변경과 outbox insert를 서로 다른 SQLite commit으로 둠
- filesystem과 SQLite가 하나의 원자 transaction이라고 주장함
- picker/camera가 준 임시 URI를 영구 data로 저장함
- capability availability와 permission state를 하나의 boolean으로 합침
- 위치가 선택 기능이라는 이유로 foreground location adapter 검증을 생략함
- `Date.now()`와 client timestamp만으로 conflict를 해결함
- background task와 notification delivery가 반드시 실행된다고 가정함
- Expo Go나 한 platform 결과로 native·다른 platform 완료를 선언함
- secret·record text·정확한 위치를 log 또는 제출 evidence에 포함함

## 최종 산출물

Stage 06이 끝나면 [capstone](../../capstone/README.md)의 architecture, sync history, Android/iOS device matrix, native boundary, release evidence와 known limits를 채운다.

`prepare.sh`·`verify.sh` 성공은 자동화 가능한 contract와 기준 결과의 일부만 증명한다. 실제 OS lifecycle, permission dialog, camera·picker, 보조기술, signing과 store 전달은 별도 evidence가 필요하다. 완성 UI나 자동 green만으로 stable이라고 선언하지 않으며, 최종 상태는 사람의 stable 검토를 받을 준비가 된 상태다.
