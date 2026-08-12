-- [Implementation 6] View layer는 workload의 row 단위와 tenant filter를 index 설계 전에 고정한다.
-- [Implementation 6-1] Project backlog는 project가 row owner이고 open ticket의 count·oldest를 집계한다.
CREATE OR REPLACE VIEW q_project_backlog AS
SELECT
    p.org_id,
    p.id AS project_id,
    count(t.id) FILTER (WHERE t.status <> 'DONE')::bigint AS open_count,
    min(t.created_at) FILTER (WHERE t.status <> 'DONE') AS oldest_opened_at
FROM projects AS p
LEFT JOIN tickets AS t ON t.project_id = p.id AND t.org_id = p.org_id
GROUP BY p.org_id, p.id;

-- [Implementation 6-2] Organization open-ticket view는 keyset page에 필요한 완전한 tuple을 노출한다.
CREATE OR REPLACE VIEW q_org_open_tickets AS
SELECT id, org_id, project_id, priority, created_at
FROM tickets
WHERE status <> 'DONE';

-- [Implementation 6-3] Assignee queue는 담당자가 있는 미완료 ticket만 tenant 안에서 노출한다.
CREATE OR REPLACE VIEW q_assignee_queue AS
SELECT id, org_id, project_id, assignee_id, priority, created_at
FROM tickets
WHERE assignee_id IS NOT NULL
  AND status <> 'DONE';
