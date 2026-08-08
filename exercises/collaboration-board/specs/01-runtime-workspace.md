# 01. Runtime과 작업 공간

## 목표

브라우저, Node.js와 build 단계의 실행 위치를 구분하고, 웹·API·공유 계약·DB package를 하나의 pnpm workspace로 연결합니다.

## 구현할 변경

- `apps/web`, `apps/api`, `packages/contracts`, `packages/db`의 package 경계를 만듭니다.
- package는 `exports`로 공개 진입점을 제한하고 내부 import를 금지합니다.
- 환경 변수는 startup에서 검증하며 client bundle에 비밀값을 넣지 않습니다.
- API는 SIGTERM에서 새 요청을 멈추고 서버·timer·pool을 닫을 수 있는 종료 경계를 가집니다.

## 실패 조건

- browser file이 `process.env`의 server secret을 직접 읽습니다.
- 한 package가 다른 package의 `src/internal.ts`를 직접 import합니다.
- import만으로 server가 시작되거나 전역 timer가 생깁니다.
- 검사 뒤 열린 handle 때문에 process가 종료되지 않습니다.

## 검증

- workspace package import가 공개 entry에서 해석됩니다.
- 잘못된 환경 변수로 startup이 즉시 실패합니다.
- 종료 함수를 두 번 호출해도 안전합니다.

검증 진입점은 다음과 같습니다. `work/package.json`의 `verify:01`는 이 단계까지의 형 검사·테스트·build를 누적 실행해야 합니다.

```sh
node checks/verify-work.mjs work 1
```

## 완료 계약

각 파일의 실행 위치와 각 package의 공개 책임을 한 문장으로 설명할 수 있고, 다음 단계가 아직 존재하지 않는 내부 파일을 참조하지 않습니다.
