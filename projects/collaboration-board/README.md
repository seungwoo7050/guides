# 실시간 협업 보드

Fastify와 Next.js로 구성한 실시간 보드의 완성 구현입니다. HTTP 요청은 Zod로 검사하고, PostgreSQL 변경은 Kysely 트랜잭션으로 저장하며, 접속 중인 사용자는 WebSocket으로 같은 보드 상태를 공유합니다. 학습용 골격 없이 이 디렉터리만으로 설치, 실행과 검증을 진행할 수 있습니다.

## 실행

Node.js 22와 pnpm 10이 필요합니다. 의존성 버전은 프로젝트 안의 잠금 파일로 고정되어 있습니다.

```sh
pnpm install --frozen-lockfile
pnpm typecheck
pnpm test
pnpm build
```

개발 서버에서 PostgreSQL 경로를 사용하려면 다음 순서로 실행합니다.

```sh
docker compose -f compose.dev.yml up -d
cp .env.example .env
pnpm --filter @board/db migrate
pnpm dev
```

HTTP API는 로그인하지 않은 요청과 권한이 없는 요청을 각각 `401`, `403`으로 구분합니다. 변경 요청은 현재 버전을 함께 보내며, 다른 사용자가 먼저 수정했다면 `409`와 최신 상태를 반환합니다. WebSocket 연결도 같은 세션과 역할을 확인하고, 잘못된 메시지는 정책 위반 코드로 닫습니다.

브라우저 검사는 PostgreSQL과 API·웹 서버를 실행한 상태에서 수행합니다.

```sh
pnpm test:e2e
```

단위 검사는 세션 무효화, 신뢰하지 않는 Origin, 두 클라이언트 사이의 전파, 오래된 버전의 재동기화를 포함합니다. 브라우저 검사는 보드 화면의 주요 흐름을 실제 포인터와 키보드 입력으로 확인합니다.
