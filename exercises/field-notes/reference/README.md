# Field Notes Stage 01–05 reference

Expo SDK 57와 Expo Router로 만든 실행 가능한 비교 기준이다. Stage 01의 안전한 startup navigation, Stage 02의 durable local-first 저장 경계, Stage 03의 최소 권한 media·foreground location, Stage 04의 bounded sync에 Stage 05의 lifecycle·notification response 경계를 연결한다.

## 현재 동작

- list/new/detail/edit/sync/settings route와 safe-area·keyboard-aware form
- framework-independent URL/record ID normalization, repository readiness 이후의 startup link/restoration, bootstrap 중 warm URL 최신 1개 보존
- link·notification이 함께 쓰는 bounded in-process route arbiter; route 적용 실패 시 reservation을 release하고 성공 뒤에만 dedupe 확정
- SQLite schema v6의 `records`, `attachments`, `outbox`, `conflicts`, `sync_checkpoints`, leased `processed_intents`, `lifecycle_settings`, `external_media_operations`, `schema_migrations`
- record save/delete tombstone과 immutable command snapshot의 단일 exclusive transaction
- `expectedLocalRevision` guard, process 재시작 뒤 record/outbox 복원, normal list에서 tombstone 제외
- v1 fixture의 ID·nullable notes·긴 Unicode payload를 보존하며 external media v4, durable sync v5, notification lease/state v6까지 전진하는 단계별 v1→v6 migration
- provider/cache URI를 staging으로 복사·검증한 뒤 app-owned document URI로 이동하는 파일 소유권 전환
- startup/foreground에서 partial staging, metadata 없는 orphan, bytes 없는 attachment, delete cleanup을 명시적으로 수렴하는 reconciliation; media 완료와 foreground maintenance는 같은 직렬 queue 사용
- pending/missing/cleanup 결과를 화면에서 관찰하는 경로
- `expo-image-picker`의 camera와 system photo picker를 분리한 adapter와 `not-required` picker permission
- camera permission을 기능 버튼에서만 요청하고 capture 직전에 다시 확인하는 revoke 경계; second-query/bridge 예외는 durable interrupted/failed 결과로 수렴
- launch 전에 기록하는 단일 durable external-operation slot, Android pending-result recovery와 duplicate claim 거부
- picker/camera temporary URI를 공통 staging→owned→atomic metadata pipeline으로 수렴하는 흐름
- `expo-location` foreground one-shot 측정과 memory-only preview; 사용자가 포함을 다시 선택할 때만 record/outbox에 좌표·accuracy·측정 시각 저장
- app active 복귀 시 상태 재조회와 늦은 위치 결과 폐기; startup prompt·last-known fallback·자동 민감 action 없음
- 첫 claim에서만 고정되는 attempted command, stable command ID retry, durable lease/retry/auth/permanent/completed state와 checkpoint history
- success checkpoint에서 known remote version을 전진시키되 최신 local edit를 보존하고 아직 미시도인 command만 새 ID/base로 교체하는 transaction
- local/remote 양측과 attempted evidence를 보존하는 conflict 및 remote 수용·최신 local 재전송 해결 경로
- configurable local/test URL의 fetch transport, credential lookup을 포함한 caller abort와 10초 request deadline, 최대 5회 UNKNOWN 뒤 terminal이 되는 bounded foreground worker
- React와 독립적인 공용 sync runtime factory, module-scope background task definition, OS expiration/deadline abort와 durable checkpoint 기반 result 판정
- cold `getLastNotificationResponse()`와 warm listener의 단일 직렬 queue, v6 claim/lease/dedup/terminal evidence, 현재 SQLite 상태 재확인 뒤 route 적용
- 열린 edit/new draft에서 notification route를 자동 덮지 않고 claim을 release해 native response와 명시적 retry action을 보존하는 경계
- Android channel→permission→token의 명시적 사용자 action과 redacted UI 상태; EAS project ID가 없으면 channel·permission 뒤 `token-failed`로 멈추며 raw token·notification payload·content는 SQLite나 UI/log에 저장하지 않음

production reference에서 network worker는 `/sync`의 명시적 foreground 버튼으로만 실행된다. Background task는 한 개를 정의·관찰·등록할 수 있지만 `automatic_sync_enabled=false`가 기본이자 고정 경계라 headless callback은 worker를 시작하지 않고 disabled/no-work로 관찰된다. OS callback은 SDK가 제공하는 제한된 enum의 `Success`로 종료하지만, 이는 sync 완료나 command checkpoint의 증거가 아니다. app-active와 notification도 production network egress를 시작하지 않는다. lifecycle-engine과 injected reference test는 manual/app-active/background/notification이 같은 coordinator/worker 계약을 쓰고 background 미실행 뒤 app-active가 수렴할 수 있음을 검증하지만, 이 production app에서 자동 전송이 실행됐다고 주장하지 않는다.

