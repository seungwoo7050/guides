# 관계 모델과 SQL

메모를 객체 배열에 저장하면 처음에는 간단하지만, 사용자와 공유하고 동시에 수정하는 순간 관계와 제약이 필요해집니다. 관계형 데이터베이스는 값을 표에 넣는 도구가 아니라 **허용되는 상태와 관계를 데이터 수준에서 제한하는 시스템**입니다.

## 목표

- 행·열·표와 key의 역할을 설명합니다.
- 업무 개체와 관계를 table로 나눕니다.
- primary key, foreign key, unique와 check constraint로 불변식을 표현합니다.
- `SELECT`, `INSERT`, `UPDATE`, `DELETE`의 대상 행을 명확히 제한합니다.
- `NULL`, 중복, 정렬과 pagination의 기본 함정을 구분합니다.

## 표는 같은 의미의 행 집합입니다

공유 메모 애플리케이션을 다음처럼 시작할 수 있습니다.

```sql
create table users (
  id uuid primary key,
  email text not null unique,
  display_name text not null,
  created_at timestamptz not null
);

create table notes (
  id uuid primary key,
  owner_id uuid not null references users(id),
  title text not null,
  body text not null,
  version integer not null default 0 check (version >= 0),
  created_at timestamptz not null,
  updated_at timestamptz not null
);
```

각 열은 단순 저장 공간이 아니라 의미와 허용 범위를 가집니다. `owner_id`는 임의 문자열이 아니라 실제 사용자 행을 가리키고, `version`은 음수가 될 수 없습니다.

## 식별자와 업무 속성을 구분합니다

이메일은 사용자에게 보이는 자연스러운 식별자지만 바뀔 수 있습니다. 내부 관계는 안정된 surrogate key를 사용하고, 이메일의 유일성은 별도 제약으로 표현할 수 있습니다.

```text
users.id       → 내부 관계의 안정된 식별자
users.email    → 업무상 유일해야 하지만 변경 가능한 속성
```

모든 표에 무조건 UUID가 필요한 것은 아닙니다. 외부 노출 여부, 생성 위치, 정렬·크기와 운영 요구를 기준으로 정합니다. 중요한 것은 key의 의미가 명확하고 다른 행을 안정적으로 가리킬 수 있다는 점입니다.

## 다대다 관계는 연결 표로 표현합니다

한 사용자가 여러 메모를 공유받고, 한 메모도 여러 사용자를 가질 수 있습니다.

```sql
create table note_members (
  note_id uuid not null references notes(id) on delete cascade,
  user_id uuid not null references users(id) on delete cascade,
  role text not null check (role in ('editor', 'viewer')),
  primary key (note_id, user_id)
);
```

`primary key (note_id, user_id)`는 같은 사용자가 같은 메모에 두 번 가입되는 상태를 경쟁 요청에서도 막습니다. 코드에서 먼저 존재 여부를 검사하는 것만으로는 동시에 들어온 두 요청을 완전히 막을 수 없습니다.

이 첫 모델에서는 `notes.owner_id`가 소유자의 정본이고 `note_members`에는 추가로 공유받은 `editor`·`viewer`만 저장합니다. 소유자도 membership role로 표현하려면 `owner_id`와 role을 동시에 정본으로 두지 말고, `owner_id`를 제거한 뒤 생성 transaction에서 첫 `owner` membership을 함께 만들어야 합니다. [`공유 메모`](../06-capstones/03-shared-notes.md)는 두 번째 모델로 확장합니다.

## 제약은 마지막 방어선입니다

애플리케이션 validation과 데이터베이스 constraint는 역할이 다릅니다.

- 애플리케이션은 사용자에게 이해하기 쉬운 오류를 빠르게 제공합니다.
- 데이터베이스는 어떤 경로와 경쟁 조건에서도 잘못된 최종 상태를 거부합니다.

예를 들어 제목 길이는 API에서 먼저 확인할 수 있지만, 핵심 업무 불변식은 DB에도 표현하는 편이 안전합니다.

```sql
alter table notes
  add constraint notes_title_not_blank
  check (length(trim(title)) between 1 and 120);
```

모든 복잡한 업무 규칙을 check constraint에 넣을 필요는 없습니다. 여러 표와 외부 상태를 함께 판단하는 규칙은 transaction 안의 application service가 담당할 수 있습니다.

## 기본 쓰기와 읽기

```sql
insert into notes (id, owner_id, title, body, created_at, updated_at)
values ($1, $2, $3, $4, now(), now());
```

placeholder를 사용하고 사용자 문자열을 SQL 문장에 직접 이어 붙이지 않습니다.

