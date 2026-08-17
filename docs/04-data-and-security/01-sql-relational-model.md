# 관계형 모델과 SQL

메모를 객체 배열에 저장하는 방식은 처음에는 단순합니다. 그러나 여러 사용자가 데이터를 공유하고 동시에 수정하기 시작하면 개체 간 관계와 데이터 제약이 필요해집니다. 관계형 데이터베이스는 값을 테이블에 보관하는 도구를 넘어, **허용되는 데이터 상태와 관계를 데이터베이스 수준에서 제한하는 시스템**입니다.

## 목표

- 행·열·테이블과 키의 역할을 설명합니다.
- 도메인 개체와 관계를 테이블로 나눕니다.
- 기본 키, 외래 키, 고유 제약 조건, 검사 제약 조건으로 불변식을 표현합니다.
- `SELECT`, `INSERT`, `UPDATE`, `DELETE`가 처리할 행을 명확히 제한합니다.
- `NULL`, 중복 행, 정렬, 페이지네이션에서 흔히 발생하는 문제를 구분합니다.

## 테이블은 같은 의미를 가진 행의 집합입니다

공유 메모 애플리케이션은 다음과 같은 스키마로 시작할 수 있습니다.

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

각 열은 단순한 저장 공간이 아니라 값의 의미와 허용 범위를 나타냅니다. `owner_id`는 임의의 문자열이 아니라 실제 사용자 행을 참조하며, `version`은 음수가 될 수 없습니다.

## 식별자와 도메인 속성을 구분합니다

이메일은 사용자에게 보이는 자연 식별자지만 변경될 수 있습니다. 내부 관계에는 안정적인 대체 키를 사용하고, 이메일의 고유성은 별도 제약 조건으로 보장할 수 있습니다.

```text
users.id       → 내부 관계에서 사용하는 안정적인 식별자
users.email    → 도메인상 고유해야 하지만 변경 가능한 속성
```

모든 테이블에 반드시 UUID를 사용할 필요는 없습니다. 외부 노출 여부, 생성 위치, 정렬 특성, 저장 크기, 운영 요구사항을 기준으로 키 형식을 정합니다. 중요한 것은 키의 의미가 명확하고 다른 행을 안정적으로 참조할 수 있어야 한다는 점입니다.

## 다대다 관계는 연결 테이블로 표현합니다

한 사용자가 여러 메모를 공유받을 수 있고, 한 메모도 여러 사용자와 공유될 수 있습니다.

```sql
create table note_members (
  note_id uuid not null references notes(id) on delete cascade,
  user_id uuid not null references users(id) on delete cascade,
  role text not null check (role in ('editor', 'viewer')),
  primary key (note_id, user_id)
);
```

`primary key (note_id, user_id)`는 동일한 사용자가 같은 메모에 중복으로 등록되는 상태를 막습니다. 애플리케이션 코드에서 먼저 존재 여부를 조회하는 것만으로는 동시에 들어온 두 요청을 완전히 차단할 수 없습니다.

이 초기 모델에서는 `notes.owner_id`가 소유자를 나타내는 기준값이고, `note_members`에는 공유받은 `editor`와 `viewer`만 저장합니다. 소유자도 멤버십 역할로 표현하려면 두 위치에 소유권을 중복 저장해서는 안 됩니다. 이 경우 `owner_id`를 제거하고, 메모 생성 트랜잭션에서 첫 번째 `owner` 멤버십을 함께 만들어야 합니다. [`공유 메모`](../06-capstones/03-shared-notes.md)는 후자의 모델로 확장합니다.

## 제약 조건은 데이터의 마지막 방어선입니다

애플리케이션 입력 검증과 데이터베이스 제약 조건은 역할이 다릅니다.

- 애플리케이션은 사용자에게 이해하기 쉬운 오류를 빠르게 제공합니다.
- 데이터베이스는 어떤 코드 경로나 경쟁 조건에서도 잘못된 최종 상태를 거부합니다.

예를 들어 제목 길이는 API에서 먼저 확인할 수 있지만, 핵심 도메인 불변식은 데이터베이스에도 표현하는 편이 안전합니다.

```sql
alter table notes
  add constraint notes_title_not_blank
  check (length(trim(title)) between 1 and 120);
```

모든 복잡한 도메인 규칙을 검사 제약 조건에 넣을 필요는 없습니다. 여러 테이블이나 외부 상태를 함께 확인해야 하는 규칙은 트랜잭션 안의 애플리케이션 서비스에서 처리할 수 있습니다.

## 기본적인 쓰기와 읽기

```sql
insert into notes (id, owner_id, title, body, created_at, updated_at)
values ($1, $2, $3, $4, now(), now());
```

매개변수 자리표시자를 사용하고 사용자 입력을 SQL 문자열에 직접 이어 붙이지 않습니다.

```sql
select id, title, version, updated_at
from notes
where owner_id = $1
order by updated_at desc, id desc
limit $2;
```

`ORDER BY`가 없으면 데이터베이스가 행을 반환하는 순서는 보장되지 않습니다. `updated_at` 값이 같은 행까지 안정적으로 정렬하려면 `id` 같은 보조 정렬 키를 추가합니다.

