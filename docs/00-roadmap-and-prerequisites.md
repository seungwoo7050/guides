# 학습 경로와 선행조건

이 가이드는 React와 Next.js의 첫 사용법을 설명하는 입문서가 아니다. 작은 React 애플리케이션을 만들어 본 개발자가 기존 코드베이스에 합류해 **운영 가능한 수직 기능을 설계·구현·검증하는 과정**을 다룬다.

HTML·CSS·JavaScript·TypeScript·React와 App Router의 기초가 아직 익숙하지 않다면 먼저 [`guide-web-applications`](https://github.com/woopinbell/guide-web-applications)를 완료한다. 이 저장소는 그 과정의 내용을 반복하지 않고, 실무에서 경계가 흐려지기 쉬운 상태 소유권, 서버·클라이언트 실행 위치, 비동기 요청 수명, 접근성, 운영 산출물에 집중한다.

## 대상 독자

다음 작업을 한 번 이상 해 본 개발자를 대상으로 한다.

- React 컴포넌트에 props를 전달하고 로컬 state를 갱신했다.
- 폼 제출과 목록 렌더링을 구현했다.
- `fetch`로 JSON API를 호출하고 loading·error 상태를 표시했다.
- TypeScript로 객체와 함수의 타입을 작성했다.
- App Router의 `page.tsx`, `layout.tsx`, Route Handler를 사용했다.
- Git 브랜치에서 기능을 수정하고 패키지 관리자의 잠금 파일을 사용했다.

아래 항목이 낯설다면 선행 과정에서 보완한다.

- 의미에 맞는 HTML 요소와 연결된 `label`
- CSS 기본 흐름, Flexbox와 Grid
- Promise, `async`·`await`, module
- TypeScript의 union, `unknown`, narrowing
- HTTP method, status, header, JSON body
- React의 props, state, event, effect와 cleanup
- Node.js, `package.json`, script와 lockfile

## 종료 능력

가이드를 완료한 독자는 다음을 독립적으로 수행할 수 있어야 한다.

1. 처음 보는 저장소에서 Node.js·패키지 관리자·환경 변수·라우트·빌드·테스트 경계를 복원한다.
2. 사용자 행동 하나를 URL, 서버 데이터, 오류, 접근성 검사까지 잇는 수직 기능으로 정의한다.
3. UI state, URL state, server state, 편집 draft와 파생 값을 서로 다른 소유자에게 배치한다.
4. 외부 데이터를 `unknown`으로 받아 신뢰 경계에서 검증하고 화면 모델로 변환한다.
5. 요청 취소와 generation 검사를 함께 사용해 늦은 응답이 최신 화면을 덮지 못하게 한다.
6. 낙관적 변경의 성공, 일반 실패, 버전 충돌을 구분해 복구한다.
7. 실제 브라우저에서 키보드, 초점, 뒤로 가기, 작은 화면, 확대와 성능 예산을 검사한다.
8. 고정 설치, 운영 빌드, 운영 서버, health contract와 smoke test로 배포 산출물을 증명한다.

## 이 가이드가 소유하는 범위

이 저장소가 주로 가르치는 내용은 다음과 같다.

- 기존 React/Next.js 프로젝트 합류와 첫 수직 기능
- UI 상태 모델과 컴포넌트 책임 배치
- Server Component와 Client Component 경계
- URL과 browser history를 정본으로 사용하는 화면
- 외부 응답의 runtime validation
- 요청 취소, 응답 순서 역전과 stale result 차단
- 낙관적 갱신, draft 보존과 conflict recovery
- 접근 가능한 이름, 키보드 흐름과 초점 복구
- production build, 브라우저 E2E와 성능 예산
- 프런트엔드 애플리케이션의 health·release·smoke 계약

## 의도적으로 다루지 않는 범위

다음 영역은 이 저장소의 종료점 밖에 있다.

- HTML·CSS·JavaScript·React의 첫 문법 학습
- 일반적인 백엔드 API와 데이터베이스 설계
- 사용자 인증 서버와 세션 저장소 구현
- Docker 호스트, DNS, TLS, registry와 배포 자동화
- 로그·metric 저장소와 alerting infrastructure
- React reconciler, browser engine와 bundler 내부구조
- 특정 상태 관리·캐시 라이브러리의 전체 API
- 대규모 design system 운영과 조직 프로세스

호스트·컨테이너·DNS·TLS·중앙 관측·백업·rollback 실행은 `guide-web-infrastructure`가 담당한다. 이 가이드에서는 인프라가 배포하고 감시할 수 있도록 애플리케이션 산출물과 검증 계약을 제공하는 지점까지만 다룬다.

## 버전 기준

실습은 저장소의 `package.json`, `pnpm-lock.yaml`, `.nvmrc`가 고정한 버전으로 실행한다.

```text
Node.js       22.16.x
pnpm          10.32.1
Next.js       15.5.21
React         19.2.8
TypeScript    5.9.3
Playwright    1.61.1
Vitest        3.2.7
```

버전 번호 자체를 외우지 않는다. 대신 다음 두 종류를 분리한다.

### 오래 유지되는 원리

- 하나의 상태에는 하나의 정본이 있어야 한다.
- 외부 입력은 신뢰 경계에서 검증해야 한다.
- 취소 요청이 이미 시작된 작업 전체를 되돌리지는 않는다.
- 서버가 확정하는 값과 사용자가 편집 중인 draft는 다르다.
- 접근성은 markup뿐 아니라 시간에 따른 초점과 알림 계약이다.
- 개발 서버가 아니라 배포할 산출물을 검사해야 한다.

### 버전에 따라 다시 확인할 구현

- `searchParams`와 route API의 구체적인 타입
- Server Action과 cache API의 동작
- production output과 build analysis 형식
- Next.js가 생성하는 type 정보와 명령
- React의 실험적 또는 새 API

버전 종속 항목은 현재 프로젝트의 공식 문서와 실제 build 결과를 근거로 결정한다.

## 읽기 순서

| 순서 | 문서 | 완료 판단 |
| ---: | --- | --- |
| 1 | [프로젝트 합류와 첫 기능](01-project-onboarding.md) | 실행 경로를 복원하고 URL에서 첫 화면을 구성한다. |
| 2 | [UI와 상태 구조](02-ui-and-state-architecture.md) | 모순 없는 상태와 runtime contract를 만든다. |
| 3 | [Next.js 데이터·효과·동시성](03-nextjs-data-effects-and-concurrency.md) | 늦은 응답과 충돌에서도 화면을 수렴시킨다. |
| 4 | [테스트·접근성·성능](04-testing-accessibility-and-performance.md) | 실제 브라우저에서 주요 위험을 재현한다. |
| 5 | [운영 런타임 계약](05-production-runtime-contract.md) | 운영 서버와 health·smoke 계약을 검증한다. |

[실무 점검표](90-practical-checklist.md)는 첫 학습용 본문이 아니라 구현·리뷰·장애 분석 때 다시 사용하는 압축된 기준이다.

## 실습과 문서 대응

모든 문서는 하나의 [프로젝트 목록 실습](../exercises/project-catalog/README.md)에 연결된다.

| Stage | 구현할 경계 | 자동 검증 |
| --- | --- | --- |
| 01 | URL query → Server Component → 첫 화면 | query parsing, initial render, typecheck |
| 02 | runtime validation과 discriminated UI state | malformed input, state transition, typecheck |
| 03 | history, cancellation, generation, optimistic recovery | unit test, build, deterministic browser test |
| 04 | keyboard, focus, responsive layout, reduced motion, budget | production browser test |
| 05 | health, release, secret boundary, production smoke | build, browser, standalone smoke |

`reference/`를 먼저 읽지 않는다. 요구사항과 실패 출력으로 구현하고 해당 Stage를 통과한 뒤 설계 차이를 비교한다.

## 학습 방식

각 단계에서 같은 순서를 사용한다.

```text
사용자 결과를 한 문장으로 적기
→ 입력·출력·실패·시간 계약 적기
→ 자동 검사로 현재 실패 확인
→ 가장 작은 수직 변경 구현
→ 대표 실패를 재현
→ production 조건에서 검증
→ reference와 설계 차이 비교
```

검사가 실패하면 정답 모양을 추측하지 않는다. 먼저 실패한 계약이 순수 변환, 컴포넌트 행동, HTTP 경계, 브라우저, 운영 런타임 중 어디에 속하는지 분류한다.

## 시작

저장소 루트에서 실행한다.

```sh
nvm use
corepack enable
pnpm install --frozen-lockfile
pnpm exercise:create
pnpm exercise:verify:01
```

`workspace/`는 생성 후 자동으로 덮어쓰지 않는다. 진행 중인 구현을 보존한 뒤에만 직접 삭제하거나 다시 만든다.
