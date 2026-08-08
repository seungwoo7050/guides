CREATE INDEX IF NOT EXISTS tickets_org_open_priority_created_idx
ON tickets(org_id, priority DESC, created_at DESC, id DESC)
WHERE status <> 'DONE';

CREATE INDEX IF NOT EXISTS tickets_project_open_created_idx
ON tickets(org_id, project_id, created_at, id)
WHERE status <> 'DONE';

CREATE INDEX IF NOT EXISTS tickets_assignee_queue_idx
ON tickets(org_id, assignee_id, priority DESC, created_at, id)
WHERE status <> 'DONE' AND assignee_id IS NOT NULL;
