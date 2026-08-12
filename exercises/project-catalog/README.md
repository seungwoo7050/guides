# 프로젝트 목록 실습

검색 가능한 프로젝트 목록을 하나의 코드베이스에서 다섯 단계로 완성한다. URL에서 첫 화면을 복원하고, 외부 응답을 검증하며, 늦은 요청과 낙관적 변경 충돌을 수렴시킨다. 마지막에는 실제 production server를 browser와 standalone smoke test로 검증한다.

## 학습 계약

이 실습은 `skeleton/`의 미완성 파일을 `reference/` 프로젝트 위에 덮어쓴 `workspace/`에서 진행한다.

- `skeleton/`은 각 단계의 실제 미완성 상태다.
- `reference/`는 검사 체계 자체를 검증하는 완성 구현이다.
- `workspace/`는 학습자가 수정하는 유일한 작업 공간이다.
- 각 Stage 검사는 현재 단계와 이전 단계의 계약을 함께 확인한다.
- 구현 표시를 지우는 것만으로는 행동 검사를 통과할 수 없다.

생성기는 package·설정·공개 test·build/browser/smoke harness를 `reference/`에서 제공하고, 다음 일곱 source를 `skeleton/`의 미완성 파일로 교체한다.

```text
app/page.tsx
app/project-catalog.tsx
app/styles.css
app/api/health/route.ts
lib/catalog-contract.ts
lib/catalog-model.ts
lib/request-coordinator.ts
```

위 source는 분리하거나 새 `app/`·`lib/` 모듈로 확장해도 된다. 반면 제공된 package script, 설정, 공개 test와 검증 harness는 검사 신뢰 경계이므로 수정하지 않는다. Stage 검사는 실행 전에 이 보호 파일들이 기준본과 같은지 확인한다.

`reference/`는 처음부터 읽지 않는다. 요구사항, compiler와 test의 실패 출력을 먼저 사용하고, 해당 Stage를 통과한 뒤 아래의 Stage별 범위만 비교한다.

## 준비

저장소 루트에서 실행한다.

```sh
nvm use
./prepare.sh
pnpm exercise:create
```

이미 `workspace/`가 있으면 생성기는 종료 코드 2로 중단한다. 기존 작업을 보존하거나 직접 삭제한 뒤 다시 실행한다.

## 단계

| Stage | 요구사항 | 검증 계층 |
| --- | --- | --- |
| [01](specs/01-project-onboarding.md) | URL query를 server 첫 화면에 복원 | typecheck, unit |
| [02](specs/02-ui-state-architecture.md) | runtime contract와 discriminated state | typecheck, unit |
| [03](specs/03-data-effects-concurrency.md) | history, abort, generation, optimistic recovery | unit, build, browser |
| [04](specs/04-testing-accessibility-performance.md) | keyboard, focus, responsive, reduced motion, budget | build, browser |
| [05](specs/05-production-runtime-contract.md) | health·release 구현, 제공된 test boundary·standalone smoke 분석·실행 | unit, build, browser, process |

순서대로 실행한다.

```sh
pnpm exercise:verify:01
pnpm exercise:verify:02
pnpm exercise:verify:03
pnpm exercise:verify:04
pnpm exercise:verify:05
```

전체 구현을 한 번에 검증한다.

```sh
pnpm exercise:verify
```

필요한 계층만 다시 실행할 수도 있다.

```sh
pnpm exercise:check
pnpm exercise:build
pnpm exercise:test:e2e
pnpm exercise:smoke
```

## 권장 구현 순서

아래 번호는 Git history나 파일의 위아래 순서가 아니라, 완성된 `reference/`를 다시 구성할 때 권장하는 학습용 구현 순서다. 번호 scope는 `exercises/project-catalog/reference/` 전체 하나이며 파일마다 다시 시작하지 않는다. Stage는 학습 checkpoint이고, 이 표의 번호는 파일 사이를 오가는 construction dependency이므로 서로 같은 번호 체계가 아니다.

