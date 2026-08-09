# Field Notes Stage 01–02 reference

Expo SDK 57와 Expo Router로 만든 실행 가능한 비교 기준이다. Stage 01의 안전한 startup navigation과 입력 경험을 유지하면서 Stage 02의 durable local-first 저장 경계를 연결한다.

## 현재 동작

- list/new/detail/edit/sync/settings route와 safe-area·keyboard-aware form
- framework-independent URL/record ID normalization, repository readiness 이후의 startup link/restoration
- SQLite schema v3의 `records`, `attachments`, `outbox`, `conflicts`, `processed_intents`, `schema_migrations`
- record save/delete tombstone과 immutable command snapshot의 단일 exclusive transaction
- `expectedLocalRevision` guard, process 재시작 뒤 record/outbox 복원, normal list에서 tombstone 제외
- v1 fixture의 ID·nullable notes·긴 Unicode payload를 보존하는 단계별 v1→v2→v3 forward migration
- provider/cache URI를 staging으로 복사·검증한 뒤 app-owned document URI로 이동하는 파일 소유권 전환
- startup/foreground에서 partial staging, metadata 없는 orphan, bytes 없는 attachment, delete cleanup을 명시적으로 수렴하는 reconciliation
- pending/missing/cleanup 결과를 화면에서 관찰하는 경로

`/sync`는 durable outbox를 읽기만 한다. Stage 04 전에는 remote transport, claim, retry, auth 또는 conflict resolution을 실행하지 않는다. 상세 화면의 test file 버튼은 permission이나 민감한 실제 media 없이 파일 소유권 경계를 확인하기 위한 작은 text fixture다. Camera/photo picker/location은 Stage 03 범위다.

## 검증

저장소 root에서 Node 24.19.0과 npm 11.17.0으로 실행한다.

```sh
npm ci
npm run typecheck
npm run test:stage01
npm run test:stage02
npm run bundle:android
npm run bundle:ios
```

Stage 02 Jest 검사는 production adapter와 같은 public contracts 및 mutation policy를 사용하는 결정적 in-memory database/file harness에서 final state를 검증한다. transaction rollback, 같은 revision의 중복 save, restart snapshot, migration failure/retry, partial copy, orphan, missing bytes, tombstone cleanup을 포함한다.

Jest는 Android/iOS의 native `expo-sqlite`와 `expo-file-system` 구현을 직접 실행하지 않는다. 따라서 이 검사는 실제 SQLite WAL/fsync, OS process kill, provider URI, disk-full, platform file protection 또는 native transaction scheduling을 보장하지 않는다. production adapter는 타입 검사와 양 플랫폼 Expo bundle로 확인하며, development build에서 다음 증거를 사람이 추가로 확인해야 한다.

1. 기록을 저장한 뒤 앱 process를 종료·재시작해 record와 `/sync` command가 함께 남는지
2. 동일 편집 화면을 두 곳에서 열어 한 write 이후 stale write가 거부되고 입력을 잃지 않는지
3. test file 추가 후 app 재진입에서 state가 유지되며, bytes를 제거한 fault fixture에서는 `missing-local-file`이 표시되는지
4. v1 fixture가 있는 device database를 복사해 migration 전후 row count, IDs와 payload가 보존되는지

bundle 성공도 simulator/device 동작, signing, permission dialog, disk durability 또는 store 제출을 증명하지 않는다.

## development build

```sh
npm run run:android --workspace=@field-notes/reference
npm run run:ios --workspace=@field-notes/reference
npm run start:dev-client --workspace=@field-notes/reference
```

`run:*`은 CNG native project와 development binary를 생성한다. `android/`와 `ios/`는 source of truth가 아니며 추적하지 않는다. 이후 `start:dev-client`가 Metro를 제공한다.