Camera는 명시적인 촬영 action, picker는 사용자가 고른 한 항목만 받는다. Location은 선택 가능한 record field이며 생략·거절·timeout도 정상적인 text record 결과다. Background location, 지속 tracking, remote push delivery, installation/backend mapping, video, microphone과 전체 photo library 관리는 구현하지 않는다. production notification registration action은 Android channel/permission/token 경로만 연결하며 iOS에서는 `unsupported-platform`을 반환한다. iOS permission/token enrollment는 구현·검사됐다고 주장하지 않는다. `local-demo-account`는 notification account mismatch 동작을 보여 주는 로컬 고정값일 뿐 실제 로그인/session/backend account가 아니다.

`expo-image-picker`에는 camera hardware preflight API가 없으므로 production camera availability는 Android/iOS에서 거짓 `available` 대신 `limited/unknown-until-explicit-launch`로 표시한다. Injectable bounded probe는 unavailable/timeout 상태 계약을 검증하지만 production hardware probe 구현을 주장하지 않는다. 실제 no-camera device/simulator의 launch degradation은 수동 검토 항목이다. Link와 notification의 공용 arbiter는 process-local route 중복만 줄이며, link delivery 자체를 notification message ledger처럼 durable하다고 주장하지 않는다.

## 검증

저장소 root에서 Node 24.19.0과 npm 11.17.0으로 실행한다.

```sh
npm ci
npm run typecheck
npm run test:stage01
npm run test:stage02
npm run test:stage03
npm run test:stage04
npm run test:stage05
npm run bundle:android
npm run bundle:ios
```

Stage 01 Jest 검사는 bootstrap 전 최신 warm URL, route reservation rollback, cross-source process-local dedupe와 clean/dirty/committed back decision을 확인한다. Stage 02 검사는 production adapter와 같은 public contracts 및 mutation policy를 사용하는 결정적 in-memory database/file harness에서 final state와 authoritative index read 실패 시 파일 비삭제를 검증한다. Stage 03 검사는 raw availability/permission mapping, startup prompt 0회, picker library permission API 0회, denied/restricted/limited/revoked/cancel, second permission-query rejection, foreground media/reconcile serialization, partial copy·invalid/oversize media, pending recovery·expiry·duplicate result, optional/late/invalid location과 unsent location removal을 final state로 확인한다. Stage 04 검사는 Node 24 SQLite에 production migration/repository SQL을 실행해 response loss, duplicate delivery, reorder, checkpoint rollback, restart/expired lease, auth stop/resume, malformed/version regression, attempt ceiling, historical permanent evidence, field merge와 v4 conflict 보존을 확인한다. Fetch timeout은 signal을 무시하는 injected fetch까지 bounded `AbortError`/durable `retry_wait`로 수렴하는지 검사한다. Stage 05는 v5→v6 보존, 두 connection의 동시 migration owner, restart/live lease/expiry/duplicate/stale/account mismatch/malformed, cold/warm serialized response, draft defer, fallback route 실패 재전달, legacy notification-disabled token gate, checkpoint-only background result와 production-default NOT-RUN을 검증한다.

Jest는 Android/iOS의 native SQLite, FileSystem, ImagePicker, Location 또는 radio stack을 직접 실행하지 않는다. Node SQLite의 transaction 결과도 mobile fsync·process lock과 동일하다는 뜻은 아니다. 따라서 이 검사는 실제 WAL/fsync, OS process kill, provider/iCloud URI, hardware camera, dialog, disk-full, TLS/proxy, platform file protection 또는 native scheduling을 보장하지 않는다. production adapter는 타입 검사, CNG와 양 플랫폼 Expo bundle로 확인하며, development build에서 다음 증거를 사람이 추가로 확인해야 한다.

