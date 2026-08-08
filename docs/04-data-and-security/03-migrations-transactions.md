# Migration과 Transaction

애플리케이션 코드와 데이터베이스 schema는 따로 배포될 수 있습니다. migration이 개발자 노트에만 있거나, 여러 쓰기가 각각 commit되면 재배포와 실패 중간 상태에서 데이터가 깨집니다. schema 변화와 업무 쓰기 모두 **적용 단위와 실패 후 상태**를 먼저 정의해야 합니다.

## 목표

- migration을 순서가 있는 immutable 변경 기록으로 관리합니다.
- 빈 DB와 기존 데이터가 있는 DB에서 migration을 검증합니다.
- 함께 성공해야 하는 쓰기를 하나의 transaction으로 묶습니다.
- isolation, lock, deadlock과 retry의 최소 모델을 설명합니다.
- application 배포와 schema 변경을 호환 가능한 단계로 나눕니다.

## migration은 현재 schema가 아니라 변화 기록입니다

```text
001_create_users.sql
002_create_notes.sql
003_add_note_version.sql
```

적용된 migration 파일을 나중에 수정하면 이미 실행한 환경과 새 환경의 결과가 달라집니다. 잘못된 변경은 새 migration으로 교정합니다.

migration runner는 다음을 기록해야 합니다.

- migration 식별자와 적용 순서
- 적용 시각
- checksum 또는 변경 여부
- 실패한 migration의 상태

동시에 여러 instance가 migration을 실행하지 않도록 lock이나 별도 release step을 사용합니다.

## 빈 DB와 업그레이드 경로를 모두 검사합니다

두 경로가 필요합니다.

```text
빈 DB → 모든 migration 순차 적용 → 현재 schema
이전 release DB → 새 migration만 적용 → 현재 schema
```

새 개발 환경에서만 성공하고 실제 운영 데이터에서 실패할 수 있습니다. `NOT NULL` 열을 기존 행이 있는 표에 바로 추가하는 경우가 대표적입니다.

## expand–migrate–contract

호환성 있는 schema 변경은 여러 release로 나눌 수 있습니다.

예: `users.name`을 `display_name`으로 바꿉니다.

1. **expand**: 새 nullable 열을 추가하고 새 코드가 양쪽을 읽을 수 있게 합니다.
2. **migrate**: 기존 행을 batch로 backfill하고 누락을 측정합니다.
3. **switch**: 모든 writer가 새 열을 쓰도록 배포합니다.
4. **contract**: 이전 코드가 사라진 뒤 old column을 제거하고 제약을 강화합니다.

한 번의 rename이 기술적으로 가능해도 mixed-version 배포와 rollback이 필요한 환경에서는 호환되지 않을 수 있습니다.

## backfill은 별도 작업으로 다룹니다

큰 표를 한 transaction에서 모두 갱신하면 lock, WAL과 replica lag가 커질 수 있습니다. batch key, 재시작 위치, 처리 속도와 완료 검증을 가진 작업으로 분리합니다.

```sql
with batch as (
  select id
  from users
  where id > $1
    and display_name is null
  order by id
  limit $2
  for update skip locked
)
update users as u
set display_name = u.name
from batch
where u.id = batch.id
returning u.id;
```

PostgreSQL의 실제 batch update 문장은 CTE나 key 목록을 사용할 수 있습니다. 중요한 것은 작업이 중단돼도 다시 시작할 수 있고, 이미 처리한 행을 안전하게 건너뛴다는 점입니다.

## transaction은 원자적 업무 단위입니다

메모 수정과 활동 기록이 함께 성공해야 합니다.

```ts
await db.transaction().execute(async (trx) => {
  const note = await updateNoteIfCurrent(trx, command);
  if (!note) throw new VersionConflict();
  await appendActivity(trx, {
    noteId: note.id,
    actorId: command.actorId,
    version: note.version,
    occurredAt: clock.now()
  });
});
```

callback이 실패하면 둘 다 rollback됩니다. transaction 안에서 외부 HTTP·email·broker 응답을 오래 기다리지 않습니다. DB transaction은 DB 상태만 원자적으로 만들 수 있습니다.

## transaction 경계를 너무 작거나 크게 잡지 않습니다

너무 작은 경우:

```text
note update commit
→ activity insert 실패
→ 감사 기록이 없는 변경
```

너무 큰 경우:

```text
DB lock 획득
→ 외부 API timeout 10초 대기
→ 다른 요청이 같은 행을 기다림
```

