# 명령 빠른 참조

이 문서는 명령을 빠르게 다시 찾기 위한 보조 자료입니다. 학습 순서와 완료 조건은 [`docs/00-roadmap.md`](../docs/00-roadmap.md)와 각 exercise의 README가 소유합니다.

## 시작 환경 확인

```sh
node --version
corepack enable
pnpm --version
docker compose version
```

Part 01은 Docker 없이 진행할 수 있습니다. 브라우저 실행 파일을 자동으로 찾지 못하면 `CHROMIUM_PATH`를 설정합니다.

## 저장소 구조 검사

외부 서비스와 설치된 package 없이 문서 구조, 내부 링크, 코드 블록과 단계 명세를 확인합니다.

```sh
pnpm check:repository
```

동일한 검사를 Node.js로 직접 실행할 수도 있습니다.

```sh
node scripts/verify-guide-structure.mjs
node scripts/verify-links.mjs
node scripts/verify-snippets.mjs
node exercises/collaboration-board/checks/verify-stage-specs.mjs
node scripts/verify-collaboration-board.mjs
```

실습 계약과 검사기 mutation 검출까지 포함한 공식 품질 게이트는 의존성·Docker·브라우저를 준비한 뒤 `pnpm check`로 실행합니다.

## 정적 파일 서버

```sh
node scripts/serve-static.mjs exercises/00-first-web-app/reference 8080
```

브라우저에서 `http://127.0.0.1:8080`을 열고, 종료할 때 `Ctrl+C`를 누릅니다.

## 실습별 reference 검증

```sh
pnpm verify:foundations
pnpm verify:runtime
pnpm verify:react
pnpm verify:api
pnpm verify:database
pnpm verify:security
pnpm verify:realtime
pnpm verify:testing
pnpm verify:collaboration
```

`verify:database`는 빈 host port를 선택해 PostgreSQL 16 container를 시작하고, typecheck·migration·실제 DB test를 실행한 뒤 container와 volume을 정리합니다.

학습자 작업 디렉터리는 exercise별 README에 적힌 명령으로 검사합니다. 기초 browser exercise는 다음과 같습니다.

```sh
node exercises/00-first-web-app/tests/verify.mjs work
node exercises/02-browser/tests/verify.mjs work
node exercises/03-react-nextjs/tests/run.mjs work
```

## 수동 PostgreSQL 실습

자동 명령 대신 직접 관찰할 때는 기본 port `55432`를 사용합니다.

```sh
docker compose -f exercises/05-postgresql-kysely/compose.test.yml up -d --wait
export DATABASE_URL=postgres://postgres:postgres@127.0.0.1:55432/board_dev
pnpm --dir exercises/05-postgresql-kysely/reference typecheck
pnpm --dir exercises/05-postgresql-kysely/reference migrate
pnpm --dir exercises/05-postgresql-kysely/reference test
docker compose -f exercises/05-postgresql-kysely/compose.test.yml down -v
```

## Playwright browser 준비

저장소에는 서로 독립된 두 Playwright project가 있으므로 각각의 package에서 Chromium을 준비합니다.

```sh
pnpm --dir exercises/08-testing/reference exec playwright install chromium
pnpm --dir projects/collaboration-board exec playwright install chromium
```

## 전체 검증

```sh
pnpm install --frozen-lockfile
pnpm verify
```

전체 명령은 구조 검사, 모든 exercise reference, 실제 PostgreSQL, 두 Playwright 경로와 완성 협업 보드의 typecheck·test·production build·E2E를 순서대로 실행합니다. 한 단계가 실패하면 해당 `verify:*` 명령을 따로 실행해 경계를 좁힙니다.


## 협업 보드 단계 검증

```sh
cd exercises/collaboration-board
rm -rf work
cp -R skeleton work
cd work
corepack enable
pnpm install
cd ..
node checks/verify-work.mjs work 1
```

각 단계를 구현하면서 `work/package.json`에 누적 `verify:02`~`verify:08`을 추가하고 같은 명령의 마지막 번호를 바꿉니다. 단계 8은 다음과 같습니다.

```sh
node checks/verify-work.mjs work 8
```

`--structure-only`는 검사기 유지보수용이며 테스트 실행을 건너뛰므로 학습 완료 판정에 사용하지 않습니다.

## 선택적 patch walkthrough

누적 patch는 직접 구현을 대신하지 않는 비교 자료입니다. patch는 변경 불가 `walkthrough-base/`에 적용되며 학습자 `skeleton/`을 수정하지 않습니다.

```sh
pnpm check:walkthrough
```
