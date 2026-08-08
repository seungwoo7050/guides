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

## 목표

협업 도메인의 소속·역할·상태 규칙을 복합 키와 선언적 제약으로 데이터베이스 경계에 둔다.

## 완료 기준

- 대소문자만 다른 이메일과 같은 프로젝트의 중복 membership insert가 거부된다.
- 다른 프로젝트 member를 task assignee로 지정하는 교차 경계 참조가 거부된다.
- priority 범위와 `DONE`/`completed_at` 조합의 정상·비정상 사례가 모두 검증된다.

## 자기 설명

1. 단일 `user_id` 외래 키만으로 assignee의 프로젝트 소속을 보장할 수 없는 이유는 무엇인가?
2. 애플리케이션 validation과 데이터베이스 제약을 함께 유지해야 하는 실패 시나리오는 무엇인가?

## 검증

`./prepare.sh` 뒤 `make postgres-check`를 실행하고 각 음성 사례가 특정 제약에서 실패하는지 확인한다.
