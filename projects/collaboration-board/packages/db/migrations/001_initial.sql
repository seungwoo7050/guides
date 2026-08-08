create extension if not exists pgcrypto;

create table if not exists schema_migrations (
  version text primary key,
  applied_at timestamptz not null default now()
);
create table if not exists users (
  id uuid primary key default gen_random_uuid(),
  handle text not null unique,
  display_name text not null,
  role text not null default 'user' check (role in ('user', 'admin')),
  status text not null default 'active' check (status in ('active', 'suspended')),
  created_at timestamptz not null default now()
);
create table if not exists sessions (
  token text primary key,
  user_id uuid not null references users(id) on delete cascade,
  expires_at timestamptz not null,
  created_at timestamptz not null default now()
);
create table if not exists boards (
  id uuid primary key default gen_random_uuid(),
  owner_id uuid not null references users(id),
  title text not null,
  version integer not null default 0,
  closed_at timestamptz,
  created_at timestamptz not null default now()
);
create table if not exists board_members (
  board_id uuid not null references boards(id) on delete cascade,
  user_id uuid not null references users(id) on delete cascade,
  role text not null check (role in ('owner', 'editor', 'viewer')),
  joined_at timestamptz not null default now(),
  primary key (board_id, user_id)
);
create table if not exists board_items (
  id uuid primary key default gen_random_uuid(),
  board_id uuid not null references boards(id) on delete cascade,
  kind text not null check (kind in ('note', 'shape')),
  content text not null default '',
  x double precision not null,
  y double precision not null,
  width double precision not null default 240,
  height double precision not null default 140,
  version integer not null default 0,
  updated_by uuid not null references users(id),
  updated_at timestamptz not null default now()
);
create table if not exists board_events (
  id uuid primary key default gen_random_uuid(),
  board_id uuid not null references boards(id) on delete cascade,
  sequence bigint not null,
  actor_id uuid not null references users(id),
  event_type text not null,
  payload jsonb not null,
  created_at timestamptz not null default now(),
  unique (board_id, sequence)
);
create table if not exists admin_actions (
  id uuid primary key default gen_random_uuid(),
  actor_id uuid not null references users(id),
  target_user_id uuid not null references users(id),
  action text not null check (action in ('suspend', 'restore')),
  reason text not null,
  created_at timestamptz not null default now()
);

create index if not exists board_members_user_idx on board_members (user_id);
create index if not exists board_items_board_idx on board_items (board_id);
create index if not exists board_events_board_sequence_idx on board_events (board_id, sequence desc);
create index if not exists admin_actions_created_at_idx on admin_actions (created_at desc);
