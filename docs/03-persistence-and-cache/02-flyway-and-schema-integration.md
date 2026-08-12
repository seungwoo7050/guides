# Flyway와 스키마 연결

JPA entity는 애플리케이션 매핑이며 스키마 변경 기록이 아니다. Flyway migration을 스키마의 정본으로 두고 Hibernate는 `ddl-auto=validate`로 매핑 차이를 시작 단계에서 발견하게 한다.

## 빈 데이터베이스에서 항상 재현한다

운영에 배포된 migration은 수정하지 않는다. 변경이 필요하면 새 version을 추가한다.

```text
V1__create_project.sql
V2__add_project_status.sql
V3__backfill_project_status.sql
V4__require_project_status.sql
```

개발자 DB를 수동으로 고쳐 성공한 상태는 재현 가능한 스키마가 아니다. Testcontainers의 빈 PostgreSQL에서 첫 migration부터 전부 적용한다.

## 호환 가능한 순서로 나눈다

열 이름 변경이나 필수 제약 추가는 한 번의 배포로 끝내지 않을 수 있다.

```text
새 구조 추가
→ 새·구 구조를 함께 읽거나 쓰는 호환 버전 배포
→ 기존 데이터 backfill
→ 새 구조 사용 확인
→ 이전 구조 제거
```

migration과 application binary의 배포 순서를 문서화한다. 이전 binary로 rollback했을 때 새 스키마와 호환되는지도 검사한다. 실제 배포 orchestrator와 host rollback은 `guide-web-infrastructure`가 담당한다.

## 데이터베이스 제약을 마지막 방어선으로 둔다

Bean Validation은 빠른 사용자 오류를 제공하지만 동시에 들어온 요청의 경쟁을 막지 못한다.

```sql
constraint ck_inventory_available check (available >= 0),
constraint uq_request_actor_key unique (actor_id, idempotency_key),
constraint fk_project_owner foreign key (owner_id) references account(id)
```

제약 이름을 명시하면 application exception 번역과 운영 진단이 쉬워진다. repository test는 제약 위반이 원하는 domain error로 변환되는지 확인한다.

## Flyway 실행 위치를 하나로 정한다

여러 application instance가 동시에 시작하더라도 migration owner와 잠금 정책이 명확해야 한다. 애플리케이션 시작 시 Flyway를 실행할지, 별도 release job이 실행할지 선택한다. 두 방식을 섞어 누가 schema를 변경했는지 불명확하게 만들지 않는다.

이 가이드의 실습은 application startup에서 migration을 실행하고 실제 PostgreSQL에서 검증한다. 운영 배포에서는 변경 크기, lock 시간과 별도 migration job 필요성을 추가 판단한다.

## 검사 항목

- 빈 DB에서 전체 migration 성공
- entity mapping validation 성공
- 이미 적용한 migration checksum이 바뀌지 않음
- constraint 이름과 오류 번역 확인
- rollback binary와의 schema 호환성
- migration 실패 시 readiness가 성공하지 않음

[트랜잭션 잠금 실습](../../exercises/transaction-locking/README.md)에서 빈 PostgreSQL migration, mapping validation과 동시 차감의 최종 불변식을 함께 확인한다. Capstone migration은 primary path의 나머지 단계를 마친 뒤 최종 실습에서 검증한다.
