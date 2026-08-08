CREATE OR REPLACE VIEW q_project_backlog AS
SELECT
    p.org_id,
    p.id AS project_id,
    count(t.id) FILTER (WHERE t.status <> 'DONE')::bigint AS open_count,
    min(t.created_at) FILTER (WHERE t.status <> 'DONE') AS oldest_opened_at
FROM projects AS p
LEFT JOIN tickets AS t ON t.project_id = p.id AND t.org_id = p.org_id
GROUP BY p.org_id, p.id;

CREATE OR REPLACE VIEW q_org_open_tickets AS
SELECT id, org_id, project_id, priority, created_at
FROM tickets
WHERE status <> 'DONE';

CREATE OR REPLACE VIEW q_assignee_queue AS
SELECT id, org_id, project_id, assignee_id, priority, created_at
FROM tickets
WHERE assignee_id IS NOT NULL
  AND status <> 'DONE';
