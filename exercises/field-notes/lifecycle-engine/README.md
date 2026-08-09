# Field Notes lifecycle engine

Stage 05의 background opportunity와 notification response를 platform API에서 분리한 순수 TypeScript reference core다. 이 package는 scheduler가 실행된다고 가정하지 않고, 실행 기회가 왔을 때 Stage 04의 같은 bounded worker를 호출하는 의미만 소유한다.

```text
manual / app-active / background opportunity
→ LifecycleSyncCoordinator
→ BoundedWorkerPort.run(...)
→ durable claim / lease / checkpoint를 소유한 sync-engine
```

`BoundedWorkerPort`는 `@field-notes/sync-engine`의 `BoundedSyncWorker`와 구조적으로 호환된다. lifecycle core는 command payload, transport result 또는 checkpoint를 다시 해석하지 않는다. trigger는 관측 문맥이고 성공 의미는 worker와 durable repository의 checkpoint가 정본이다.

## 포함된 계약

### sync opportunity

- `manual`, `app-active`, `background`가 같은 worker port를 호출한다.
- background task가 한 번도 실행되지 않아도 pending command는 그대로 남고 다음 `app-active`에서 처리할 수 있다.
- deadline 또는 parent abort는 worker의 `AbortSignal`로 전달된다. 이미 만료된 opportunity는 worker에 들어가지 않는다.
- worker는 signal을 command claim 전에 다시 확인해야 한다. request 결과를 모르는 중단은 `success`가 아니라 durable retry/UNKNOWN 상태로 checkpoint해야 한다.
- 한 process 안의 concurrent trigger는 한 실행에 coalesce한다. 이는 최적화일 뿐 정확성 경계가 아니다. headless/foreground process가 분리되거나 process가 재생성되면 production repository의 atomic claim과 lease가 중복 시도를 막는다.
- background leader에 foreground trigger가 coalesce해도 leader의 deadline을 늘리지 않는다. queue가 남으면 다음 foreground opportunity가 다시 같은 worker를 호출한다.

### notification intent

허용 envelope는 업무 snapshot 없이 schema와 opaque identity만 가진다.

```ts
type NotificationEnvelope = {
  schemaVersion: 1;
  messageId: string;
  accountId: string;
  intent:
    | { kind: "record-conflict"; recordId: string }
    | { kind: "record-updated"; recordId: string }
    | { kind: "sync-blocked" };
};
```

parser는 unknown type, extra business field, 잘못된 ID와 schema를 거부한다. coordinator는 다음 순서를 보존한다.

```text
runtime parse
→ repository.ready()
→ current account 재조회
→ response identity durable lease claim
→ current record/conflict/sync 상태 재조회
→ current-state navigation intent 또는 safe rejection
→ caller가 navigation을 적용한 뒤 acknowledge
```

`prepare()`의 `prepared` 결과는 아직 처리 완료가 아니다. caller가 cold/warm navigation 정책과 dirty-draft 보호를 적용한 뒤 `acknowledge()`해야 한다. 그 전에 process가 종료되면 live claim 동안 duplicate는 `in-progress`이고, lease expiry 뒤 다시 준비할 수 있다. 완료 claim, stale/deleted 결과는 durable하게 terminal 처리돼 같은 message가 업무 효과를 반복하지 않는다.

account mismatch/deleted는 protected route를 만들지 않는다. 이미 해결된 conflict는 stale conflict route를 거부하고 현재 record detail만 safe fallback으로 제안한다. deleted/missing record는 목록 fallback만 제안한다. notification title/body나 과거 record snapshot은 판정에 사용하지 않는다.

### Android registration

`AndroidNotificationRegistrationCoordinator`는 다음 호출 순서를 강제한다.

```text
channel ensure
→ permission current/request
→ granted 또는 not-required일 때만 token
```

`not-determined`는 명시적 사용자 문맥에서만 request한다. `denied`와 `restricted`에서는 token을 요청하지 않는다. runtime permission이 필요 없는 OS의 `not-required`는 `granted`와 다른 결과로 유지한다. token-ready도 backend mapping, provider acceptance, OS delivery 또는 사용자 tap을 뜻하지 않는다.

## production Expo adapter 경계

이 package에는 Expo import가 없다. production app은 다음 adapter를 별도 의미 단위로 제공한다.

- module scope의 TaskManager/background-task definition과 app 설정 이후 registration
- AppState `active`, 수동 action과 headless callback을 `LifecycleSyncCoordinator`로 전달하는 adapter
- wall-clock deadline을 abort로 바꾸는 timer adapter
- SQLite의 sync-engine claim/lease/checkpoint와 processed-notification claim adapter
- `expo-notifications` Android channel, permission과 project/device token adapter
- DB migration/session 복원 이후 notification `prepare`, router 적용 이후 `acknowledge`하는 startup adapter

background callback은 React component, toast 또는 router를 직접 변경하지 않는다. worker 결과를 durable repository에 남기고 foreground UI가 repository를 다시 읽는다. task registration 상태나 요청 interval을 “동기화 완료”로 표시하지 않는다.

## deterministic 검증

```sh
npm run typecheck
npm test
```

testkit은 수동 clock/deadline, lease repository, bounded worker, repository readiness gate, durable intent claim과 Android call log를 제공한다. 검사는 다음을 포함한다.

- trigger별 같은 worker/final command state
- background 미실행 후 app-active 수렴
- deadline 중단의 UNKNOWN retry와 새 command 미시작
- in-process coalesce, cross-coordinator live lease, process-death lease expiry
- malformed/stale/duplicate/deleted account·record notification
- cold-start readiness와 incomplete intent claim recovery
- channel→permission→token 순서와 denied/not-required 차이

## 자동 검사가 보장하지 않는 범위

Node test는 다음을 보장하지 않는다.

- Android/iOS scheduler가 callback을 주거나 요청 interval을 지키는지
- OS expiration callback, force-stop, recent 제거, reboot와 vendor battery policy
- 실제 SQLite fsync·transaction·process 간 lease
- Android channel 설정과 POST_NOTIFICATIONS dialog의 실제 순서/문구
- APNs/FCM/Expo provider token, backend installation mapping, token rotation 또는 delivery
- notification cold/warm tap의 실제 native response와 router/dirty draft UI
- background network, credential 복원과 headless dependency initialization

이 항목은 SDK 57 development build와 Android/iOS 실제 기기에서 별도 evidence로 확인한다. 실행하지 않은 platform은 `미검사`이며 이 package의 green test가 branch의 stable 상태를 자동 선언하지 않는다.
