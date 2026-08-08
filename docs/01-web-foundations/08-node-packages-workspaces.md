# Node.js, package와 workspace

웹 애플리케이션은 코드만으로 실행되지 않습니다. Node.js runtime, `package.json`, lockfile, package manager, build 명령과 환경 변수가 함께 실행 계약을 이룹니다. 여러 앱과 공유 package를 한 저장소에 둘 때는 import 경계와 명령의 위치를 명확히 해야 합니다.

## 목표

- browser와 Node.js runtime API를 구분합니다.
- dependency, devDependency, script와 lockfile의 역할을 설명합니다.
- ESM과 TypeScript 출력 경로를 이해합니다.
- pnpm workspace package를 공개 진입점으로 연결합니다.
- process startup과 graceful shutdown을 설계합니다.

## browser와 Node.js

같은 JavaScript 문법을 쓰지만 제공 API가 다릅니다.

| 기능 | browser | Node.js |
|---|---|---|
| 화면·현재 주소 | `document`, `location` | 기본 제공 안 함 |
| file·process | 제한됨 | `node:fs`, `process` |
| HTTP 요청 | `fetch` | `fetch` |
| TCP server | 제공 안 함 | `node:net`, framework |
| 환경 변수 | build 설정에 따라 노출 | `process.env` |

server secret을 browser bundle에서 읽을 수 있게 만들면 이미 사용자에게 공개된 것입니다. 실행 위치를 file 단위로 확인합니다.

## `package.json`

```json
{
  "name": "@board/api",
  "private": true,
  "type": "module",
  "scripts": {
    "dev": "tsx watch src/server.ts",
    "typecheck": "tsc --noEmit",
    "test": "vitest run",
    "build": "tsc -p tsconfig.build.json"
  },
  "dependencies": {
    "fastify": "^5.0.0"
  },
  "devDependencies": {
    "typescript": "^5.0.0"
  }
}
```

runtime code가 import하는 package는 `dependencies`, build·test 도구는 `devDependencies`에 둡니다. 단순히 운영 image에서 devDependency를 제거한다는 이유만으로 runtime import를 잘못 분류하지 않습니다.

script는 팀과 CI가 공유하는 명령 계약입니다. 개발, typecheck, test, build와 start를 분리합니다.

## lockfile과 재현성

manifest의 range는 허용 범위를, lockfile은 실제 선택된 dependency graph를 기록합니다.

```sh
pnpm install --frozen-lockfile
```

CI와 검증에서는 lockfile이 예상치 않게 바뀌면 실패하도록 합니다. lockfile을 삭제하고 “최신”을 다시 설치하는 것은 동일한 코드 검증이 아닙니다.

## ESM과 상대 import

`"type": "module"`인 Node.js package는 ESM 규칙을 사용합니다. TypeScript `NodeNext` 설정에서는 출력될 JavaScript 경로를 기준으로 상대 import에 `.js` 확장자를 쓰는 경우가 있습니다.

```ts
import { parseBoard } from "./board.js";
```

compiler 설정과 runtime module 해석을 함께 봅니다. bundler가 해결해 주는 import와 Node가 직접 실행하는 import를 혼동하지 않습니다.

## workspace

```yaml
packages:
  - apps/*
  - packages/*
```

내부 package는 다음처럼 연결합니다.

```json
{
  "dependencies": {
    "@board/contracts": "workspace:*"
  }
}
```

package의 공개 entry를 `exports`로 제한합니다.

```json
{
  "name": "@board/contracts",
  "type": "module",
  "exports": {
    ".": "./src/index.ts"
  }
}
```

소비자가 `@board/contracts/src/internal/ws.ts`처럼 내부 경로를 직접 import하면 directory 변경이 저장소 전체의 호환성 문제가 됩니다.

## application과 library의 부수 효과

공유 package를 import했는데 server가 시작되거나 process event listener가 생기면 test와 종료가 어려워집니다.

```ts
export function buildApp(dependencies: Dependencies) {
  return fastify().register(routes, { dependencies });
}
```

실제 port를 여는 entry는 별도로 둡니다.

```ts
const app = buildApp(createProductionDependencies());
await app.listen({ host: "0.0.0.0", port: env.PORT });
```

이 분리는 `app.inject` 검사와 graceful shutdown을 가능하게 합니다.

## startup validation

환경 변수, writable directory, database schema와 필수 dependency를 요청 수신 전에 확인합니다. 일부 값이 잘못됐는데 fallback으로 계속 실행해 늦은 500을 만들지 않습니다.

```ts
const env = EnvSchema.parse(process.env);
```

모든 dependency가 “살아 있음”을 startup에서 무한 대기할 필요는 없습니다. process가 시작할 수 있는 조건과 요청을 받을 준비가 된 조건을 liveness·readiness로 구분할 수 있습니다.

## graceful shutdown

```ts
let closing = false;

async function shutdown(signal: string) {
  if (closing) return;
  closing = true;
  app.log.info({ signal }, "shutdown started");
  await app.close();
  await db.destroy();
}
```

새 요청 수락을 멈추고 진행 중인 작업, timer, WebSocket과 pool을 정리합니다. signal handler에서 종료를 시작하되 중복 signal과 timeout 정책도 정합니다. 검사에서도 같은 close 경계를 호출합니다.

## 단계별 변경 기록

Capstone의 각 단계를 작은 commit으로 남기면 실패 원인과 책임 이동을 비교하기 쉽습니다. Git을 처음 사용한다면 다음 네 명령만 먼저 익힙니다.

```sh
git status --short
git diff
git add <변경한-경로>
git commit -m "feat(notes): 메모 생성 계약 구현"
```

검사를 통과하지 않은 임시 상태를 무조건 commit할 필요는 없습니다. 한 단계의 외부 계약이 완성됐을 때 관련 문서·구현·검사를 함께 기록합니다. 비밀값, `.env`, 의존성 디렉터리와 빌드 결과는 추가하지 않습니다.

## 실패 조건

- browser와 Node API를 같은 file에서 무조건 사용할 수 있다고 가정합니다.
- runtime dependency를 devDependency로 숨깁니다.
- lockfile 없이 설치 결과를 재현 가능하다고 주장합니다.
- workspace package 내부 경로를 직접 import합니다.
- import 자체가 server·timer를 시작합니다.
- 환경 변수를 첫 요청이 올 때까지 검증하지 않습니다.
- 종료에서 server만 닫고 pool·socket·timer를 남깁니다.

## 연결 실습

[`실행 환경과 작업 공간`](../../exercises/01-runtime/README.md)에서 package 공개 경계, event loop와 runtime validation을 직접 확인합니다.

## 완료 기준

- browser·Node 실행 위치와 API 차이를 설명할 수 있습니다.
- package script, dependency와 lockfile 역할을 구분합니다.
- workspace package를 `workspace:*`와 `exports`로 연결합니다.
- app factory와 실제 listen entry를 분리합니다.
- startup과 shutdown의 자원 계약을 설명하고 검사할 수 있습니다.

## 다음 단계

브라우저 기초를 component model로 확장하려면 [`React 컴포넌트와 상태`](../02-frontend/01-react-components-state.md)로 이동합니다.
