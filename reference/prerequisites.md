# 시작 전 준비

이 문서는 도구를 한꺼번에 설치하라는 목록이 아니라 **현재 Part에 필요한 실행 환경**을 확인하는 참조입니다. 전체 학습 순서와 선행지식은 [`docs/00-roadmap.md`](../docs/00-roadmap.md)가 소유합니다.

## Part 01: 웹 기초

필수:

```sh
node --version
corepack --version
```

기준은 Node.js 24.19.0 이상 25 미만이며 `.nvmrc`는 재현 가능한 시작 버전인 24.19.0을 가리킵니다. package 실습을 시작할 때 저장소가 선언한 pnpm을 활성화합니다.

```sh
corepack enable
pnpm --version
```

첫 브라우저 실습은 Chrome 또는 Chromium을 실제로 실행합니다. 자동 탐색에 실패하면 실행 파일 경로를 지정합니다.

```sh
export CHROMIUM_PATH=/usr/bin/chromium
```

운영체제에 따라 `/usr/bin/chromium`, `/usr/bin/google-chrome`, macOS 애플리케이션 경로가 다를 수 있습니다.

## Part 02~03: React·Next.js와 API

저장소 루트에서 잠금 파일 그대로 의존성을 설치합니다.

```sh
pnpm install --frozen-lockfile
```

학습자 `work/`처럼 아직 lockfile이 없는 새 프로젝트에서는 해당 디렉터리에서 `pnpm install`을 한 번 실행해 lockfile을 만들고 함께 관리합니다.

Git은 capstone의 단계별 변경을 기록할 때 필요합니다.

```sh
git --version
git init
git add .
git commit -m 'chore: 시작 상태'
```

Git 원격 저장소나 복잡한 branch 전략은 필수 선행지식이 아닙니다.

## Part 04 이후: PostgreSQL과 통합 검사

DB 실습은 Docker Compose를 기본 경로로 제공합니다.

```sh
docker compose version
```

`psql`은 직접 SQL을 관찰할 때 유용하지만 자동 실습의 필수 조건은 아닙니다.

```sh
psql --version
```

Docker를 사용할 수 없는 환경에서는 별도 PostgreSQL 16 instance를 준비하고 exercise README의 `DATABASE_URL` 형식에 맞춥니다. 학습용 DB를 개인·운영 DB와 공유하지 않습니다.

## Playwright 브라우저

Playwright package와 브라우저 binary는 별개입니다. 해당 프로젝트 안에서 Chromium을 설치합니다.

```sh
pnpm --dir exercises/08-testing/reference exec playwright install chromium
pnpm --dir projects/collaboration-board exec playwright install chromium
```

첫 브라우저 실습의 dependency 없는 CDP 검사와 Playwright 검사는 서로 다른 경로입니다.

## 알아둘 운영체제 모델

- **process**: 실행 중인 프로그램과 그 자원 수명의 경계
- **port**: 한 host의 여러 network server를 구분하는 번호
- **environment variable**: process 시작 시 주입하는 설정
- **current directory**: 상대 경로와 package 명령이 해석되는 기준
- **localhost**: 명령을 실행한 현재 network namespace 자신
- **exit status**: 명령의 성공과 실패를 호출자에게 전달하는 숫자

포트가 이미 사용 중이라면 점유 process를 찾습니다.

```sh
lsof -iTCP:4000 -sTCP:LISTEN
```

Linux에서는 `ss -ltnp`도 사용할 수 있습니다.

## 설치 실패를 다루는 순서

1. 현재 디렉터리와 실행한 명령을 기록합니다.
2. Node.js·pnpm·Docker 버전을 확인합니다.
3. 오류의 첫 원인과 마지막 요약을 함께 읽습니다.
4. 회사 proxy·인증서·방화벽 제한 여부를 확인합니다.
5. lockfile을 지우기 전에 변경 이유를 확인합니다.
6. 임의로 최신 버전을 설치해 기준 환경을 바꾸지 않습니다.

환경 문제를 애플리케이션 결함처럼 수정하지 않고, 재현 명령과 실패 경계를 먼저 분리합니다.
