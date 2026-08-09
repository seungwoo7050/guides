# Field Notes Stage 01–04 reference

Expo SDK 57와 Expo Router로 만든 실행 가능한 비교 기준이다. Stage 01의 안전한 startup navigation, Stage 02의 durable local-first 저장 경계, Stage 03의 최소 권한 media·foreground location에 Stage 04의 수동 bounded sync를 연결한다.

## 현재 동작

- list/new/detail/edit/sync/settings route와 safe-area·keyboard-aware form
- framework-independent URL/record ID normalization, repository readiness 이후의 startup link/restoration
- SQLite schema v5의 `records`, `attachments`, `outbox`, `conflicts`, `sync_checkpoints`, `processed_intents`, `external_media_operations`, `schema_migrations`
- record save/delete tombstone과 immutable command snapshot의 단일 exclusive transaction
- `expectedLocalRevision` guard, process 재시작 뒤 record/outbox 복원, normal list에서 tombstone 제외
- v1 fixture의 ID·nullable notes·긴 Unicode payload를 보존하며 external media v4와 durable sync v5까지 전진하는 단계별 v1→v5 migration
- provider/cache URI를 staging으로 복사·검증한 뒤 app-owned document URI로 이동하는 파일 소유권 전환
- startup/foreground에서 partial staging, metadata 없는 orphan, bytes 없는 attachment, delete cleanup을 명시적으로 수렴하는 reconciliation
- pending/missing/cleanup 결과를 화면에서 관찰하는 경로
- `expo-image-picker`의 camera와 system photo picker를 분리한 adapter와 `not-required` picker permission
- camera permission을 기능 버튼에서만 요청하고 capture 직전에 다시 확인하는 revoke 경계
- launch 전에 기록하는 단일 durable external-operation slot, Android pending-result recovery와 duplicate claim 거부
- picker/camera temporary URI를 공통 staging→owned→atomic metadata pipeline으로 수렴하는 흐름
- `expo-location` foreground one-shot 측정과 memory-only preview; 사용자가 포함을 다시 선택할 때만 record/outbox에 좌표·accuracy·측정 시각 저장
- app active 복귀 시 상태 재조회와 늦은 위치 결과 폐기; startup prompt·last-known fallback·자동 민감 action 없음
- 첫 claim에서만 고정되는 attempted command, stable command ID retry, durable lease/retry/auth/permanent/completed state와 checkpoint history
- success checkpoint에서 known remote version을 전진시키되 최신 local edit를 보존하고 아직 미시도인 command만 새 ID/base로 교체하는 transaction
- local/remote 양측과 attempted evidence를 보존하는 conflict 및 remote 수용·최신 local 재전송 해결 경로
- configurable local/test URL의 fetch transport, credential lookup을 포함한 caller abort와 10초 request deadline, 최대 5회 UNKNOWN 뒤 terminal이 되는 bounded foreground worker

`/sync`의 버튼을 누를 때만 network worker가 실행된다. 시작·app-active만으로 remote 요청, auth 재개 또는 conflict resolution을 실행하지 않는다. Camera는 명시적인 촬영 action, picker는 사용자가 고른 한 항목만 받는다. Location은 선택 가능한 record field이며 생략·거절·timeout도 정상적인 text record 결과다. Background sync/location, 지속 tracking, video, microphone과 전체 photo library 관리는 구현하지 않는다.

## 검증

저장소 root에서 Node 24.19.0과 npm 11.17.0으로 실행한다.

```sh
npm ci
npm run typecheck
npm run test:stage01
npm run test:stage02
npm run test:stage03
npm run test:stage04
npm run bundle:android
npm run bundle:ios
```

Stage 02 Jest 검사는 production adapter와 같은 public contracts 및 mutation policy를 사용하는 결정적 in-memory database/file harness에서 final state를 검증한다. Stage 03 검사는 raw availability/permission mapping, startup prompt 0회, picker library permission API 0회, denied/restricted/limited/revoked/cancel, partial copy·invalid/oversize media, pending recovery·expiry·duplicate result, optional/late/invalid location과 unsent location removal을 final state로 확인한다. Stage 04 검사는 Node 24의 in-memory SQLite에 production migration/repository SQL을 그대로 실행해 response loss, duplicate delivery, reorder, checkpoint rollback, restart/expired lease, auth resume, malformed/version regression, permanent failure, newer edit rebase, conflict resolution과 v4 conflict 보존을 확인한다. Fetch timeout은 실제 sleep 없이 composed AbortSignal을 전진시켜 durable `retry_wait` 결과를 검사한다.

