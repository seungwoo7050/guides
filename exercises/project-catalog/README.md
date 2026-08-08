# 프로젝트 목록 실습

검색 가능한 프로젝트 목록을 하나의 코드베이스에서 다섯 단계로 완성한다. URL에서 첫 화면을 복원하고, 외부 응답을 검증하며, 늦은 요청과 낙관적 변경 충돌을 수렴시킨다. 마지막에는 실제 production server를 browser와 standalone smoke test로 검증한다.

## 학습 계약

이 실습은 `skeleton/`의 미완성 파일을 `reference/` 프로젝트 위에 덮어쓴 `workspace/`에서 진행한다.

- `skeleton/`은 각 단계의 실제 미완성 상태다.
- `reference/`는 검사 체계 자체를 검증하는 완성 구현이다.
- `workspace/`는 학습자가 수정하는 유일한 작업 공간이다.
- 각 Stage 검사는 현재 단계와 이전 단계의 계약을 함께 확인한다.
- 구현 표시를 지우는 것만으로는 행동 검사를 통과할 수 없다.

`reference/`는 처음부터 읽지 않는다. 요구사항, compiler와 test의 실패 출력을 먼저 사용하고, 해당 Stage를 통과한 뒤 설계 차이를 비교한다.

## 준비

저장소 루트에서 실행한다.

```sh
nvm use
corepack enable
pnpm install --frozen-lockfile
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
| [05](specs/05-production-runtime-contract.md) | health, release, test boundary, standalone smoke | unit, build, browser, process |

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

Stage를 통과한 뒤에만 같은 파일의 reference를 읽는다.

비교할 질문:

- 같은 상태에 서로 다른 정본을 만들지 않았는가?
- stale result를 취소와 generation 중 어느 경계에서 막았는가?
- conflict에서 최신 server value와 local draft를 함께 보존했는가?
- focus transition이 사용자 흐름과 맞는가?
- production build와 smoke가 실제 배포 산출물을 검사하는가?

reference와 모양이 달라도 계약과 검증을 만족하면 유효한 해법이다.
