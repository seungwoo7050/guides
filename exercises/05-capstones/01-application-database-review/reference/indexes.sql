-- [Implementation 7] Workload index는 앞서 고정한 filter·order·row shape를 물리 access path로 내린다.
-- [Implementation 7-1] Organization page의 equality prefix와 완전한 descending cursor를 그대로 따른다.
CREATE INDEX IF NOT EXISTS tickets_org_open_priority_created_idx
ON tickets(org_id, priority DESC, created_at DESC, id DESC)
WHERE status <> 'DONE';

-- [Implementation 7-2] Project backlog의 tenant/project grouping과 oldest scan 순서를 지원한다.
CREATE INDEX IF NOT EXISTS tickets_project_open_created_idx
ON tickets(org_id, project_id, created_at, id)
WHERE status <> 'DONE';

-- [Implementation 7-3] Assignee queue의 equality prefix, priority order와 partial predicate를 일치시킨다.
CREATE INDEX IF NOT EXISTS tickets_assignee_queue_idx
ON tickets(org_id, assignee_id, priority DESC, created_at, id)
WHERE status <> 'DONE' AND assignee_id IS NOT NULL;
