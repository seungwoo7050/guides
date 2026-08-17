# Runtime Workspace

`pnpm` workspace 안에서 TypeScript library package와 실행 application을 분리한 작은 runtime 관찰 프로젝트입니다. Package export, `workspace:*` dependency, 외부 입력 검증과 Node.js event-loop ordering을 한 번에 확인할 수 있습니다.

## Features

- `apps/*`, `packages/*` workspace boundary
- `@runtime-workspace/math` public export
- immutable input을 받는 `sum()`
- `unknown`에서 시작하는 TCP port validation
- application이 library 내부 경로가 아닌 package export만 사용
- `sync → microtask → task` 실행 순서 관찰

## Structure

```text
runtime-workspace/
├── apps/demo/
├── packages/math/
├── tests/
├── package.json
├── pnpm-workspace.yaml
└── tsconfig.base.json
```

## Install and run

```sh
corepack enable
pnpm install
pnpm typecheck
pnpm demo
```

정상 실행은 다음 순서를 출력합니다.

```text
sum 6
port 4000
sync
microtask
task
```

`PORT`가 정수가 아니거나 `1..65535` 범위를 벗어나면 process는 오류로 종료합니다.

## Tests

Node.js 22 이상에서는 dependency install 없이 core domain test를 실행할 수 있습니다.

```sh
npm test
```

전체 workspace typecheck와 실행 검증은 `pnpm install` 뒤 수행합니다.

## Major design decisions

- Library는 side effect가 없는 순수 연산과 validation만 공개합니다.
- Application은 `@runtime-workspace/math` export를 사용하므로 library 내부 directory가 public API가 되지 않습니다.
- Port는 환경 변수 문자열을 바로 사용하지 않고 `unknown` input boundary에서 검증합니다.
- Event-loop 예시는 callback 등록 순서와 실제 출력 순서를 같은 entry point에 둡니다.

## Implementation Order

| Order | Responsibility | Primary anchor |
| ----: | --- | --- |
| 1 | Workspace package ownership | `pnpm-workspace.yaml` |
| 2 | Pure shared operation | `packages/math/src/index.ts` |
| 3 | External port validation | `packages/math/src/index.ts` |
| 4 | Package-export consumption | `apps/demo/src/index.ts` |
| 5 | Event-loop lifecycle observation | `apps/demo/src/index.ts` |

## Scope and limitations

이 프로젝트는 package publishing, bundled output, worker thread, stream, process signal과 network server를 구현하지 않습니다. Runtime boundary와 workspace ownership을 좁게 보여 주는 실행 artifact입니다.
