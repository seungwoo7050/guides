# 스키마와 제약 설계

협업 프로젝트 도메인의 업무 규칙을 애플리케이션의 `if`가 아니라 키와 제약으로 내린다.

## 보장해야 할 규칙

- 이메일은 대소문자를 무시하고 유일하다.
- 같은 사용자는 한 프로젝트에 한 번만 가입한다.
- membership 역할은 `OWNER`, `EDITOR`, `VIEWER` 중 하나다.
- task assignee는 같은 프로젝트의 member여야 한다.
- priority는 1~5다.
- `DONE` task만 `completed_at`을 가지며, `DONE`이면 반드시 값이 있어야 한다.
- 외래 키가 존재하지 않는 사용자·프로젝트·membership을 참조하지 못한다.

문서: [`docs/01-relational-semantics-and-design/03-er-normalization-and-constraints.md`](../../../docs/01-relational-semantics-and-design/03-er-normalization-and-constraints.md)

## 시작

```bash
./scripts/new-workspace.sh exercises/01-relational-semantics-and-design/02-schema-and-constraints
```

직접 수정할 파일은 `workspace/schema.sql`이다. 생성 직후 검사가 지정된 제약 결함에서 실패하는지 먼저 확인한다.

## 목표

협업 도메인의 소속·역할·상태 규칙을 복합 키와 선언적 제약으로 데이터베이스 경계에 둔다.

## 완료 기준

- 대소문자만 다른 이메일과 같은 프로젝트의 중복 membership insert가 거부된다.
- 다른 프로젝트 member를 task assignee로 지정하는 교차 경계 참조가 거부된다.
- priority 범위와 `DONE`/`completed_at` 조합의 정상·비정상 사례가 모두 검증된다.

## 자기 설명

1. 단일 `user_id` 외래 키만으로 assignee의 프로젝트 소속을 보장할 수 없는 이유는 무엇인가?
2. 애플리케이션 validation과 데이터베이스 제약을 함께 유지해야 하는 실패 시나리오는 무엇인가?

## 권장 구현 순서

아래 번호 범위는 `reference/schema.sql` 전체다. 과거 작성 순서가 아닌 권장 construction order이며, workspace가 통과한 뒤에만 같은 번호의 reference 주석과 비교한다.

| 순서 | 파일·대상 | 책임 |
|---:|---|---|
| 1 | `schema.sql` · `users` | identity와 대소문자 무시 uniqueness |
| 2 | `schema.sql` · `projects` | owner·이름·lifecycle 제약 |
| 3 | `schema.sql` · `memberships` | project 안의 user role 복합 identity |
| 4 | `schema.sql` · `tasks` | project-scoped assignee와 상태·시간 불변식 |

## 검증

`make prepare` 뒤 학습자 workspace에 구현한 제약을 공용 fixture로 검사한다.

```bash
./scripts/check-workspace.sh exercises/01-relational-semantics-and-design/02-schema-and-constraints
```

초기 skeleton은 `GUIDE_SEMANTIC:schema-email-constraint`에서 실패하고, 정상·음성 insert 계약을 모두 구현하면 같은 명령이 통과해야 한다.
