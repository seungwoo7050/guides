# 문제 해결

문제 해결의 첫 목표는 빠른 임시 수정이 아니라 **어느 경계에서 처음 실패했는지 재현하는 것**입니다. 전체 `pnpm verify`가 실패하면 가장 작은 `verify:*` 명령이나 exercise 명령으로 범위를 줄입니다.

## `pnpm`을 찾지 못합니다

```sh
corepack enable
pnpm --version
```

저장소가 선언한 package manager 버전과 현재 Node.js 버전을 [`시작 전 준비`](prerequisites.md)에서 확인합니다.

## 작업 공간 package를 찾지 못합니다

다음을 순서대로 확인합니다.

- 명령을 실행한 현재 디렉터리
- `pnpm-workspace.yaml`의 glob
- package의 `name`
- 소비 package의 `workspace:*` dependency
- package `exports`와 공개 진입점

저장소 루트나 해당 학습자 `work/`에서 `pnpm install`을 다시 실행합니다. 내부 `src/...` 경로를 직접 import해 임시로 우회하지 않습니다.

## 브라우저 자동 검사가 Chromium을 찾지 못합니다

실행 파일을 명시합니다.

```sh
export CHROMIUM_PATH=/usr/bin/chromium
node exercises/00-first-web-app/tests/verify.mjs exercises/00-first-web-app/work
```

CI container에서 root로 실행할 때만 환경 정책에 따라 `CHROMIUM_NO_SANDBOX=1`이 필요할 수 있습니다. 일반 desktop에서는 sandbox를 끄지 않습니다.

## 화면은 열리지만 API 요청이 실패합니다

Network 탭에서 다음을 구분합니다.

- 연결 거부: API process와 port
- 404: route·base URL
- 401·403: session·role·Origin
- 409: version·중복·업무 충돌
- 500: server log의 request ID
- JSON parse 실패: content type과 실제 response body

frontend console만 보고 server 경계를 추측하지 않습니다.

## 브라우저에서 cookie가 저장되지 않습니다

client 요청의 `credentials: "include"`, server의 정확한 CORS allowlist와 `credentials: true`를 함께 확인합니다. 발급·삭제의 cookie `name`, `path`, `domain`, `secure`, `sameSite`도 같아야 합니다. 운영의 `Secure` cookie는 HTTPS에서만 전송됩니다.

## 로그인 후에도 401이 반환됩니다

- `Set-Cookie` response가 실제로 왔는지
- 다음 요청에 `Cookie` header가 포함됐는지
- server session digest, 만료와 폐기 상태
- 사용자의 정지·삭제 상태
- reverse proxy 뒤 secure cookie 인식

을 확인합니다. browser cookie 존재만으로 server session이 유효한 것은 아닙니다.

## API는 되지만 WebSocket이 1008로 닫힙니다

upgrade 요청의 cookie, `Origin`, 계정 상태와 board membership을 확인합니다. join 전 변경, viewer의 영속 쓰기, 잘못된 schema와 stale version도 policy violation으로 거부될 수 있습니다.

## 재연결 뒤 항목이 이전 위치로 돌아갑니다

`cursor.move`나 drag preview는 임시 상태입니다. `item.move`의 `final: true`가 server에서 transaction으로 확정됐는지 확인합니다. 재연결 뒤에는 local memory를 정본으로 쓰지 않고 최신 snapshot과 sequence를 적용합니다.

## 변경이 충돌해 사라집니다

`baseVersion`과 server의 현재 version을 확인합니다. 409 또는 operation rejection에서 local draft를 버리지 말고 최신 DTO·snapshot과 함께 복구 선택을 제공합니다.

## PostgreSQL 검사가 시작되지 않습니다

자동 경로:

```sh
pnpm verify:database
```

수동 관찰:

```sh
POSTGRES_PORT=55432 docker compose -p guide-web-app-05-manual -f exercises/05-postgresql-kysely/compose.test.yml up -d --wait
export DATABASE_URL=postgres://postgres:postgres@127.0.0.1:55432/board_dev
pnpm --dir exercises/05-postgresql-kysely/work migrate
pnpm --dir exercises/05-postgresql-kysely/work test
docker compose -p guide-web-app-05-manual -f exercises/05-postgresql-kysely/compose.test.yml down -v
```

port 충돌, container health, migration 적용 여부와 `DATABASE_URL`의 DB 이름을 함께 확인합니다. 병렬 worktree에서는 Compose project name 접미사와 `POSTGRES_PORT`를 고유하게 바꾸고 `DATABASE_URL`에도 같은 port를 사용합니다. 개인 데이터가 있는 DB를 test 대상으로 사용하지 않습니다.

## Transaction 검사가 통과했지만 일부 데이터가 남습니다

같은 transaction object를 모든 repository 호출에 전달했는지 확인합니다. service가 transaction 밖의 기본 DB client를 다시 import하면 activity와 본문 쓰기가 다른 commit 경계가 됩니다.

## Next.js hydration 경고가 발생합니다

server와 browser의 첫 render에서 시각·무작위 값·storage·viewport를 직접 읽지 않았는지 확인합니다. browser 전용 값은 client component의 effect 이후에 읽고, loading placeholder가 양쪽에서 결정적으로 같아야 합니다.

## Production build만 실패합니다

개발 server와 production build는 다른 검증입니다.

```sh
pnpm --dir exercises/03-react-nextjs/work typecheck
pnpm --dir exercises/03-react-nextjs/work build
```

server/client import 경계, dynamic route의 `params`, 환경 변수 노출과 build 시점 data access를 확인합니다.

## 검사가 끝나지 않습니다

Fastify server, WebSocket, heartbeat·retry timer, event listener, PostgreSQL pool, browser와 child process를 성공·실패 양쪽에서 닫았는지 확인합니다. `finally`, Fastify `onClose`, test lifecycle hook과 idempotent close 경계를 사용합니다.

## Playwright 검사가 간헐적으로 실패합니다

- `waitForTimeout`을 관찰 가능한 상태 대기로 교체
- 검사마다 고유 사용자·board·port 사용
- role·name·label 기반 selector 사용
- animation과 network 완료가 아니라 사용자 결과를 기다림
- 실패 시 trace·screenshot·server log 보존

을 확인합니다. 재시도 횟수를 늘려 간헐 실패를 숨기지 않습니다.

## 협업 보드 단계 검사가 script 누락을 보고합니다

각 단계는 `work/package.json`의 누적 script를 요구합니다.

```json
{
  "scripts": {
    "verify:01": "...",
    "verify:02": "..."
  }
}
```

`node exercises/collaboration-board/checks/verify-work.mjs work 2`는 `verify:01`과 `verify:02`, 단계별 package script와 최소 증거 경로를 확인한 뒤 `verify:02`를 실행합니다. `--structure-only`로 통과한 결과는 실제 테스트 완료가 아닙니다.
