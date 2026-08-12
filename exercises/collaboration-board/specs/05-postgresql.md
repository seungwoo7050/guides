# 05. PostgreSQL 영속성

## 목표

업무 불변식을 schema 제약과 transaction으로 보호하고, 메모리 repository를 PostgreSQL 구현으로 교체합니다.

## 구현할 변경

- users, sessions, boards, board_members, board_items, board_events, admin_actions migration을 만듭니다.
- 기본 키, 외래 키, unique와 check constraint로 잘못된 상태를 거부합니다.
- Kysely type과 repository implementation을 추가하되 service는 구체 DB client를 알지 않습니다.
- item 완료 변경, board version 증가와 activity event 추가를 한 transaction으로 묶습니다.
- migration과 seed를 application start와 분리합니다.

## 실패 조건

- 먼저 조회한 뒤 insert하는 코드만으로 uniqueness를 보장합니다.
- 업무 쓰기와 audit event가 서로 다른 transaction입니다.
- migration이 기존 데이터를 고려하지 않고 destructive change를 수행합니다.
- pool을 닫지 않아 검사가 남습니다.

## 검증

빈 DB migration, constraint violation, 두 경쟁 변경 중 하나만 성공, 중간 실패 rollback과 재실행 가능한 setup을 실제 PostgreSQL에서 확인합니다.

검증 진입점은 다음과 같습니다. `work/package.json`의 `verify:05`는 이 단계까지의 형 검사·테스트·build를 누적 실행해야 합니다.

```sh
node exercises/collaboration-board/checks/verify-work.mjs exercises/collaboration-board/work 5
```

## 완료 계약

응용 코드가 실수하거나 요청이 경쟁해도 데이터베이스가 핵심 불변식을 보존합니다.