## UPDATE에는 대상과 조건을 함께 표현합니다

```sql
update notes
set title = $1,
    version = version + 1,
    updated_at = now()
where id = $2
  and version = $3
returning id, title, version, updated_at;
```

`version = $3` 조건은 오래된 화면에서 보낸 요청이 최신 변경을 덮어쓰는 것을 막습니다. 반환된 행이 없다면 리소스가 없는지, 권한이 없는지, 버전이 충돌했는지 구분할 추가 조회나 API 정책이 필요할 수 있습니다.

`UPDATE notes SET title = $1`처럼 `WHERE` 절이 빠지면 모든 행이 변경됩니다. 쓰기 쿼리를 검토할 때는 대상 행을 제한하는 조건부터 확인합니다.

## DELETE와 데이터 수명

```sql
delete from notes
where id = $1 and owner_id = $2
returning id;
```

물리 삭제, 보관 상태, 논리 삭제 중 무엇을 사용할지는 복구·감사·개인정보 삭제 요구사항에 따라 결정합니다. `deleted_at` 열을 추가한다고 모든 조회에서 삭제된 행이 자동으로 제외되지는 않습니다. 기본 조회 조건, 고유 제약 조건, 외래 키 정책을 함께 설계해야 합니다.

## NULL은 빈 문자열이 아닙니다

`NULL`은 값이 알려지지 않았거나 적용되지 않음을 나타냅니다. SQL의 비교 결과는 참과 거짓뿐 아니라 `UNKNOWN`이 될 수 있습니다.

```sql
-- NULL인 행을 찾지 못합니다.
where archived_at = null

-- 올바른 형태입니다.
where archived_at is null
```

반드시 있어야 하는 값에는 `NOT NULL`을 지정합니다. 값이 없을 수 있다면 그 상태가 “아직 없음”, “적용되지 않음”, “알 수 없음” 중 무엇을 뜻하는지 모델에서 설명할 수 있어야 합니다.

## JOIN은 관계를 따라 데이터를 읽습니다

```sql
select n.id, n.title, m.role
from notes as n
join note_members as m on m.note_id = n.id
where m.user_id = $1
order by n.updated_at desc, n.id desc;
```

`JOIN`으로 결과 행 수가 늘어나는 이유를 이해해야 합니다. 메모 하나에 구성원이 세 명이면 메모 행이 세 번 나타날 수 있습니다. 이를 무조건 `DISTINCT`로 감추기보다 원하는 결과 단위와 조인 카디널리티를 먼저 확인합니다.

## 페이지네이션

작은 목록은 `LIMIT`과 `OFFSET`으로 시작할 수 있습니다.

```sql
order by updated_at desc, id desc
limit $1 offset $2;
```

데이터가 커지고 조회 사이에 행이 추가되면 페이지가 겹치거나 일부 행을 건너뛸 수 있습니다. 안정적인 정렬 키를 사용하는 커서 기반 페이지네이션은 마지막으로 읽은 행 다음부터 조회합니다.

```sql
where (updated_at, id) < ($1, $2)
order by updated_at desc, id desc
limit $3;
```

입문 단계에서는 두 방식의 차이와 정렬 기준의 중요성을 이해하면 충분합니다.

## 흔한 오류

- 배열이나 단일 JSON 값에 모든 관계를 숨깁니다.
- 애플리케이션 검사만 믿고 핵심 고유·외래 키 제약 조건을 생략합니다.
- 사용자 입력을 문자열 보간으로 SQL에 삽입합니다.
- `ORDER BY` 없이 목록 순서가 고정된다고 가정합니다.
- `NULL`을 빈 문자열과 같은 값으로 취급합니다.
- 조인으로 늘어난 행을 이유 없이 `DISTINCT`로 감춥니다.
- `UPDATE`와 `DELETE`가 처리할 행을 제한하는 조건을 확인하지 않습니다.

## 연결 실습

[`PostgreSQL과 Kysely`](../../exercises/05-postgresql-kysely/README.md)의 좌석 예약 예제에서 고유 제약 조건과 실제 경쟁 요청이 어떻게 연결되는지 확인합니다.

## 완료 기준

- 도메인 개체와 다대다 관계를 테이블로 나눌 수 있습니다.
- 기본 키, 외래 키, 고유 제약 조건, 검사 제약 조건의 역할을 설명할 수 있습니다.
- 매개변수화된 쿼리와 안정적인 정렬을 사용합니다.
- `NULL`, 조인 카디널리티, 페이지네이션에서 발생하는 기본적인 문제를 구분합니다.
- 애플리케이션 검증과 데이터베이스 제약 조건이 각각 무엇을 보장하는지 설명할 수 있습니다.

## 다음 단계

TypeScript에서 PostgreSQL 쿼리를 안전하게 작성하고 결과를 애플리케이션 타입으로 변환하는 방법은 [`PostgreSQL과 Kysely`](02-postgresql-kysely.md)에서 다룹니다.
