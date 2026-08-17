# Node.js, 패키지와 워크스페이스

웹 애플리케이션의 실행 환경은 소스 코드만으로 결정되지 않습니다. Node.js 런타임, `package.json`, lockfile, 패키지 관리자, 빌드 명령, 환경 변수가 함께 실행 계약을 구성합니다. 여러 애플리케이션과 공유 패키지를 한 저장소에 둘 때는 가져오기 경계와 명령 실행 위치를 명확하게 정해야 합니다.

## 목표

- 브라우저와 Node.js가 제공하는 런타임 API를 구분합니다.
- 의존성, 개발 의존성, 스크립트, lockfile의 역할을 설명합니다.
- ESM과 TypeScript 출력 경로의 관계를 이해합니다.
- pnpm 워크스페이스 패키지를 공개 진입점으로 연결합니다.
- 프로세스 시작과 정상 종료 절차를 설계합니다.

## 브라우저와 Node.js

두 환경은 같은 JavaScript 문법을 사용하지만 기본으로 제공하는 API가 다릅니다.

| 기능 | 브라우저 | Node.js |
|---|---|---|
| 화면·현재 주소 | `document`, `location` | 기본 제공하지 않음 |
| 파일·프로세스 | 제한적 | `node:fs`, `process` |
| HTTP 요청 | `fetch` | `fetch` |
| TCP 서버 | 제공하지 않음 | `node:net`, 프레임워크 |
| 환경 변수 | 빌드 설정에 따라 번들에 포함 | `process.env` |

서버 비밀값이 브라우저 번들에서 읽히도록 구성했다면 그 값은 이미 사용자에게 공개된 것입니다. 각 파일이 어느 환경에서 실행되는지 확인해야 합니다.

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

런타임 코드에서 가져오는 패키지는 `dependencies`에, 빌드·테스트 도구는 `devDependencies`에 둡니다. 운영 이미지에서 개발 의존성을 제외한다는 이유로 실제 런타임 의존성을 `devDependencies`에 잘못 분류해서는 안 됩니다.

스크립트는 개발자와 CI가 공유하는 명령 계약입니다. 개발 서버 실행, 타입 검사, 테스트, 빌드, 프로덕션 실행 명령을 구분합니다.

## lockfile과 재현성

패키지 매니페스트의 버전 범위는 설치를 허용할 범위를, lockfile은 실제로 선택된 의존성 그래프를 기록합니다.

```sh
pnpm install --frozen-lockfile
```

CI와 검증 환경에서는 설치 과정에서 lockfile이 예상치 않게 변경되면 실패하도록 합니다. lockfile을 삭제하고 최신 버전을 다시 설치하는 것은 기존 코드와 같은 의존성으로 검증하는 일이 아닙니다.

## ESM과 상대 경로 가져오기

`"type": "module"`인 Node.js 패키지는 ESM 규칙을 사용합니다. TypeScript의 `NodeNext` 설정에서는 컴파일 후 생성될 JavaScript 파일 경로를 기준으로 상대 경로에 `.js` 확장자를 작성할 수 있습니다.

```ts
import { parseBoard } from "./board.js";
```

TypeScript 컴파일러 설정과 Node.js의 런타임 모듈 해석 방식을 함께 확인해야 합니다. 번들러가 해석하는 경로와 Node.js가 직접 실행할 때 해석하는 경로를 혼동해서는 안 됩니다.

## 워크스페이스

```yaml
packages:
  - apps/*
  - packages/*
```

내부 패키지는 다음처럼 연결합니다.

```json
{
  "dependencies": {
    "@board/contracts": "workspace:*"
  }
}
```

패키지의 공개 진입점은 `exports`로 제한합니다.

```json
{
  "name": "@board/contracts",
  "type": "module",
  "exports": {
    ".": "./src/index.ts"
  }
}
```

소비자가 `@board/contracts/src/internal/ws.ts`처럼 패키지 내부 경로를 직접 가져오면 내부 디렉터리 구조의 변경이 저장소 전체의 호환성 문제로 이어집니다.

## 애플리케이션과 라이브러리의 부수 효과