Jest는 Android/iOS의 native SQLite, FileSystem, ImagePicker, Location 또는 radio stack을 직접 실행하지 않는다. Node SQLite의 transaction 결과도 mobile fsync·process lock과 동일하다는 뜻은 아니다. 따라서 이 검사는 실제 WAL/fsync, OS process kill, provider/iCloud URI, hardware camera, dialog, disk-full, TLS/proxy, platform file protection 또는 native scheduling을 보장하지 않는다. production adapter는 타입 검사, CNG와 양 플랫폼 Expo bundle로 확인하며, development build에서 다음 증거를 사람이 추가로 확인해야 한다.

1. 기록을 저장한 뒤 앱 process를 종료·재시작해 record와 `/sync` command가 함께 남는지
2. 동일 편집 화면을 두 곳에서 열어 한 write 이후 stale write가 거부되고 입력을 잃지 않는지
3. fresh install startup에서 permission dialog가 없고 system picker가 library-wide permission 없이 cancel/success하는지
4. camera deny와 `canAskAgain=false`, Settings revoke 뒤 picker/text-only 흐름이 유지되고 자동 relaunch가 없는지
5. Android `활동 유지 안 함`에서 pending result가 복구되거나 명시적 interrupted가 되며 attachment가 한 개인지
6. foreground 위치를 preview 뒤 포함/버림하고 background 복귀의 늦은 결과가 저장되지 않는지
7. v1/v4 fixture가 있는 device database를 복사해 v5 migration 전후 row count, IDs, payload와 conflict evidence가 보존되는지
8. local fault server에서 response loss·401·conflict를 주입해 같은 command ID, restart 뒤 lease 회수와 최신 local edit 보존이 화면에서도 관측되는지

bundle 성공도 simulator/device 동작, signing, permission dialog, disk durability 또는 store 제출을 증명하지 않는다.

## development build

```sh
npm run run:android --workspace=@field-notes/reference
npm run run:ios --workspace=@field-notes/reference
npm run start:dev-client --workspace=@field-notes/reference
```

`run:*`은 CNG native project와 development binary를 생성한다. `android/`와 `ios/`는 source of truth가 아니며 추적하지 않는다. 이후 `start:dev-client`가 Metro를 제공한다.

수동 sync 기본 URL은 `http://127.0.0.1:3104/commands`다. simulator/device에서 host loopback 주소가 다르면 development build 전에 `EXPO_PUBLIC_FIELD_NOTES_SYNC_URL`을 허가된 local/test server URL로 설정한다. URL에 credential을 넣지 않는다. reference는 optional bearer provider와 HTTP client만 제공하며 운영 backend, 계정 발급, TLS termination 또는 multi-user authorization을 만들지 않는다. 401의 `blocked-auth`는 retry timer로 풀리지 않는다. 외부 session/auth 경로가 credential을 실제로 복구한 뒤에만 `/sync`의 명시적 재개 action을 눌러야 하며, 버튼 자체는 인증하지 않는다. `Content-Length`가 있으면 1 MiB 초과를 읽기 전에 거부하지만, post-read 문자 제한은 streaming memory cap을 보장하지 않는다.

`expo-image-picker` config는 microphone을 끄고, `expo-location` config는 when-in-use만 허용하며 iOS/Android background location과 Android foreground location service를 끈다. config 변경 뒤 development binary를 새로 만들어야 한다. 생성된 Android manifest에는 camera와 coarse/fine foreground location만, iOS plist에는 camera/photo 설명과 `NSLocationWhenInUseUsageDescription`만 있는지 별도로 검토한다.

`exif: false`는 adapter가 EXIF object를 요청하지 않는다는 뜻이며 원본 image bytes에서 EXIF가 제거됐음을 보장하지 않는다. 원본 filename·MIME·asset ID도 권위 있는 metadata로 취급하지 않는다. 로그와 operation failure에는 provider URI, 사진 bytes, record text 또는 정확한 좌표를 넣지 않는다. Server content validation, EXIF stripping, malware 검사, store privacy declaration과 실제 device 결과는 사람이 별도로 검토한다.
