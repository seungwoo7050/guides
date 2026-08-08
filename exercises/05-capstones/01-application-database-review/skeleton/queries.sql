CREATE VIEW q_project_backlog AS
SELECT org_id, project_id, count(*)::bigint AS open_count
FROM tickets
GROUP BY org_id, project_id;

CREATE VIEW q_org_open_tickets AS
SELECT id, org_id, project_id, priority, created_at
FROM tickets
WHERE status <> 'DONE';

CREATE VIEW q_assignee_queue AS
SELECT id, org_id, assignee_id, priority, created_at
FROM tickets
WHERE assignee_id IS NOT NULL
ORDER BY created_at;
