# 05. save와 replay migration

## 목표

old save를 current schema로 안전하게 옮기고, 두 replay trace의 첫 divergence를 찾는다. save, replay와 network snapshot을 같은 serialization 문제로 취급하지 않는다.

## 입력

- [`inputs/save-v1.json`](inputs/save-v1.json)
- [`inputs/save-v2-schema.json`](inputs/save-v2-schema.json)
- [`inputs/content-aliases.json`](inputs/content-aliases.json)
- [`inputs/replay-a.json`](inputs/replay-a.json)
- [`inputs/replay-b.json`](inputs/replay-b.json)

## 제출

- [`template/migration-plan.md`](template/migration-plan.md)
- [`template/divergence-report.md`](template/divergence-report.md)

## 대표 오답

- current struct에 old JSON을 바로 매핑한다.
- unknown stable id를 조용히 삭제한다.
- migration 실패 뒤 원본 save를 덮어쓴다.
- replay 마지막 state만 비교한다.
- random seed만 같으면 determinism이 보장된다고 쓴다.

## 사람 검토 질문

1. versioned decoder와 migration step이 분리돼 있는가?
2. checksum/형식 검증이 runtime object 생성보다 먼저인가?
3. removed content의 fallback이 사용자 손실을 설명하는가?
4. first diverging tick과 관련 command/subsystem을 찾았는가?
5. determinism 범위를 build·platform·content·state field 수준으로 제한했는가?

## 완료 기준

- v1→v2 migration의 atomic commit과 rollback을 작성한다.
- newer/corrupt/missing-content save 처리표를 제출한다.
- replay의 첫 divergence와 가능한 원인을 근거로 분리한다.
