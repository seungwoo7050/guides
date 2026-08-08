# 실행 환경과 작업 공간

브라우저와 Node.js의 실행 위치, 마이크로태스크와 태스크의 순서, `unknown` 입력 검증, pnpm 작업 공간의 공개 패키지 경계를 확인합니다.

## 선행 문서

- [`JavaScript 기초`](../../docs/01-web-foundations/04-javascript-foundations.md)
- [`비동기 작업과 fetch`](../../docs/01-web-foundations/06-async-fetch-errors.md)
- [`Node.js와 패키지 작업 공간`](../../docs/01-web-foundations/08-node-packages-workspaces.md)

## 작업 공간 만들기

```sh
cd exercises/01-runtime
rm -rf work
cp -R skeleton work
cd work
pnpm install
```

`reference/`를 먼저 실행하지 않습니다. `work/`의 TODO를 직접 완성하고, 출력과 오류를 예상한 뒤 검사합니다.

## 구현할 계약

1. 동기 코드, `queueMicrotask`, `setTimeout`의 출력 순서를 실행 전에 적습니다.
2. 포트 입력은 `unknown`에서 시작해 `1..65535` 범위의 정수로 좁힙니다.
3. 작업 공간 패키지는 `workspace:*`로 연결합니다.
4. 패키지 내부 파일을 직접 가져오지 않고 `exports`에 선언된 공개 진입점만 사용합니다.
5. demo 패키지는 성공과 실패를 관찰할 수 있는 명령을 제공합니다.

## 검증

```sh
pnpm typecheck
pnpm demo
```

다음 결함을 한 번씩 만들어 실패 위치를 확인합니다.

- `exports`를 제거합니다.
- 작업 공간 의존성을 일반 버전 문자열로 바꿉니다.
- `parsePort`에서 `as number`만 사용합니다.
- 실패한 Promise를 `await`하거나 반환하지 않습니다.

## 완료 기준

- 출력 순서를 event loop의 task·microtask 규칙으로 설명할 수 있습니다.
- 잘못된 포트가 TypeScript 형 단언을 통과해도 실행 시점에는 거부됩니다.
- 패키지 소비자가 내부 폴더 배치에 의존하지 않습니다.
- `work/`가 형 검사를 통과하고 정상·실패 입력의 결과가 의도와 일치합니다.

완료한 뒤에만 `diff -ru work reference`로 설계 차이를 비교합니다.
