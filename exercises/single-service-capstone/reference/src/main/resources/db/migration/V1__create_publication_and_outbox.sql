create table publication (
  id uuid primary key,
  actor_id varchar(100) not null,
  idempotency_key varchar(120) not null,
  title varchar(120) not null,
  source varchar(500) not null,
  created_at timestamptz not null,
  constraint uq_publication_actor_key unique (actor_id, idempotency_key)
);

create table outbox_event (
  id uuid primary key,
  aggregate_id uuid not null,
  event_type varchar(100) not null,
  payload text not null,
  created_at timestamptz not null,
  published_at timestamptz,
  constraint fk_outbox_publication
    foreign key (aggregate_id) references publication(id)
);

create index ix_outbox_pending
  on outbox_event (created_at)
  where published_at is null;
