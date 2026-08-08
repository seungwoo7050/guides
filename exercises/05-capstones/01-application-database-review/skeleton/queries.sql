CREATE VIEW q_project_backlog AS
SELECT project_id, count(*)::bigint AS open_count
FROM tickets
GROUP BY project_id;

CREATE VIEW q_assignee_queue AS
SELECT id, org_id, assignee_id, priority, created_at
FROM tickets
WHERE assignee_id IS NOT NULL
ORDER BY created_at;
