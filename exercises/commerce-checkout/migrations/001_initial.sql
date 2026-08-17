-- [Implementation 4] Enforce money, order, idempotency, command leasing, provider-event deduplication, and one-time inventory movement invariants in PostgreSQL.
create table if not exists products (
  id text primary key,
  sku text not null unique,
  name text not null,
  price_minor bigint not null check (price_minor >= 0),
  currency char(3) not null check (currency ~ '^[A-Z]{3}$'),
  stock_on_hand integer not null check (stock_on_hand >= 0),
  active boolean not null default true,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists orders (
  id text primary key,
  status text not null check (status in (
    'pending_payment', 'cancel_pending', 'paid', 'refund_pending',
    'payment_failed', 'canceled', 'refunded'
  )),
  currency char(3) not null check (currency ~ '^[A-Z]{3}$'),
  subtotal_minor bigint not null check (subtotal_minor >= 0),
  total_minor bigint not null check (total_minor >= 0),
  inventory_released_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  check (total_minor = subtotal_minor)
);

create table if not exists order_items (
  order_id text not null references orders(id) on delete cascade,
  product_id text not null references products(id),
  sku text not null,
  product_name text not null,
  unit_price_minor bigint not null check (unit_price_minor >= 0),
  currency char(3) not null check (currency ~ '^[A-Z]{3}$'),
  quantity integer not null check (quantity between 1 and 20),
  line_total_minor bigint not null check (line_total_minor >= 0),
  primary key (order_id, product_id),
  check (line_total_minor = unit_price_minor * quantity)
);

create table if not exists payments (
  id text primary key,
  order_id text not null unique references orders(id) on delete cascade,
  provider_payment_id text unique,
  status text not null check (status in (
    'pending', 'cancel_pending', 'succeeded', 'failed',
    'canceled', 'refund_pending', 'refunded'
  )),
  amount_minor bigint not null check (amount_minor >= 0),
  currency char(3) not null check (currency ~ '^[A-Z]{3}$'),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists idempotency_records (
  scope text not null,
  key text not null,
  request_hash char(64) not null,
  state text not null check (state in ('processing', 'completed')),
  response_status integer,
  response_body jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  primary key (scope, key),
  check (
    (state = 'processing' and response_status is null and response_body is null)
    or
    (state = 'completed' and response_status is not null and response_body is not null)
  )
);

create table if not exists payment_commands (
  id text primary key,
  order_id text not null references orders(id) on delete cascade,
  kind text not null check (kind in ('create', 'cancel', 'refund')),
  status text not null check (status in ('pending', 'processing', 'sent', 'dead')),
  attempts integer not null default 0 check (attempts >= 0),
  provider_operation_id text,
  last_error text,
  next_attempt_at timestamptz not null default now(),
  claimed_at timestamptz,
  claim_token text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (order_id, kind),
  check (
    (status = 'processing' and claimed_at is not null and claim_token is not null)
    or
    (status <> 'processing' and claimed_at is null and claim_token is null)
  )
);

create index if not exists payment_commands_pending_idx
  on payment_commands (next_attempt_at, created_at)
  where status = 'pending';

create table if not exists provider_events (
  event_id text primary key,
  event_type text not null,
  provider_payment_id text not null,
  payload_hash char(64) not null,
  outcome text not null,
  received_at timestamptz not null default now()
);

create table if not exists inventory_movements (
  id text primary key,
  order_id text not null references orders(id) on delete cascade,
  product_id text not null references products(id),
  kind text not null check (kind in ('reserve', 'release')),
  quantity integer not null check (quantity > 0),
  created_at timestamptz not null default now(),
  unique (order_id, product_id, kind)
);

create table if not exists order_events (
  id text primary key,
  order_id text not null references orders(id) on delete cascade,
  event_type text not null,
  data jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);
