# 협업 보드 시작점

이 디렉터리는 [`../README.md`](../README.md)와 `../specs/`의 단계 계약을 직접 구현하기 위한 최소 workspace입니다. 빈 폴더가 아니라 다음 경계를 이미 제공합니다.

- `apps/web`: 의미 있는 첫 Next.js page와 production build 진입점
- `apps/api`: import와 listen을 분리한 Fastify app factory
- `packages/contracts`: browser와 server가 공유할 공개 전송 타입의 시작점
- `packages/db`: 수명 종료가 가능한 repository port
- 환경 변수 검증, `/health` 계약과 멱등 종료를 확인하는 첫 API test

첫 단계는 다음 명령으로 확인합니다.

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

이 시작점은 최종 구조를 대신하지 않습니다. 단계 02부터 route·contract·repository·migration·security·realtime 경계를 직접 추가하고, 각 단계마다 `verify:0N` 명령과 자동 검사를 누적합니다.

```text
한 단계의 명세 읽기
→ 구현과 검사를 함께 작성
→ node checks/verify-work.mjs work N
→ 자신의 commit 기록
→ 필요한 경우에만 완성 프로젝트와 patch 비교
```

`../patches/`를 순서대로 적용해 완성하는 방식은 기본 과제가 아닙니다. patch는 구현을 마친 뒤 책임 이동과 파일 변화 순서를 비교하는 선택적 walkthrough 자료입니다.
