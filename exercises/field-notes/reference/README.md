# Field Notes Stage 01 reference

Expo SDK 57와 Expo Router로 만든 실행 가능한 비교 기준이다. 다음을 포함한다.

- list/new/detail/edit/sync/settings route와 safe-area·keyboard-aware form
- framework-independent URL/record ID normalization
- repository readiness와 record existence 뒤에 결정하는 startup link/restoration
- malformed/too-long/unknown link, valid-but-missing target, duplicate intent 처리
- in-memory optimistic revision과 process 종료 뒤 fixture reset
- validation error·focus 유지, accessible role/label/state, unsaved draft back guard
- lifecycle을 관찰하되 background callback에 저장을 맡기지 않는 경계

SQLite, durable draft, media/location, remote sync, background work와 notification은 명시적인 후속 adapter다. reference의 `local-only` 표시는 server 적용을 보장하지 않는다.

저장소 root에서 자동 검증한다.

```sh
npm ci
npm run typecheck
npm run test:stage01
npm run bundle:android
npm run bundle:ios
```

실행 및 development build:

```sh
npm run start --workspace=@field-notes/reference
npm run run:android --workspace=@field-notes/reference
npm run run:ios --workspace=@field-notes/reference
npm run start:dev-client --workspace=@field-notes/reference
```

`run:*`은 CNG native project와 development binary를 만든다. 이후 `start:dev-client`가 Metro를 제공한다. JS bundle 성공은 simulator/device 동작, permission dialog, signing 또는 store 제출을 증명하지 않는다.

