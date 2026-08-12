# React와 Next.js 프런트엔드 설계

이 저장소는 웹 개발 입문 과정이 아니라, 작은 React 애플리케이션을 이미 만들어 본 개발자가 **기존 Next.js 코드베이스에 합류해 운영 가능한 기능을 완성하는 과정**을 다룹니다.

HTML·CSS·JavaScript·TypeScript·React의 첫 사용법과 간단한 App Router 애플리케이션 작성은 [`guide-web-applications`](https://github.com/woopinbell/guide-web-applications)가 담당합니다. 이 가이드는 그 위에서 다음 판단을 훈련합니다.

- 저장소의 실제 실행·빌드·배포 경계를 어떻게 복원할까요?
- URL, 브라우저 상태, 서버 데이터와 편집 초안의 소유자를 어떻게 나눌까요?
- Server Component와 Client Component 경계를 어디에 둘까요?
- 요청 취소, 응답 순서 역전과 낙관적 변경 충돌을 어떻게 수렴시킬까요?
- 접근성, 운영 빌드와 성능 예산을 어떤 자동 검사로 고정할까요?
- 프런트엔드 산출물이 배포 인프라에 제공해야 할 계약은 무엇일까요?

호스트 준비, Docker 이미지 배포, DNS·TLS, 중앙 관측 시스템, 백업과 롤백 실행은 `guide-web-infrastructure`의 영역입니다. 여기서는 **프런트엔드 애플리케이션이 검증 가능한 운영 산출물을 만드는 지점까지** 다룹니다.

## 학습 종료 능력

가이드를 마치면 다음을 독립적으로 수행할 수 있어야 합니다.

1. 처음 보는 React/Next.js 저장소의 런타임, 라우트, 서버·클라이언트 경계와 검증 명령을 복원합니다.
2. 사용자 행동 하나를 URL·서버 데이터·오류·접근성 검증까지 이어지는 수직 기능으로 구현합니다.
3. 모순 없는 화면 상태와 명시적인 외부 데이터 계약을 설계합니다.
4. 요청 취소와 세대 검사를 함께 사용해 오래된 응답을 차단합니다.
5. 낙관적 변경의 성공·일반 실패·버전 충돌을 구분해 복구합니다.
6. 실제 브라우저에서 키보드, 초점, 반응형 배치와 성능 예산을 검사합니다.
7. 고정 설치, 운영 빌드, 운영 서버와 smoke test로 배포 가능한 산출물을 검증합니다.

## 학습 순서

첫 학습에서는 한 문서를 읽고 연결된 Stage를 구현·검증한 뒤, 그 Stage에 해당하는 `reference/` 범위만 비교하고 다음 행으로 이동합니다. 별도 관찰 예제는 없습니다. 짧은 코드는 문서 안에서 개념만 설명하며, 완성 구현을 미리 보여 주는 example로 사용하지 않습니다.

| 순서 | 문서 | 관찰 예제 | 직접 수행 | 수정 위치 | 검증 | 완료 뒤 비교·다음 |
| ---: | --- | --- | --- | --- | --- | --- |
| 0 | [학습 경로와 선행조건](docs/00-roadmap-and-prerequisites.md) | — | `./prepare.sh`로 고정 의존성과 browser runtime을 준비한 뒤 `pnpm exercise:create`로 시작점을 만듭니다. | — | `pnpm check:repository` | `pnpm exercise:verify:01`이 미완성 상태를 거절함을 확인하고 [Stage 01 문서](docs/01-project-onboarding.md)로 이동합니다. |
| 1 | [프로젝트 합류와 첫 기능](docs/01-project-onboarding.md) | — | [Stage 01 명세](exercises/project-catalog/specs/01-project-onboarding.md): URL query에서 첫 화면을 복원합니다. | `exercises/project-catalog/workspace/app/page.tsx` | `pnpm exercise:verify:01` | 통과 뒤 `exercises/project-catalog/reference/app/page.tsx`의 `Page`를 비교하고 Stage 02로 이동합니다. |
| 2 | [UI와 상태 구조](docs/02-ui-and-state-architecture.md) | — | [Stage 02 명세](exercises/project-catalog/specs/02-ui-state-architecture.md): 외부 계약과 모순 없는 화면 상태를 만듭니다. | `exercises/project-catalog/workspace/lib/catalog-contract.ts`, `exercises/project-catalog/workspace/lib/catalog-model.ts` | `pnpm exercise:verify:02` | 통과 뒤 같은 `exercises/project-catalog/reference/lib/` 파일을 비교하고 Stage 03으로 이동합니다. |
| 3 | [Next.js 데이터·효과·동시성](docs/03-nextjs-data-effects-and-concurrency.md) | — | [Stage 03 명세](exercises/project-catalog/specs/03-data-effects-concurrency.md): history, 취소, generation과 낙관적 복구를 구현합니다. | `exercises/project-catalog/workspace/lib/request-coordinator.ts`, `exercises/project-catalog/workspace/app/project-catalog.tsx` | `pnpm exercise:verify:03` | 통과 뒤 `exercises/project-catalog/reference/lib/request-coordinator.ts`와 `project-catalog.tsx`의 `runSearch`·`rename`만 비교합니다. `ProjectEditor`는 Stage 04 통과 뒤 보고 다음 행으로 이동합니다. |
| 4 | [테스트·접근성·성능](docs/04-testing-accessibility-and-performance.md) | — | [Stage 04 명세](exercises/project-catalog/specs/04-testing-accessibility-performance.md): 초점 수명, 반응형 배치와 성능 예산을 만족합니다. | `exercises/project-catalog/workspace/app/project-catalog.tsx`, `exercises/project-catalog/workspace/app/styles.css` | `pnpm exercise:verify:04` | 통과 뒤 `exercises/project-catalog/reference/app/project-catalog.tsx`의 `ProjectEditor`와 `exercises/project-catalog/reference/app/styles.css`를 비교하고 Stage 05로 이동합니다. |
| 5 | [운영 런타임 계약](docs/05-production-runtime-contract.md) | — | [Stage 05 명세](exercises/project-catalog/specs/05-production-runtime-contract.md): production health 계약을 구현하고 제공된 smoke harness를 분석·실행합니다. | `exercises/project-catalog/workspace/app/api/health/route.ts` | `pnpm exercise:verify:05` | 통과 뒤 `exercises/project-catalog/reference/app/api/health/route.ts`의 `GET`을 비교하고 전체 검증으로 이동합니다. |
| 90 | [실무 점검표](docs/90-practical-checklist.md) | — | Stage 01–05의 완료 증거와 배포 경계를 다시 점검합니다. | — | `pnpm exercise:verify` | 이 저장소의 필수 경로는 끝납니다. 실제 배포 실행은 `guide-web-infrastructure`로 이어집니다. |

문서 번호는 학습 의존 순서입니다. [실무 점검표](docs/90-practical-checklist.md)는 별도 Stage가 아니라 전 과정에서 다시 사용하는 자료입니다. Stage 02는 접근 가능한 상태 구조를 만들고, Stage 04는 실제 브라우저에서 초점과 시간에 따른 동작까지 검증합니다.

## 프로젝트 목록 실습

실습은 검색과 편집이 가능한 프로젝트 목록 하나를 단계적으로 완성합니다. 각 단계는 같은 코드베이스를 확장하며, 앞 단계의 계약을 이후 단계에서도 계속 검사합니다.
별도 Capstone 디렉터리는 없으며, Stage 01–05를 누적한 이 프로젝트와 `pnpm exercise:verify`가 필수 학습 경로의 종료점입니다.

`pnpm exercise:create`는 완성 프로젝트의 package·설정·공개 검사 기반을 복사한 뒤 `skeleton/`의 미완성 `app/`, `lib/`, `tests/`를 덮어써 `exercises/project-catalog/workspace/`를 만듭니다. 학습자가 수정하는 위치는 이 `workspace/`뿐입니다. Stage별 source는 자유롭게 설계할 수 있지만, 복사된 package script, 공개 test와 build·browser·smoke harness는 repository-owned 검증 계약이므로 변경할 수 없습니다.

```text
Stage 01  URL에서 첫 화면 복원
Stage 02  런타임 계약과 모순 없는 화면 상태
Stage 03  요청 취소·순서 역전·낙관적 충돌 복구
Stage 04  키보드·초점·작은 화면·성능 예산
Stage 05  운영 빌드·health contract·smoke test
```

```sh
nvm use
./prepare.sh
pnpm exercise:create
```

`nvm`을 사용하지 않는 환경에서는 `.nvmrc` 계약과 같은 Node.js 24.19.0 이상 25 미만을 준비합니다.

```sh
pnpm exercise:verify:01
pnpm exercise:verify:02
pnpm exercise:verify:03
pnpm exercise:verify:04
pnpm exercise:verify:05
```

전체 구현을 마친 뒤에는 다음 명령을 사용합니다.

```sh
pnpm exercise:verify
```

`reference/`는 검사 체계 자체를 검증하는 완성 구현입니다. 먼저 요구사항과 실패 출력을 사용하고, 해당 Stage를 통과한 뒤 [Stage별 비교 범위](exercises/project-catalog/README.md#reference-비교)만 읽습니다. 여러 Stage가 같은 파일을 사용하므로 아직 구현하지 않은 다음 Stage의 symbol은 미리 비교하지 않습니다.

## 저장소 자체 검증

```sh
pnpm check
pnpm build
pnpm test:e2e
pnpm verify
```

표준 전체 검증은 `./prepare.sh` 다음 `./verify.sh` 순서로 실행합니다. 전체 로그는 성공·실패와 관계없이 저장소 밖의 임시 디렉터리에 남고 마지막에 `VERIFY LOG` 경로가 출력됩니다. 다른 위치가 필요하면 저장소 밖의 절대 경로를 지정합니다.

```sh
VERIFY_LOG=/tmp/guide-web-front.log ./verify.sh
```

- `check`는 reference의 형·단위 검사와 skeleton의 의도된 미완성 상태를 확인합니다.
- `build`는 운영 빌드를 만듭니다.
- `test:e2e`는 빌드한 운영 서버를 실제 브라우저로 검사합니다.
- `verify`는 위 검사와 운영 smoke test를 모두 실행합니다.

## 버전과 원리

실습은 `package.json`과 잠금 파일에 기록된 버전을 기준으로 재현합니다. 문서의 중심은 상태 소유권, 신뢰 경계, 요청 수명과 검증 계층처럼 버전이 바뀌어도 유지되는 원리입니다. `searchParams`, 캐시 API, 빌드 출력처럼 버전에 따라 달라지는 항목은 현재 Next.js 공식 문서와 실제 운영 빌드로 다시 확인합니다.