| 순서 | 파일·symbol | 먼저 고정할 책임 |
| ---: | --- | --- |
| 1 | `lib/catalog-contract.ts` · `ContractError`와 parser | URL query와 `unknown` 응답을 신뢰 경계에서 canonical data로 바꾼다. |
| 2 | `lib/catalog-model.ts` · `CatalogState` | 화면 상태의 단일 owner와 마지막으로 확인된 결과 보존 invariant를 정한다. |
| 3 | `app/page.tsx` · `Page` | 같은 query에서 server 첫 결과와 직렬화 가능한 client props를 만든다. |
| 3-1 | `app/project-catalog.tsx` · `ProjectCatalog` | draft, 확인된 결과, 알림과 요청 수명의 owner를 분리한다. |
| 4 | `lib/request-coordinator.ts` · `createRequestCoordinator` | transport abort와 monotonic generation으로 오래된 작업을 무효화한다. |
| 4-1 | `app/project-catalog.tsx` · `runSearch` | history 기록과 탐색을 분리하고 최신의 검증된 응답만 commit한다. |
| 4-2 | `app/project-catalog.tsx` · `rename` | optimistic 값, 이전 server 값과 local draft를 성공·실패·충돌별로 수렴시킨다. |
| 5 | `app/project-catalog.tsx` · `ProjectEditor` | 조건부 editor의 저장 상태, draft와 focus lifecycle을 소유한다. |
| 5-1 | `app/styles.css` | 작은 viewport, 긴 값, focus 표시와 reduced motion을 하나의 layout 계약으로 고정한다. |
| 6 | `app/api/health/route.ts` · `GET` | release만 노출하는 exact health 응답과 no-store 경계를 제공한다. |
| 6-1 | `app/api/health/route.ts` · `pnpm typecheck` / `next typegen` | route가 존재한 뒤 framework route type을 생성하고 `tsc` 검사로 연결한다. 생성물은 직접 수정하지 않는다. |

이 저장소에는 검증된 application generator나 package/framework 초기화 기록이 없으므로 Implementation 0은 없다. `nvm use`, 의존성 설치와 `exercise:create`는 repository 준비 또는 learner workspace materialization이며 application construction 번호에 포함하지 않는다.

`project-types.ts`, in-memory project store, API adapter, layout, reset route, package/TypeScript 설정, public test, Playwright와 smoke script는 제공된 baseline 또는 검증 infrastructure다. `performance-budget.json`은 구현 답안이 아니라 Stage 04의 machine-readable 검증 정책이다. 이 파일들은 위 numbered source annotation의 대상이 아니다. `next typegen`은 package 설정을 변경하는 bootstrap이 아니라 route 구현 뒤 실행하는 중간 code generation이므로 6-1에 둔다.

## 구현 표시

미완성 위치에는 다음 형식의 표시가 있다.

```text
TODO(stage-01)
TODO(stage-02)
...
TODO(stage-05)
```

현재 Stage 이하의 표시는 구현 뒤 제거한다. 이후 Stage 표시는 남아 있어도 현재 검사가 통과할 수 있다. 표시 문구만 지우지 말고 연결된 동작을 구현한다.

## 완료 증거

Stage를 통과한 뒤 다음을 짧게 기록한다.

```text
사용자 결과:
막으려는 실패:
선택한 상태·실행 경계:
실행한 검증:
남은 범위:
```

## Reference 비교

Stage를 통과한 뒤에만 아래 범위의 reference를 읽는다. 여러 Stage가 공유하는 파일은 symbol 단위로 범위를 제한하여 다음 Stage의 완성 구현을 미리 노출하지 않는다.

| Stage | 통과 뒤 비교할 범위 |
| --- | --- |
| 01 | `reference/app/page.tsx`의 `Page` |
| 02 | `reference/lib/catalog-contract.ts`, `reference/lib/catalog-model.ts` |
| 03 | `reference/lib/request-coordinator.ts` 전체, `reference/app/project-catalog.tsx`의 `ProjectCatalog` state owner·`runSearch`·`rename`; `ProjectEditor`는 읽지 않음 |
| 04 | `reference/app/project-catalog.tsx`의 `ProjectEditor`, `reference/app/styles.css` |
| 05 | `reference/app/api/health/route.ts`의 `GET` |

비교할 질문:

- 같은 상태에 서로 다른 정본을 만들지 않았는가?
- stale result를 취소와 generation 중 어느 경계에서 막았는가?
- conflict에서 최신 server value와 local draft를 함께 보존했는가?
- focus transition이 사용자 흐름과 맞는가?
- production build와 smoke가 실제 배포 산출물을 검사하는가?

reference와 모양이 달라도 계약과 검증을 만족하면 유효한 해법이다.