공유 패키지를 가져오는 것만으로 서버가 시작되거나 프로세스 이벤트 리스너가 등록되면 테스트와 종료 처리가 어려워집니다.

```ts
export function buildApp(dependencies: Dependencies) {
  return fastify().register(routes, { dependencies });
}
```

실제 포트를 여는 진입점은 별도 파일에 둡니다.

```ts
const app = buildApp(createProductionDependencies());
await app.listen({ host: "0.0.0.0", port: env.PORT });
```

이렇게 분리하면 `app.inject`를 사용한 검사와 정상 종료 처리를 독립적으로 구현할 수 있습니다.

## 시작 시점 검증

환경 변수, 쓰기 가능한 디렉터리, 데이터베이스 스키마, 필수 의존성을 요청 수신 전에 확인합니다. 일부 설정이 잘못되었는데 임의의 대체값으로 실행을 계속해 첫 요청에서 500 오류가 발생하게 해서는 안 됩니다.

```ts
const env = EnvSchema.parse(process.env);
```

모든 외부 의존성이 응답할 때까지 프로세스 시작을 무기한 기다릴 필요는 없습니다. 프로세스가 살아 있는지 확인하는 liveness와 요청을 처리할 준비가 되었는지 확인하는 readiness를 구분할 수 있습니다.

## 정상 종료

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

새 요청 수락을 중단하고 진행 중인 작업, 타이머, WebSocket 연결, 데이터베이스 풀을 정리합니다. 시그널 처리기에서 종료를 시작하되 중복 시그널과 종료 제한 시간 정책도 정해야 합니다. 테스트에서도 같은 종료 경계를 호출합니다.

## 단계별 변경 기록

종합 실습의 각 단계를 작은 커밋으로 남기면 오류가 도입된 시점과 책임의 변화를 추적하기 쉽습니다. Git을 처음 사용한다면 다음 네 명령부터 익힙니다.

```sh
git status --short
git diff
git add <변경한-경로>
git commit -m "feat(notes): 메모 생성 계약 구현"
```

테스트를 통과하지 않는 모든 임시 상태를 커밋할 필요는 없습니다. 한 단계의 외부 계약을 완성했을 때 관련 문서·구현·검사를 함께 기록합니다. 비밀값, `.env`, 의존성 디렉터리, 빌드 결과물은 커밋하지 않습니다.

## 흔한 오류

- 브라우저 API와 Node.js API를 같은 파일에서 항상 사용할 수 있다고 가정합니다.
- 런타임 의존성을 `devDependencies`에 넣습니다.
- lockfile 없이도 설치 결과를 재현할 수 있다고 주장합니다.
- 워크스페이스 패키지의 내부 경로를 직접 가져옵니다.
- 모듈을 가져오는 것만으로 서버나 타이머를 시작합니다.
- 첫 요청이 들어올 때까지 환경 변수를 검증하지 않습니다.
- 종료 과정에서 서버만 닫고 데이터베이스 풀·소켓·타이머를 남깁니다.

## 연결 실습

[`실행 환경과 워크스페이스`](../../exercises/01-runtime/README.md)에서 패키지 공개 경계, 이벤트 루프, 런타임 검증을 직접 확인합니다.

## 완료 기준

- 브라우저와 Node.js의 실행 위치 및 API 차이를 설명할 수 있습니다.
- 패키지 스크립트, 의존성, lockfile의 역할을 구분합니다.
- 워크스페이스 패키지를 `workspace:*`와 `exports`로 연결합니다.
- 애플리케이션 팩터리와 실제 `listen` 진입점을 분리합니다.
- 프로세스 시작과 종료 시 관리해야 하는 자원을 설명하고 검사할 수 있습니다.

## 다음 단계

먼저 [`실행 환경과 워크스페이스`](../../exercises/01-runtime/README.md)의 `work/`에서 패키지 공개 경계·런타임 검증·이벤트 루프를 검증하고, 완료한 뒤 `reference/`와 비교합니다. 그다음 브라우저 기초를 컴포넌트 모델로 확장하려면 [`React 컴포넌트와 상태`](../02-frontend/01-react-components-state.md)로 이동합니다.
