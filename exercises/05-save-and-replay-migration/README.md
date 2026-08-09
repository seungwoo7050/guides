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

`template/`은 의도적으로 미완성인 starter다. 자신의 작업 디렉터리에 복사해 작성하고 원본 fixture나 template을 검증 과정에서 덮어쓰지 않는다. 완료 뒤 다음 예시 해설과 비교한다.

- [`reference/migration-plan.md`](reference/migration-plan.md)
- [`reference/divergence-report.md`](reference/divergence-report.md)

예시 해설은 문구를 강제하지 않지만 field 변환, alias resolution과 checkpoint/command 비교처럼 fixture가 결정하는 사실은 동일해야 한다.

## 검증 근거

자동 검사 또는 fixture에서 직접 비교 가능한 증거:

- v1/v2 schema version은 각각 `1/2`이며 v2 required payload field 다섯 개를 모두 다룬다.
- `bestTimeSeconds=54.21`은 `best_time_ms=54210`으로 변환한다.
- 두 old skin id는 `cosmetic.player.default`, `cosmetic.player.founder-blue`로 resolve된다.
- replay의 last equal checkpoint는 tick `5`, first unequal checkpoint는 tick `10`이다.
- 첫 command 차이는 sequence `3`, tick `8`, move Y 값 `1000` 대 `900`이다.
- reference는 newer/corrupt/unknown-content/storage-failure에서 원본을 보존하고 unknown id를 조용히 삭제하지 않는다.

사람이 검토할 rubric:

- versioned decoder, pure migration과 v2 invariant validation이 분리되는가?
- default를 적용한 field와 사용자 값을 보존한 field가 구분되는가?
- atomic replace 이전의 모든 실패에서 current/previous generation을 읽을 수 있는가?
- tick 10 checkpoint를 first diverging tick이라고 과장하지 않고 tick 8..10 추가 probe를 제시하는가?
- fixture에 없는 checksum/storage/cross-platform 보장을 사실처럼 주장하지 않는가?

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
- 예시 해설의 변환값과 divergence window를 비교하고 자동 확인 불가능한 보장을 별도로 표시한다.
