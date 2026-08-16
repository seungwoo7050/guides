-- Stage 02부터 완성합니다.
-- src/db.ts의 Database type과 specs/를 기준으로 PK, FK, unique, check와 index를 작성하세요.
-- 최소 table:
-- products, orders, order_items, payments, idempotency_records,
-- payment_commands, provider_events, inventory_movements, order_events

create table if not exists products (
  id text primary key,
  sku text not null unique,
  name text not null,
  price_minor bigint not null,
  currency char(3) not null,
  stock_on_hand integer not null,
  active boolean not null default true,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

-- TODO: 나머지 schema와 모든 업무 제약을 구현합니다.

-- Stage 03: payment_commands에는 claimed_at과 claim_token을 함께 두고
-- processing claim의 소유자를 complete/fail 조건에 포함하세요.
