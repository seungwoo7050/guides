# Field Notes deterministic fault server

Stage 04~05의 sync 실패를 재현하는 **허가된 local test double**이다. production backend, 인증 서비스, multi-user database나 공개 API가 아니다. 기본 HTTP entry는 `127.0.0.1`에만 bind하며 test control endpoint를 제공하므로 외부 network에 노출하거나 실제 credential·사용자 data를 보내지 않는다.

## 보장하는 test contract

- stable `commandId`와 attempted command fingerprint를 memoize한다.
- 같은 ID·같은 command retry는 같은 업무 결과를 반환하고 remote effect를 한 번만 적용한다.
- 같은 ID에 operation, record, base version, local revision, payload 또는 creation identity가 달라지면 `command-identity-reuse`로 거부한다.
- current remote version과 `baseVersion`이 다르면 current snapshot을 포함한 conflict를 memoize한다.
- response loss, malformed success와 version regression은 실제 apply/memoize 뒤 **전달 결과만** 잃거나 왜곡할 수 있다.
- delay는 `ManualClock`을 test가 전진시키기 전까지 풀리지 않으므로 wall-clock sleep 없이 response reorder를 만든다.
- 401은 pre-apply transient failure이며, permanent validation은 apply 없이 memoized terminal result가 된다.

결정적 test 통과는 실제 HTTP radio/TLS/proxy, production authorization/policy, database transaction, provider outage나 운영 backend를 보장하지 않는다.

## Node와 실행

Node 24의 built-in TypeScript type stripping을 사용한다.

```sh
fnm exec --using=24.19.0 npm --prefix exercises/field-notes/fault-server run typecheck
fnm exec --using=24.19.0 npm --prefix exercises/field-notes/fault-server test
```

package를 직접 실행하면 loopback port `3104`를 사용한다. `FIELD_NOTES_FAULT_PORT`로 다른 local port를 선택할 수 있다.

```sh
fnm exec --using=24.19.0 npm --prefix exercises/field-notes/fault-server start
```

## app 실행 환경별 endpoint

HTTP server는 의도적으로 host loopback에만 bind한다. 실행 환경에서 `127.0.0.1`이 가리키는 owner가 다르므로 reference app의 `EXPO_PUBLIC_FIELD_NOTES_SYNC_URL`을 다음처럼 선택한다.

| app 실행 환경 | app에 설정할 command endpoint | 범위와 준비 |
|---|---|---|
| Node/in-process test | HTTP endpoint 없음 | 같은 core를 memory에서 직접 호출한다. |
| iOS simulator | `http://127.0.0.1:3104/commands` | simulator가 host network를 공유하는 개발 evidence다. 실제 iPhone evidence가 아니다. |
| Android emulator | `http://10.0.2.2:3104/commands` | Android emulator의 host-loopback alias다. 다른 emulator 제품은 자체 정본을 확인한다. |
| Android physical development device | `http://127.0.0.1:3104/commands` | 아래 `adb reverse`가 성공한 현재 USB device에서만 사용한다. |
| iOS physical device | local DNS가 연결한 `https://<name>.test/commands` 또는 `미검사` | reference transport는 reserved `.test` HTTPS만 허용한다. device DNS, local CA trust, endpoint owner·격리 근거가 모두 필요하며 이 저장소는 bridge나 certificate를 제공하지 않는다. |

Android physical device에서는 server를 loopback bind 그대로 둔 채 USB reverse를 명시적으로 열고, 실습 뒤 제거한다.

```sh
adb reverse tcp:3104 tcp:3104
adb reverse --list
# device evidence 수행
adb reverse --remove tcp:3104
```

예를 들어 Android emulator용 Metro를 시작할 때는 development/test 환경에서만 다음 값을 전달한다.

```sh
EXPO_PUBLIC_FIELD_NOTES_SYNC_URL=http://10.0.2.2:3104/commands \
  npm run start:dev-client --workspace=@field-notes/reference
```