use case의 DB 불변식을 보호하는 가장 짧은 범위에 둡니다.

## isolation의 최소 모델

여러 transaction은 동시에 실행됩니다. 기본 격리에서도 다음을 고려해야 합니다.

- 같은 행을 두 요청이 읽고 갱신하는 lost update
- 서로 다른 행을 읽고 각각 쓰며 전체 규칙을 깨는 write skew
- lock을 반대 순서로 얻는 deadlock
- serialization failure

모든 문제를 높은 isolation 하나로 해결하려 하지 않습니다. 조건부 update, unique constraint, 명시적 row lock, serializable transaction 중 불변식에 맞는 도구를 선택합니다.

## row lock

다음 순번을 한 행에서 할당해야 한다면 `FOR UPDATE`로 해당 카운터 행을 잠글 수 있습니다.

```sql
select next_sequence
from board_counters
where board_id = $1
for update;
```

lock을 사용할 때는 모든 코드 경로가 같은 순서로 자원을 획득하도록 합니다. transaction이 끝나기 전까지 lock이 유지됨을 기억합니다.

## deadlock과 retry

PostgreSQL은 deadlock을 감지하면 transaction 하나를 중단합니다. serialization failure도 정상적인 동시성 결과일 수 있습니다. retry는 다음 조건일 때만 사용합니다.

- 전체 transaction을 처음부터 다시 실행할 수 있습니다.
- 외부 부수 효과가 transaction 안에 없습니다.
- 시도 횟수와 전체 deadline이 제한됩니다.
- 무작위 지연으로 동시 재시도를 줄입니다.
- 어떤 오류 code가 retry 가능한지 좁게 정의합니다.

모든 DB 오류를 무한 retry하면 장애를 증폭합니다.

## transaction 뒤 외부 효과

DB commit과 메시지 발행을 한 transaction으로 묶을 수 없다면 단순히 “commit 후 publish”로 끝내지 않습니다. 작은 단일 애플리케이션에서는 실패를 기록하고 재시도할 수 있으며, 여러 서비스 사이의 확실한 전달은 outbox 같은 분산 시스템 주제입니다. 이 가이드에서는 DB transaction의 한계까지 이해합니다.

## migration과 애플리케이션 배포

release 전에 다음을 확인합니다.

- 새 코드가 이전 schema에서도 시작 가능한가
- migration 뒤 이전 코드로 rollback 가능한가
- 장시간 migration이 request latency를 막는가
- migration 실패 시 자동으로 재시도해도 되는가
- readiness가 migration 완료 전 traffic을 받지 않는가

schema migration을 각 application instance의 일반 startup에 무조건 묶으면 여러 instance 경쟁과 긴 재시작이 발생할 수 있습니다. 별도 release job을 고려합니다.

## 검증

필수 검사는 다음입니다.

- 빈 DB 전체 적용
- 이전 snapshot에서 upgrade
- 같은 migration 재실행 정책
- 중간 오류 시 partial schema 여부
- transaction 중 두 번째 쓰기 실패와 rollback
- 같은 version의 동시 갱신
- deadlock·serialization 오류 처리
- pool·process cleanup

## 실패 조건

- 적용된 migration 파일을 직접 수정합니다.
- 현재 schema dump만 있고 변화 기록이 없습니다.
- 기존 데이터가 있는 업그레이드 경로를 검사하지 않습니다.
- transaction마다 외부 API를 호출합니다.
- 모든 DB 오류를 동일하게 retry합니다.
- destructive schema 변경을 코드 배포와 한 단계로 처리합니다.
- migration을 모든 instance가 동시에 실행하게 둡니다.

## 연결 실습

[`PostgreSQL과 Kysely`](../../exercises/05-postgresql-kysely/README.md)에서 migration과 예약·감사 기록 rollback, 경쟁 요청을 실제 DB로 확인합니다.

## 완료 기준

- migration을 immutable 순서 기록으로 관리합니다.
- 빈 DB와 기존 DB의 업그레이드 경로를 검증합니다.
- expand–migrate–contract로 호환 가능한 변경을 설명합니다.
- 업무 불변식에 맞는 transaction과 lock 경계를 선택합니다.
- deadlock·serialization retry의 안전 조건을 설명합니다.

## 다음 단계

데이터베이스에 저장할 수 없는 비밀번호와 로그인 상태의 수명은 [`비밀번호, 세션과 cookie`](04-passwords-sessions-cookies.md)에서 다룹니다.
