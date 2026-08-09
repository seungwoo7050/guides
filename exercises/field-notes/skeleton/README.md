# Field Notes skeleton

Expo SDK 57에서 실행·typecheck·native bundle이 가능한 Stage 01 시작 상태다. 다음 항목은 의도적으로 미완성이다.

- `src/navigation/stage01.ts`의 URL parsing, record ID 제한, intent identity, dirty-back decision
- startup link/restoration을 repository readiness와 target existence 뒤에 적용하는 coordinator
- edit form의 validation, focus, draft/back 처리와 in-memory save
- 유효하지 않은 ID와 유효하지만 없는 record를 구분하는 화면

repository·SQLite·camera·location·sync·background·notification을 미리 구현하지 않는다. 공개 검사는 구현 모양이 아니라 이 행동 공백을 거부한다.

저장소 root에서:

```sh
npm ci
npm run typecheck
npm run start --workspace=@field-notes/skeleton
npm run bundle:android:skeleton
npm run bundle:ios:skeleton
```

`npm run test:stage01:skeleton`은 시작 상태에서 실패해야 한다. 테스트를 건너뛰거나 expected 값을 바꾸지 말고 TODO 행동을 구현해 통과시킨다.

development build는 CNG로 생성한다. 생성되는 `android/`, `ios/`는 source가 아니며 Git에서 제외된다.

```sh
npm run run:android --workspace=@field-notes/skeleton
npm run run:ios --workspace=@field-notes/skeleton
npm run start:dev-client --workspace=@field-notes/skeleton
```

