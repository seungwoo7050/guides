# 프로젝트 목록 구현 시작점

이 디렉터리는 독립 프로젝트가 아니다. `pnpm exercise:create`가 검증 가능한 `reference/`를 `workspace/`로 복사한 뒤 이 디렉터리의 미완성 `app/`, `lib/`, `tests/`를 덮어쓴다.

학습자는 생성된 `workspace/`의 Stage source만 수정한다. 함께 복사되는 package script, 설정, 공개 test와 build·browser·smoke harness는 repository-owned 검증 계약이며 Stage 검사 전에 기준본과 같은지 확인된다. production source를 분리하고 싶다면 `workspace/app/` 또는 `workspace/lib/` 아래에 새 모듈을 추가한다.

각 `TODO(stage-XX)`는 해당 단계의 책임 경계를 표시한다.

- Stage 01: URL에서 첫 화면 복원
- Stage 02: runtime contract와 화면 state
- Stage 03: history, request lifetime과 optimistic recovery
- Stage 04: focus, responsive UI와 reduced motion
- Stage 05: production health contract

표시 문구만 지우지 말고 연결된 동작을 구현한다. 단계 검사는 source 모양이 아니라 query, state transition, HTTP response, browser behavior와 production process 결과를 확인한다.
