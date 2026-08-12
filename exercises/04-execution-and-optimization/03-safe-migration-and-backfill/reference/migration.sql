-- [Implementation 1] Expand: 먼저 nullable column을 추가한다. 재실행해도 기존 column을 보존한다.
ALTER TABLE orders ADD COLUMN IF NOT EXISTS status text;

-- [Implementation 2] Backfill: 실제 운영에서는 이 UPDATE를 안정적인 id 범위의 작은 transaction으로 반복한다.
UPDATE orders
SET status = upper(legacy_state)
WHERE status IS NULL;

-- [Implementation 3] Constraint 생성은 catalog로 선행 상태를 확인하고 NOT VALID로 write 경계를 먼저 고정한다.
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conrelid = 'orders'::regclass
          AND conname = 'orders_status_allowed'
    ) THEN
        EXECUTE 'ALTER TABLE orders ADD CONSTRAINT orders_status_allowed CHECK (status IN (''NEW'', ''PAID'', ''CANCELLED'')) NOT VALID';
    END IF;
END $$;

-- [Implementation 4] 기존 row를 검증한 다음에야 NOT NULL contract로 전환한다.
ALTER TABLE orders VALIDATE CONSTRAINT orders_status_allowed;
ALTER TABLE orders ALTER COLUMN status SET NOT NULL;

-- [Implementation 5] 최종 state가 안정된 뒤 대표 상태·시간 조회의 access path를 추가한다.
CREATE INDEX IF NOT EXISTS orders_status_created_idx
ON orders(status, created_at DESC, id DESC);
