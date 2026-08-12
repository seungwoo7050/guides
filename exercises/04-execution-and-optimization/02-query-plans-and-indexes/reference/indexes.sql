-- [Implementation 1] Tenant equality 뒤에 안정적인 최신순 key를 두고 반환 열은 INCLUDE로 분리한다.
CREATE INDEX events_tenant_created_id_idx
ON events(tenant_id, created_at DESC, id DESC)
INCLUDE (kind, payload);

-- [Implementation 2] 실행 가능한 job만 보유하는 partial index가 queue order와 payload를 함께 지원한다.
CREATE INDEX jobs_pending_schedule_idx
ON jobs(scheduled_at, id)
INCLUDE (payload)
WHERE status = 'PENDING';
