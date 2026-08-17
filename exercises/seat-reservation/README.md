# Seat Reservation

PostgreSQL unique constraint와 transaction을 이용해 같은 event의 같은 seat를 동시에 두 번 예약하지 못하게 하는 reservation library입니다. Reservation과 audit record의 atomicity, SQL value binding과 pool cleanup을 실제 database test로 검증합니다.

## Domain contract

- `seat_no`는 양수입니다.
- `(event_id, seat_no)`는 database에서 unique합니다.
- Reservation과 `reservation_audit`는 같은 transaction에서 commit됩니다.
- 동시 요청 중 정확히 하나만 성공합니다.
- PostgreSQL `23505`만 `SeatTakenError("seat_taken")`로 변환합니다.
- SQL처럼 보이는 string도 query syntax가 아니라 bound value로 저장됩니다.

## Install and run

```sh
npm install
cp .env.example .env
docker compose up -d
export DATABASE_URL=postgres://postgres:postgres@127.0.0.1:55432/seat_reservation
npm run migrate
npm run typecheck
npm test
```

정리:

```sh
docker compose down -v
```

## Architecture

`migrations/001_initial.sql`이 최종 invariant를 소유합니다. `src/db.ts`는 SQL schema를 Kysely type으로 옮기고 Kysely를 pool lifecycle의 sole owner로 둡니다. `reserveSeat()`가 transaction boundary이며 reservation과 audit insert를 한 unit으로 묶습니다.

## Major design decisions

- 경쟁 제어를 process-local mutex가 아니라 PostgreSQL unique constraint에 맡깁니다.
- Transaction 내부 row는 commit 전 외부 connection에 보이지 않습니다.
- 예상한 uniqueness failure만 domain error로 변환하고 다른 database error는 보존합니다.
- Raw migration SQL 외의 application query는 Kysely binding을 사용합니다.
- Test suite가 DB resource를 직접 만들고 `db.destroy()`로 pool까지 닫습니다.

## Implementation Order

| Order | Responsibility | Primary anchor |
| ----: | --- | --- |
| 1 | Relational reservation invariants | `migrations/001_initial.sql` |
| 2 | Typed database and pool ownership | `src/db.ts` |
| 3 | Migration resource lifecycle | `src/migrate.ts` |
| 4 | Bound event insertion | `src/repository.ts` |
| 5 | Transaction and domain-failure boundary | `src/repository.ts` |
| 6 | Reservation-audit atomic write | `src/repository.ts` |

## Scope and limitations

이 프로젝트는 seat hold timeout, payment, cancellation, waiting list와 event capacity model을 구현하지 않습니다. 단일 PostgreSQL database 안의 reservation invariant와 transaction behavior에 집중합니다.
