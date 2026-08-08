-- TODO: workload의 equality, order, projection과 predicate를 반영한다.
CREATE INDEX events_wrong_idx ON events(created_at, tenant_id);
CREATE INDEX jobs_wrong_idx ON jobs(status);
