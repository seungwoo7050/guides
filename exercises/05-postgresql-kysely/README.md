# PostgreSQL과 Kysely: 제약, 경쟁과 롤백

Kysely의 데이터베이스 형과 migration을 작성하고, 같은 좌석을 동시에 예약하는 요청 중 하나만 성공하도록 만듭니다. 애플리케이션의 사전 검사와 데이터베이스 제약이 담당하는 경계를 구분합니다.

## 선행 문서

- [`관계 모델과 SQL`](../../docs/04-data-and-security/01-sql-relational-model.md)
- [`PostgreSQL과 Kysely`](../../docs/04-data-and-security/02-postgresql-kysely.md)
- [`migration과 transaction`](../../docs/04-data-and-security/03-migrations-transactions.md)

## 데이터베이스 시작

저장소 밖의 PostgreSQL을 미리 준비할 필요가 없습니다.

```sh
cd exercises/05-postgresql-kysely
docker compose -f compose.test.yml up -d --wait
export DATABASE_URL=postgres://postgres:postgres@127.0.0.1:55432/board_dev
```

`55432`가 이미 사용 중이면 compose 파일의 호스트 포트를 바꾸고 `DATABASE_URL`도 함께 수정합니다.

## 작업하기

```sh
rm -rf work
cp -R skeleton work
cd work
pnpm install
pnpm typecheck
pnpm migrate
pnpm test
```

## 구현할 계약

- migration은 테이블·기본 키·외래 키와 `(event_id, seat_no)` 고유 제약을 만듭니다.
- 예약과 감사 기록은 하나의 transaction에서 함께 성공하거나 함께 실패합니다.
- 두 연결이 같은 좌석을 경쟁할 때 정확히 하나만 성공합니다.
- SQL 값은 parameter binding을 사용하며 사용자 입력을 `sql.raw()`에 연결하지 않습니다.
- Kysely database type에서 `any`를 사용해 열 이름 검사를 끄지 않습니다.
- 검사는 자신이 만든 데이터를 식별하고 정리합니다.

## 실패 주입

- 고유 제약을 제거합니다.
- 첫 insert 뒤 의도적인 예외를 던집니다.
- transaction 밖에서 감사 기록을 작성합니다.
- 실제 열과 다른 이름을 `any`로 숨깁니다.
- migration을 건너뛴 빈 DB에서 검사를 시작합니다.

## Reference 비교

자동 검증을 모두 통과한 뒤에만 `diff -ru work reference`로 구현을 비교합니다. 파일 배치나 표현이 달라도 계약을 만족하면 올바른 구현이며, 차이를 선택한 이유를 설명합니다.

## 완료 기준

migration, 정상 예약, 경쟁 예약, transaction rollback과 SQL injection 경계 검사가 실제 PostgreSQL에서 통과해야 합니다. 종료할 때 connection pool도 닫습니다.

```sh
cd ..
docker compose -f compose.test.yml down -v
```