local cleartext HTTP가 platform policy에 거부되면 production 전체의 transport policy를 낮추지 않는다. 허가된 reserved `.test` HTTPS endpoint를 사용하거나 해당 device 항목을 `미검사`로 남긴다. `.test` 이름만 붙였다고 안전한 것이 아니며 device가 쓰는 DNS, local CA trust, test data·endpoint owner와 정리 근거가 필요하다. reference transport는 일반 public/production hostname을 의도적으로 거부한다. iOS physical device를 위해 server를 `0.0.0.0`에 bind하거나 unauthenticated `/__test/*` control endpoint를 LAN·tunnel·공개 host에 노출하지 않는다. 외부 test endpoint가 필요하면 command API와 test control plane을 분리하고 owner·인증·격리·정리 근거를 제출한다.

## in-process API

자동 검사는 HTTP를 거치지 않고 같은 core를 직접 사용할 수 있다.

```ts
import {
  DeterministicFaultServer,
  ManualClock,
  type RecordCommand,
} from "./src/index.ts";

const clock = new ManualClock(0);
const server = new DeterministicFaultServer(clock);

server.inject({ kind: "delay", milliseconds: 50 }, { commandId: "cmd-a" });
const pendingA = server.execute(commandA satisfies RecordCommand);

await server.execute(commandB satisfies RecordCommand); // B가 먼저 완료
clock.advanceBy(50);                                    // 실제 sleep 없음
await pendingA;
```

`snapshot()`은 record, memoized command, apply count, pending fault와 normalized history를 반환한다. `getRecord()`와 `getApplyCount()`도 공개 관측용이다.

## fault 주입

`inject(fault, { commandId? })`는 FIFO fault를 추가한다. `commandId`를 주면 해당 command만 소비한다.

| fault | 적용 시점과 결과 |
|---|---|
| `{ kind: "delay", milliseconds }` | 처리 전에 manual clock까지 대기; 다른 command가 먼저 완료 가능 |
| `{ kind: "response-loss" }` | 업무 result apply/memoize 뒤 `ResponseLostError`; retry는 memoized result |
| `{ kind: "unauthorized" }` | apply 전에 401, memo 없음; 다음 retry에서 session 회복 재현 |
| `{ kind: "malformed-success", body? }` | success apply/memoize 뒤 status 200의 invalid body 한 번 전달 |
| `{ kind: "version-regression", by? }` | success apply/memoize 뒤 실제보다 낮은 version 한 번 전달 |
| `{ kind: "permanent-validation", reason }` | apply 없이 422 terminal result memoize; 수정은 새 command ID 필요 |

한 request는 matching fault 하나를 소비한다. 복합 시나리오는 command별 request 순서와 여러 retry로 구성하며 `snapshot().history`에 실제 소비·apply·delivery 순서를 남긴다.

## HTTP entry

| Method | Path | 역할 |
|---|---|---|
| `GET` | `/health` | local test double 식별 |
| `POST` | `/commands` | `RecordCommand` 실행 |
| `GET` | `/__test/state` | normalized snapshot |
| `POST` | `/__test/faults` | `{ commandId?, fault }` enqueue |
| `POST` | `/__test/clock/advance` | `{ milliseconds }`로 manual clock 전진 |
| `POST` | `/__test/reset` | pending sleeper가 없을 때 state reset |

response-loss fault는 apply 뒤 HTTP connection을 의도적으로 끊는다. client는 이를 확정 실패가 아니라 UNKNOWN으로 취급하고 같은 attempted command를 retry해야 한다.

## command 의미

wire command는 `@field-notes/shared`의 `RecordCommand`와 구조적으로 호환된다.

```text
commandId, recordId, operation,
baseVersion, localRevision,
payload 또는 delete의 null,
createdAt
```

`upsert`의 빈 title, 너무 긴 title/notes는 기본 permanent validation result다. schema 자체가 malformed면 400이고 memoize하지 않는다. delete는 payload가 반드시 `null`이어야 한다.

## 안전·정리·비보장 범위

- loopback 외 bind를 지원하지 않는다.
- test control endpoint에 인증이 없으므로 공유 환경에 배포하지 않는다.
- memory-only라 process 종료 뒤 data가 남지 않는다.
- production credential, push token, 실제 사용자 record를 사용하지 않는다.
- 각 test는 새 instance를 만들거나 sleeper가 없는 상태에서 `/__test/reset`을 호출한다.
- conflict/version/idempotency의 client 계약을 검증하는 도구이지 production storage, backup, rate limit, observability나 security 구현이 아니다.
