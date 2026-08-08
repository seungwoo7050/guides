INSERT INTO events(tenant_id, created_at, kind, payload)
SELECT
    (g % 50) + 1,
    timestamptz '2025-01-01 00:00:00+00' + g * interval '1 second',
    CASE WHEN g % 20 = 0 THEN 'ERROR' ELSE 'INFO' END,
    repeat(md5(g::text), 2)
FROM generate_series(1, 100000) AS g;

INSERT INTO jobs(status, scheduled_at, payload)
SELECT
    CASE WHEN g % 20 = 0 THEN 'PENDING' WHEN g % 3 = 0 THEN 'RUNNING' ELSE 'DONE' END,
    timestamptz '2025-02-01 00:00:00+00' + g * interval '1 minute',
    md5(g::text)
FROM generate_series(1, 50000) AS g;
ANALYZE events;
ANALYZE jobs;