```sql
select id, title, version, updated_at
from notes
where owner_id = $1
order by updated_at desc, id desc
limit $2;
```

정렬 기준이 없으면 DB가 행을 반환하는 순서는 계약이 아닙니다. 같은 `updated_at`을 가진 행도 안정적으로 정렬하려면 식별자 같은 tie-breaker를 추가합니다.

## UPDATE는 대상과 조건을 함께 표현합니다

```sql
update notes
set title = $1,
    version = version + 1,
    updated_at = now()
where id = $2
  and version = $3
returning id, title, version, updated_at;
```

`version = $3` 조건은 오래된 화면이 최신 변경을 덮는 것을 막습니다. 반환 행이 0개라면 자원이 없는지, 권한이 없는지, version conflict인지 application에서 구분할 추가 조회나 정책이 필요할 수 있습니다.

`UPDATE notes SET title = $1`처럼 `WHERE`가 빠지면 모든 행이 바뀝니다. 쓰기 query를 검토할 때 대상 행을 제한하는 조건을 먼저 확인합니다.

## DELETE와 수명

```sql
delete from notes
where id = $1 and owner_id = $2
returning id;
```

물리 삭제, 보관 상태와 soft delete 중 무엇을 사용할지는 제품의 복구·감사·개인정보 삭제 요구에 따라 달라집니다. `deleted_at`을 추가했다고 모든 query가 자동으로 제외하지는 않습니다. 기본 조회, unique constraint와 foreign key 정책을 함께 설계해야 합니다.

## NULL은 빈 문자열이 아닙니다

`NULL`은 값이 알려지지 않았거나 적용되지 않음을 나타냅니다. 비교 결과가 참·거짓뿐 아니라 unknown이 될 수 있습니다.

```sql
-- NULL 행을 찾지 못합니다.
where archived_at = null

-- 올바른 형태입니다.
where archived_at is null
```

필수 값은 `not null`로 표현합니다. 값이 없을 수 있다면 그것이 “아직 없음”, “적용되지 않음”, “알 수 없음” 중 무엇인지 모델에서 설명할 수 있어야 합니다.

## JOIN은 관계를 따라 읽습니다

```sql
select n.id, n.title, m.role
from notes as n
join note_members as m on m.note_id = n.id
where m.user_id = $1
order by n.updated_at desc, n.id desc;
```

`JOIN`으로 행 수가 늘어나는 이유를 이해해야 합니다. 메모 하나에 구성원 셋이 있으면 메모 행이 세 번 나타날 수 있습니다. `DISTINCT`로 무조건 숨기기보다 필요한 결과 단위와 join cardinality를 먼저 확인합니다.

## pagination

작은 목록은 `LIMIT`과 `OFFSET`으로 시작할 수 있습니다.

```sql
order by updated_at desc, id desc
limit $1 offset $2;
```

데이터가 커지고 중간에 행이 추가되면 페이지가 겹치거나 건너뛸 수 있습니다. 안정된 정렬 key를 사용하는 cursor pagination은 다음처럼 마지막 행 이후를 읽습니다.

```sql
where (updated_at, id) < ($1, $2)
order by updated_at desc, id desc
limit $3;
```

입문 단계에서는 두 방식의 차이와 정렬 계약을 이해하면 충분합니다.

## 실패 조건

- 배열과 JSON 하나에 모든 관계를 숨깁니다.
- 애플리케이션 검사만 믿고 핵심 unique·foreign key를 생략합니다.
- 사용자 입력을 문자열 보간으로 SQL에 넣습니다.
- `ORDER BY` 없이 목록 순서가 고정됐다고 가정합니다.
- `NULL`을 빈 문자열과 같은 값으로 취급합니다.
- join으로 늘어난 행을 이유 없이 `DISTINCT`로 덮습니다.
- update·delete의 대상 조건을 명확히 확인하지 않습니다.

## 연결 실습

[`PostgreSQL과 Kysely`](../../exercises/05-postgresql-kysely/README.md)의 좌석 예약 예제에서 unique constraint와 실제 경쟁 요청이 어떻게 연결되는지 확인합니다.

## 완료 기준

- 업무 개체와 다대다 관계를 table로 나눌 수 있습니다.
- primary·foreign·unique·check constraint의 역할을 설명합니다.
- parameterized query와 안정된 정렬을 사용합니다.
- `NULL`, join cardinality와 pagination의 기본 함정을 구분합니다.
- application validation과 DB 제약이 각각 무엇을 보장하는지 설명합니다.

## 다음 단계

TypeScript에서 PostgreSQL query를 안전하게 조립하고 결과를 application type으로 옮기는 방법은 [`PostgreSQL과 Kysely`](02-postgresql-kysely.md)에서 다룹니다.
