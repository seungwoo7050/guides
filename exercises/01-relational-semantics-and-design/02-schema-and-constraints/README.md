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
