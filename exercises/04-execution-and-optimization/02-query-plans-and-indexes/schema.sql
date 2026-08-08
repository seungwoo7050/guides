CREATE TABLE events (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    tenant_id integer NOT NULL,
    created_at timestamptz NOT NULL,
    kind text NOT NULL,
    payload text NOT NULL
);

CREATE TABLE jobs (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    status text NOT NULL CHECK (status IN ('PENDING', 'RUNNING', 'DONE')),
    scheduled_at timestamptz NOT NULL,
    payload text NOT NULL
);
