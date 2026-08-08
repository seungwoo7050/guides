-- Expand: 먼저 nullable column을 추가한다. 재실행해도 기존 column을 보존한다.
ALTER TABLE orders ADD COLUMN IF NOT EXISTS status text;

-- Backfill: 실제 운영에서는 이 UPDATE를 안정적인 id 범위의 작은 transaction으로 반복한다.
UPDATE orders
SET status = upper(legacy_state)
WHERE status IS NULL;

-- 새 write가 잘못된 값을 만들지 못하게 한 뒤 기존 데이터 검증을 분리한다.
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

ALTER TABLE orders VALIDATE CONSTRAINT orders_status_allowed;
ALTER TABLE orders ALTER COLUMN status SET NOT NULL;

CREATE INDEX IF NOT EXISTS orders_status_created_idx
ON orders(status, created_at DESC, id DESC);