1. 기록을 저장한 뒤 앱 process를 종료·재시작해 record와 `/sync` command가 함께 남는지
2. 동일 편집 화면을 두 곳에서 열어 한 write 이후 stale write가 거부되고 입력을 잃지 않는지
3. fresh install startup에서 permission dialog가 없고 system picker가 library-wide permission 없이 cancel/success하는지
4. camera deny와 `canAskAgain=false`, Settings revoke 뒤 picker/text-only 흐름이 유지되고 자동 relaunch가 없는지
5. Android `활동 유지 안 함`에서 pending result가 복구되거나 명시적 interrupted가 되며 attachment가 한 개인지
6. foreground 위치를 preview 뒤 포함/버림하고 background 복귀의 늦은 결과가 저장되지 않는지
7. v1/v4/v5 fixture가 있는 device database를 복사해 v6 migration 전후 row count, IDs, payload, conflict와 processed-intent evidence가 보존되는지
8. local fault server에서 response loss·401·conflict를 주입해 같은 command ID, restart 뒤 lease 회수와 최신 local edit 보존이 화면에서도 관측되는지
9. Android notification action 전 startup prompt가 없고, channel→permission→token 순서와 redacted 결과만 보이며 raw token/payload가 log·SQLite에 없는지. 실제 token 성공을 요구하면 소유권이 확인된 EAS project ID 증거를 별도로 제출하고, 없으면 channel·permission 뒤 `token-failed: project-id-unavailable`을 정상 경계로 기록한다.
10. cold/warm notification이 열린 draft를 덮지 않고 보류되며, draft를 떠난 뒤 retry가 현재 record/conflict 상태에 맞는 route를 한 번만 여는지
11. background task 등록 상태와 실제 sync checkpoint를 구분해 기록하고, production automatic sync가 **NOT-RUN**임을 확인한 뒤 `/sync` foreground action으로 수렴시키는지
12. iOS header/swipe와 Android hardware/predictive back에서 dirty draft가 한 번만 확인되고, clean draft와 저장 완료 replace는 확인 없이 이동하는지
13. camera 없는 device/simulator가 `limited/unknown` 사전 상태에서 launch 실패로 안전하게 저하되고 durable media operation이 retry를 막지 않는지

bundle 성공도 simulator/device 동작, signing, permission dialog, disk durability 또는 store 제출을 증명하지 않는다.

## development build

```sh
npm run run:android --workspace=@field-notes/reference
npm run run:ios --workspace=@field-notes/reference
npm run start:dev-client --workspace=@field-notes/reference
```

`run:*`은 CNG native project와 development binary를 생성한다. `android/`와 `ios/`는 source of truth가 아니며 추적하지 않는다. 이후 `start:dev-client`가 Metro를 제공한다.

수동 sync 기본 URL은 `http://127.0.0.1:3104/commands`다. 허용 host는 `127.0.0.1`, `localhost`, `::1`, Android emulator host alias `10.0.2.2`, 또는 reserved HTTPS `*.test`뿐이다. `*.test`는 device DNS와 local CA trust가 준비된 허가된 테스트 환경에서만 쓰며 그렇지 않으면 NOT-RUN이다. 일반 외부 HTTPS hostname과 production backend는 reference guard가 거부한다. physical iOS device에서 Mac의 loopback은 device 자신이므로 별도 허가된 `.test` DNS/TLS 환경 없이는 network 검증을 실행하지 않는다. URL에 credential을 넣지 않는다. reference는 optional bearer provider와 HTTP client만 제공하며 운영 backend, 계정 발급, TLS termination 또는 multi-user authorization을 만들지 않는다. 401의 `blocked-auth`는 그 worker run을 즉시 멈추고 retry timer로 풀리지 않는다. 외부 session/auth 경로가 credential을 실제로 복구한 뒤에만 `/sync`의 명시적 재개 action을 눌러야 하며, 버튼 자체는 인증하지 않는다. `Content-Length`가 있으면 1 MiB 초과를 읽기 전에 거부하지만, post-read 문자 제한은 streaming memory cap을 보장하지 않는다.

`expo-image-picker` config는 microphone을 끄고, `expo-location` config는 when-in-use만 허용하며 iOS/Android background location과 Android foreground location service를 끈다. `expo-notifications`는 stable default channel과 background remote notification 비활성, `expo-background-task`는 iOS `processing` mode와 Expo BG identifier만 구성한다. config 변경 뒤 development binary를 새로 만들어야 한다. 생성된 Android manifest에 camera, coarse/fine foreground location, `POST_NOTIFICATIONS`가 있고 exact alarm/mic/storage/background location/foreground service가 유효하지 않은지 확인한다. Dev Client/notification module의 `INTERNET`, `SYSTEM_ALERT_WINDOW`, `VIBRATE` 같은 별도 유효 선언까지 없다고 주장하지 않는다. iOS plist에는 `processing`과 `com.expo.modules.backgroundtask.processing`만 있고 remote-notification/location/audio/fetch mode가 없는지 별도로 검토한다.

`exif: false`는 adapter가 EXIF object를 요청하지 않는다는 뜻이며 원본 image bytes에서 EXIF가 제거됐음을 보장하지 않는다. 원본 filename·MIME·asset ID도 권위 있는 metadata로 취급하지 않는다. 로그와 operation failure에는 provider URI, 사진 bytes, record text 또는 정확한 좌표를 넣지 않는다. Server content validation, EXIF stripping, malware 검사, store privacy declaration과 실제 device 결과는 사람이 별도로 검토한다.
