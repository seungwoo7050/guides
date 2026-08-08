CREATE INDEX events_tenant_created_id_idx
ON events(tenant_id, created_at DESC, id DESC)
INCLUDE (kind, payload);

CREATE INDEX jobs_pending_schedule_idx
ON jobs(scheduled_at, id)
INCLUDE (payload)
WHERE status = 'PENDING';
